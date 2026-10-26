from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import nplayer_six_player_capacity as study
from scripts import plan_nplayer_six_player_capacity as pricing


class CapacityTests(unittest.TestCase):
    def test_one_fresh_cap_intervention_at_matched_nodes(self):
        c=study.fixed();self.assertEqual((c['seed'],c['target'],c['cap'],c['control_cap']),(2026102361001,10_000_000_000,500_000_000,250_000_000));self.assertTrue(c['fresh_candidate'])
        c=dict(c,tables='/tables',binaries=dict(nplayer_train='train'))
        args=study.four.train_command(c,Path('/new'),c['target'],c['seed'],c['cap'],None,16)
        self.assertNotIn('--resume',args);self.assertNotIn('--prune-bb',args)
        for key,value in [('--nodes','10000000000'),('--max-entries','500000000'),('--threads','16'),('--roots-per-seat','8'),('--max-seconds','1e100')]:self.assertEqual(args[args.index(key)+1],value)
        with self.assertRaisesRegex(ValueError,'from scratch'):study.train(None,c,None,'candidate',c['cap'],c['target'],dict(checkpoint='old'))

    def test_control_and_peer_are_distinct_and_fixed_across_arms(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);c=dict(study.fixed(),tables='/k50');models={a:dict(path=a,sha256=a) for a in ['control','candidate','peer']}
            m=study.manifest(root,c,models,'initial')
            self.assertEqual(set(m['models']),{'control','candidate','peer'});self.assertEqual(m['cases'][0]['opponents'],['peer']*5)
            self.assertEqual(m['cases'][-1]['opponents'],['peer','bot=check-call','bot=check-call','bot=pot-pressure','bot=pot-pressure'])
            for case in m['cases']:
                self.assertEqual(case['focals'],['control','candidate']);self.assertEqual(case['shared_models'],['control','candidate']);self.assertNotIn('control',case['opponents']);self.assertNotIn('candidate',case['opponents'])
            off=study.manifest(root,c,models,'off',diagnostics=False)
            self.assertTrue(all('shared_models' not in case for case in off['cases']))

    def test_fresh_deal_roots_counts_and_seating_not_extra_observations(self):
        c=study.fixed();smoke=study.fixed(True)
        self.assertEqual((c['root_base'],smoke['root_base']),(20261024650001,20261024659901));self.assertNotEqual(c['seed'],smoke['seed'])
        self.assertEqual(8*c['blocks']*len(c['schedule'])*2,786432)
        self.assertEqual(len(study.evidence.seating(6,c['schedule'])),12)
        for identity in range(6):
            for seat in range(6):self.assertEqual(sum(r[seat]==identity for r in c['schedule']),2)

    def test_frozen_scope_mutation_fails_before_source_or_compute(self):
        for key,value in [('players',5),('target',15_000_000_000),('cap',250_000_000),('seed',2),('fields',[]),('blocks',8192),('shared_models',['peer','candidate']),('resource_stops','ignore'),('no_time_rss_disk_swap_stop',False),('fresh_candidate',False)]:
            c=dict(study.fixed(),fixed=study.fixed());c[key]=value
            with patch.object(study,'source') as source:
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'scope changed'):study.validate(c)
                source.assert_not_called()

    def test_main_cannot_configure_without_owner_quote_and_qualification(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'main'
            with patch.object(study,'source') as source:
                with self.assertRaisesRegex(ValueError,'owner accepted quote'):study.configure(root,None)
                source.assert_not_called()
            self.assertFalse(root.exists())

    def test_existing_output_is_never_reused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'launch.json').write_text('original')
            with patch.object(study,'validate') as validate:
                with self.assertRaises(FileExistsError):study.run(root)
                validate.assert_not_called()
            self.assertEqual((root/'launch.json').read_text(),'original')
            with self.assertRaises(FileExistsError):study.configure(root,None,True)

    def test_quote_counts_third_model_and_keeps_budget_unaccepted(self):
        q=pricing.proposal();self.assertEqual(q,study.load(study.SOURCE/study.PROPOSAL));self.assertIsNone(q['accepted_planning_seconds'])
        self.assertEqual(q['arena_resident_models'],3);self.assertGreater(q['linear_arena_peak_gib'],50);self.assertEqual(q['storage']['new_free_scenario_gib'],120);self.assertTrue(q['storage']['headroom_included'])
        self.assertAlmostEqual(q['central_seconds'],sum(c['central_seconds'] for c in q['components']));self.assertAlmostEqual(q['reserved_seconds'],sum(c['reserved_seconds'] for c in q['components']))
        self.assertLess(q['reserved_seconds'],q['proposed_planning_seconds']);self.assertEqual(q['initial_hand_instances'],786432)
        self.assertEqual(len(q['reference_power']),8);self.assertTrue(q['no_training_or_main_started'])


if __name__=='__main__':unittest.main()
