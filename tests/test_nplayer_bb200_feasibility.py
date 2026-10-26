import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import nplayer_bb200_feasibility as pilot


class FeasibilityTests(unittest.TestCase):
    def checkpoint(self, directory, mutate=None):
        header={'format':'nplayer-cfr-v1','game':{'players':3,'stacks':[20000]*3,
            'small_blind':50,'big_blind':100,'menu':'min-pot-conditional-jam-v1',
            'schema':'nplayer-button-live-actor-history-equity-k50-v1','utility_unit':'big-blind'},
            'seed':pilot.SEED,'max_entries':pilot.CAP,'last_average_street':3,'freeze_at_cap':True,
            'sampling':'path-v1','roots_per_seat':8,'average_rule':'opponent-sampled',
            'counts':{'nodes':100000017,'discarded_keys':0,'discarded_visits':0},
            'entries':5,'frozen_at':None}
        if mutate:mutate(header)
        path=Path(directory)/'fixture.gz'
        with gzip.open(path,'wt') as f:f.write(json.dumps(header)+'\n')
        summary={'identity':copy.deepcopy(header['game']),'counts':copy.deepcopy(header['counts']),
            'entries':header['entries'],'frozen_at':header['frozen_at'],'sha256':pilot.sha(path),'stop_reason':'nodes'}
        return path,header,summary

    def test_wrong_depth_or_schema_never_becomes_a_200bb_result(self):
        for mutate in (lambda h:h['game'].update(stacks=[10000]*3),
                       lambda h:h['game'].update(players=2),
                       lambda h:h['game'].update(schema='compact'),
                       lambda h:h.update(sampling='stream-v1'),
                       lambda h:h.update(pruning={'bb':1}),
                       lambda h:h.update(last_average_street=0)):
            with self.subTest(mutate=mutate),tempfile.TemporaryDirectory() as d:
                path,header,summary=self.checkpoint(d,mutate)
                with self.assertRaises(ValueError):pilot.validate_checkpoint(summary,path,100000000,pilot.SEED,pilot.CAP)

    def test_checkpoint_hash_endpoint_and_discard_barriers(self):
        with tempfile.TemporaryDirectory() as d:
            path,header,summary=self.checkpoint(d)
            pilot.validate_checkpoint(summary,path,100000000,pilot.SEED,pilot.CAP)
            with self.assertRaises(ValueError):pilot.validate_checkpoint(summary,path,200000000,pilot.SEED,pilot.CAP)
            summary['sha256']='0'*64
            with self.assertRaises(ValueError):pilot.validate_checkpoint(summary,path,100000000,pilot.SEED,pilot.CAP)
        with tempfile.TemporaryDirectory() as d:
            path,header,summary=self.checkpoint(d,lambda h:h['counts'].update(discarded_keys=1))
            with self.assertRaises(ValueError):pilot.validate_checkpoint(summary,path,100000000,pilot.SEED,pilot.CAP)

    def test_resuming_requires_parent_hash_and_keeps_recipe(self):
        command=pilot.train_command({'binaries':{'nplayer_train':'/owned/train'},'tables':'/readonly/k50'},
            '/fresh.gz',200000000,parent={'checkpoint':'/own/first.gz','sha256':'a'*64})
        for flag,value in [('--stack-bb','200'),('--threads','16'),('--roots-per-seat','8'),
                           ('--resume-sha256','a'*64),('--max-seconds','1e100')]:
            self.assertEqual(command[command.index(flag)+1],value)
        self.assertIn('--freeze-at-cap',command);self.assertIn('--fast-gzip',command)
        self.assertNotIn('--prune-bb',command)

    def test_growth_scenarios_do_not_admit_a_large_campaign(self):
        rows=[{'counts':{'nodes':100},'entries':30,'active_training_seconds':2,
               'save_seconds':5,'elapsed_seconds':7,'stage_wall_seconds':10},
              {'counts':{'nodes':200},'entries':50,'active_training_seconds':4,
               'save_seconds':8,'elapsed_seconds':12,'stage_wall_seconds':19}]
        quote=pilot.quote_from_rows(rows)
        self.assertEqual(quote['intervals'][1]['active_nodes_per_second'],25)
        self.assertEqual(quote['intervals'][1]['keys_per_node'],.2)
        self.assertFalse(quote['full_training_admitted'])
        rows[1]['frozen_at']=27
        self.assertIsNone(pilot.quote_from_rows(rows)['uncapped_local_linear_entries']['3000000000'])
        rows[1]['active_training_seconds']=0
        with self.assertRaises(ValueError):pilot.quote_from_rows(rows)

    def test_no_duplicate_launch_even_after_completed_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'config.json').write_text('{}');(root/'launch.json').write_text('{}')
            with patch.object(pilot,'validate_config'):
                with self.assertRaisesRegex(ValueError,'attempt already exists'):
                    pilot.run(root,pilot.ALLOWANCE)

    def test_budget_must_be_explicit_and_never_launches_from_preparation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'config.json').write_text('{}')
            with patch.object(pilot,'validate_config'):
                with self.assertRaisesRegex(ValueError,'explicit acceptance'):
                    pilot.run(root,0)
            self.assertFalse((root/'launch.json').exists())


if __name__=='__main__':unittest.main()
