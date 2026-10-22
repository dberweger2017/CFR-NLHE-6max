from copy import deepcopy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import nplayer_four_player_feasibility as core
from scripts import nplayer_five_six_feasibility as pilot


class FiveSixTests(unittest.TestCase):
    def test_sizes_have_disjoint_science_and_fixture_roots(self):
        values=[s[k] for s in pilot.SPECS.values() for k in ('seed','qual_seed','cost_seed','trace_seed','main_trace_seed')]
        self.assertEqual(len(values),len(set(values)))
        for p,s in pilot.SPECS.items():
            self.assertEqual(s['seed'],2026102300001+p*1000)
            self.assertEqual(s['qualification_hands']%p,0);self.assertEqual(s['main_hands']%p,0)
            c=dict(players=p,binaries={'nplayer_train':'train'},tables='k50')
            cmd=core.train_command(c,Path('out'),50000000,s['seed'],core.CAP)
            self.assertEqual(cmd[cmd.index('--players')+1],str(p));self.assertNotIn('--prune-bb',cmd)

    def test_checkpoint_cannot_masquerade_as_another_player_count(self):
        for players in (5,6):
            with self.subTest(players=players),tempfile.TemporaryDirectory() as d:
                path=Path(d)/'cp.gz';seed=pilot.SPECS[players]['seed']
                identity=dict(players=players,stacks=[10000]*players,big_blind=100,small_blind=50,
                    menu='min-pot-conditional-jam-v1',schema='nplayer-button-live-actor-history-equity-k50-v1')
                h=dict(game=identity,seed=seed,max_entries=core.CAP,freeze_at_cap=True,roots_per_seat=8,
                    last_average_street=3,average_rule='opponent-sampled',sampling='path-v1',
                    counts=dict(nodes=25000007,discarded_keys=1,discarded_visits=1),entries=20000017,frozen_at=111)
                with gzip.open(path,'wt') as f:f.write(json.dumps(h)+'\n')
                summary=dict(identity=identity,**{k:h[k] for k in ('counts','entries','frozen_at')},stop_reason='nodes',sha256=core.sha(path))
                core.checkpoint(summary,path,25000000,seed,core.CAP,players)
                with self.assertRaises(ValueError):core.checkpoint(summary,path,25000000,seed,core.CAP,4)
                with self.assertRaises(ValueError):core.checkpoint(summary,path,50000000,seed,core.CAP,players)

    def test_combined_quote_enforces_one_allocation_and_sequential_memory(self):
        component=dict(central_seconds=400,reserved_seconds=800,memory_admission=True)
        q=pilot.combined_quote([component,component],100)
        self.assertEqual(q['reserved_seconds'],2300);self.assertTrue(q['main_admitted'])
        self.assertFalse(pilot.combined_quote([component,dict(component,reserved_seconds=3000)],100)['main_admitted'])
        self.assertFalse(pilot.combined_quote([component,dict(component,memory_admission=False)],100)['main_admitted'])

    def test_fixed_loading_cost_is_not_multiplied_by_row_count(self):
        row=dict(checkpoint=dict(counts={'nodes':1000000},entries=1000000,active_seconds=1,
            save_seconds=.1,stage_wall_seconds=1.1))
        costs=[dict(phase='cost-'+k,wall_seconds=(1.1 if k=='train' else 10 if k.startswith('play') else .2),
            sampled_peak_rss_bytes=1000000000) for k in ('train','export','audit','play-0','play-1','replay')]
        q=pilot.quote_for(6)(row,costs,10,8*2**30)
        self.assertTrue(q['main_admitted']);self.assertLess(q['reserved_seconds'],1000)
        self.assertFalse(pilot.quote_for(6)(row,costs,10,2*2**30)['main_admitted'])

    def test_player_scope_mutation_rejected_before_native_or_source_access(self):
        s=pilot.SPECS[5];c=dict(scope=deepcopy(s),players=6)
        with patch.object(core,'source_identity') as source:
            with self.assertRaisesRegex(ValueError,'player scope'):core.validate(c,s)
            source.assert_not_called()

    def test_unbalanced_button_sample_rejected_before_child_creation(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'button rotations'):
                core.export_play(Path(d),dict(players=5),None,'bad',{},24,1)
            self.assertEqual(list(Path(d).iterdir()),[])

    def test_combined_stop_is_observed_before_child_start(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);child=root/'players5';child.mkdir();(root/'STOP').touch()
            sup=core.Supervisor(child,{'NPLAYER_STOP_FILE':str(root/'STOP')},Path('thermal'))
            with patch.object(core,'sample',return_value={'thermal_state':'nominal'}),patch.object(core.subprocess,'Popen') as spawn:
                with self.assertRaisesRegex(RuntimeError,'ownerSTOP'):sup.stage('stopped',['unused'])
                spawn.assert_not_called()

    def test_combined_failed_or_changed_qualification_is_not_resumed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source={'commit':'frozen','files':{}}
            core.write(root/'quote.json',dict(main_admitted=True))
            core.write(root/'qualification.json',dict(status='passed',source=source,quote_sha256='wrong'))
            with patch.object(core,'source_identity',return_value=source):
                with self.assertRaisesRegex(ValueError,'not admitted'):pilot.validate_qualification(root)
            self.assertFalse((root/'launch.json').exists())


if __name__=='__main__':unittest.main()
