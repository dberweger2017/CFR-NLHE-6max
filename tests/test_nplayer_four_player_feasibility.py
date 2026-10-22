from copy import deepcopy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import nplayer_four_player_feasibility as pilot


class FourPlayerTests(unittest.TestCase):
    def fixture(self,path):
        identity=dict(players=4,stacks=[10000]*4,big_blind=100,small_blind=50,
            menu='min-pot-conditional-jam-v1',schema='nplayer-button-live-actor-history-equity-k50-v1')
        h=dict(game=identity,seed=pilot.SEED,max_entries=20000000,freeze_at_cap=True,roots_per_seat=8,
            last_average_street=3,average_rule='opponent-sampled',sampling='path-v1',
            counts=dict(nodes=25000007,discarded_keys=1,discarded_visits=1),entries=20000017,frozen_at=111)
        with gzip.open(path,'wt') as f:f.write(json.dumps(h)+'\n')
        return dict(identity=identity,**{k:h[k] for k in ('counts','entries','frozen_at')},stop_reason='nodes',sha256=pilot.sha(path))

    def test_fixed_four_player_command_and_resume_binding(self):
        c=dict(binaries={'nplayer_train':'train'},tables='k50');parent=dict(checkpoint='parent',sha256='pin')
        cmd=pilot.train_command(c,Path('out'),50000000,pilot.SEED,pilot.CAP,parent)
        for flag,value in [('--players','4'),('--stack-bb','100'),('--threads','10'),('--roots-per-seat','8'),
                ('--nodes','50000000'),('--max-entries','20000000'),('--resume','parent'),('--resume-sha256','pin')]:
            self.assertEqual(cmd[cmd.index(flag)+1],value)
        self.assertNotIn('--prune-bb',cmd);self.assertIn('--freeze-at-cap',cmd)
        self.assertEqual(pilot.TARGETS,(25000000,50000000))

    def test_whole_iteration_cap_and_node_overshoot_are_valid(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'cp.gz';summary=self.fixture(path)
            pilot.checkpoint(summary,path,25000000,pilot.SEED,pilot.CAP)

    def test_wrong_depth_players_endpoint_and_hash_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'cp.gz';summary=self.fixture(path)
            for key,value in [('sha256','wrong'),('stop_reason','entries'),('entries',3)]:
                bad=deepcopy(summary);bad[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):pilot.checkpoint(bad,path,25000000,pilot.SEED,pilot.CAP)
            with self.assertRaises(ValueError):pilot.checkpoint(summary,path,50000000,pilot.SEED,pilot.CAP)
            with self.assertRaises(ValueError):pilot.checkpoint(summary,path,25000000,pilot.SEED+1,pilot.CAP)

    def cost(self,active=1,available=8*2**30):
        row=dict(checkpoint=dict(counts={'nodes':1000000},entries=500000,active_seconds=active,save_seconds=.1,
            stage_wall_seconds=active+.1,elapsed_seconds=active+.1))
        costs=[dict(phase='cost-train',wall_seconds=active+.1,sampled_peak_rss_bytes=1500000000),
            dict(phase='cost-export',wall_seconds=.2,sampled_peak_rss_bytes=1500000000)]
        return pilot.quote(row,costs,120,available)

    def test_quote_admits_only_bounded_time_and_memory(self):
        q=self.cost();self.assertTrue(q['main_admitted']);self.assertLess(q['reserved_seconds'],3600)
        self.assertFalse(self.cost(active=1000)['main_admitted'])
        self.assertFalse(self.cost(available=4*2**30)['main_admitted'])
        self.assertTrue(q['no_main_started'])

    def test_duplicate_attempt_cannot_overwrite_success_or_launch(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'status.json').write_text('{"status":"complete"}')
            before=(root/'status.json').read_bytes()
            with patch.object(pilot,'validate') as validate:
                with self.assertRaises(FileExistsError):pilot.run(root,None,3600)
                validate.assert_not_called()
            self.assertEqual((root/'status.json').read_bytes(),before);self.assertFalse((root/'failure.json').exists())

    def test_config_mutation_refused_before_child_or_stage_creation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);pilot.write(root/'config.json',{'recipe':'frozen'})
            sup=pilot.Supervisor(root,{},Path('thermal'));pilot.write(root/'config.json',{'recipe':'changed'})
            with patch.object(pilot,'sample') as sample:
                with self.assertRaisesRegex(ValueError,'frozen config'):sup.stage('must-not-start',['unused'])
                sample.assert_not_called()
            self.assertFalse((root/'measurements').exists())


if __name__=='__main__':unittest.main()
