from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import nplayer_four_player_candidate as study
from scripts import plan_nplayer_four_player_candidate as pricing


class FourPlayerCandidateTests(unittest.TestCase):
    def test_fixed_game_targets_seating_counts_and_disjoint_fixture(self):
        c=study.fixed();q=study.fixed(True)
        self.assertEqual((c['players'],c['stack_bb'],c['seed']),(4,100,2026102341001))
        self.assertEqual(c['targets'],[3000000000,10000000000]);self.assertEqual(c['cap'],250000000)
        self.assertEqual(len(study.evidence.seating(4,c['schedule'])),24)
        self.assertEqual(c['blocks']*24*2*8,1572864)
        self.assertFalse(set(range(c['root_base'],c['root_base']+8))&set(range(q['root_base'],q['root_base']+8)))
        self.assertNotEqual(c['seed'],q['seed']);self.assertEqual(q['targets'],[100000,200000])

    def test_only_focal_changes_and_all_opponents_are_fixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=dict(study.fixed(),tables='/tables');m=study.manifest(Path(tmp),c,{},'first')
            self.assertEqual(len(m['cases']),8)
            for row,field in zip(m['cases'],c['fields']):
                self.assertEqual(row['focals'],['baseline','candidate']);self.assertEqual(row['opponents'],field['opponents'])
                self.assertEqual(row['schedule'],c['schedule']);self.assertEqual(len(row['traces']),2)
            self.assertEqual(m['cases'][0]['opponents'],['baseline']*3)
            self_case=study.manifest(Path(tmp),c,{},'self',self_only=True)['cases'][0]
            self.assertEqual(self_case['focals'],['baseline','baseline'])

    def test_recipe_resume_and_no_extra_resource_cutoffs(self):
        c=dict(study.fixed(),tables='/tables',binaries={'nplayer_train':'train'})
        parent=dict(checkpoint='/prior',sha256='pinned')
        args=study.four.train_command(c,Path('/out'),10000000000,c['seed'],c['cap'],parent,16)
        for option,value in (('--players','4'),('--stack-bb','100'),('--threads','16'),('--seed','2026102341001'),('--max-entries','250000000'),('--roots-per-seat','8'),('--resume-sha256','pinned')):
            self.assertEqual(args[args.index(option)+1],value)
        self.assertIn('--freeze-at-cap',args);self.assertNotIn('--prune-bb',args)
        self.assertTrue(c['no_time_rss_disk_swap_stop']);self.assertEqual(args[args.index('--max-seconds')+1],'1e100')

    def test_wrong_budget_or_existing_root_cannot_prepare_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'new'
            with self.assertRaisesRegex(ValueError,'acceptance required'):study.configure(root,None,False,accepted=1)
            self.assertFalse(root.exists())
            root.mkdir()
            with self.assertRaises(FileExistsError):study.configure(root,None,False,accepted=36000)

    def test_duplicate_attempt_cannot_reach_validation_or_science(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);study.write(root/'launch.json',dict(pid=1))
            with patch.object(study,'validate') as v,patch.object(study,'execute') as e:
                with self.assertRaises(FileExistsError):study.run(root)
                v.assert_not_called();e.assert_not_called()

    def test_mutated_targets_recipe_seeds_counts_schedule_and_guards_refused(self):
        for key,value in [('targets',[3000000000]),('seed',2),('cap',300000000),('threads',8),('players',3),('stack_bb',200),('pruning',True),('schedule',study.SCHEDULE[:4]),('fields',[]),('blocks',8192),('no_time_rss_disk_swap_stop',False)]:
            c=dict(study.fixed());c['fixed']=study.fixed();c[key]=value
            with self.subTest(key=key),patch.object(study,'source') as s:
                with self.assertRaisesRegex(ValueError,'scope changed'):study.validate(c)
                s.assert_not_called()

    def test_reproduction_failure_never_calls_statistical_readout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);a=root/'a';b=root/'b';a.write_text('old');b.write_text('changed')
            class NoStages:
                def stage(self,*args):raise AssertionError('must reject before replay')
            with self.assertRaisesRegex(ValueError,'reproduction differs'):
                study.verify_case(root,{},NoStages(),dict(name='field',traces=[str(a)]),dict(traces=[str(b)]))

    def test_binary_gzip_parity_normalizes_only_audited_source_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/'a',Path(tmp)/'b';models={'baseline':dict(sha256='binary',source_policy_sha256='gzip')}
            left={'identity':{'players':4},'policies':[{'sha256':'binary','mass_sha256':'mass'}]}
            right={'identity':{'players':4},'policies':[{'sha256':'gzip','mass_sha256':'mass'}]}
            a.write_text(json.dumps(left)+'\n'+json.dumps({'actions':['call']})+'\n')
            b.write_text(json.dumps(right)+'\n'+json.dumps({'actions':['call']})+'\n')
            study.trace_payload_parity(a,b,models)
            b.write_text(json.dumps(right)+'\n'+json.dumps({'actions':['fold']})+'\n')
            with self.assertRaisesRegex(ValueError,'payload differs'):study.trace_payload_parity(a,b,models)
            right['identity']['players']=3;b.write_text(json.dumps(right)+'\n')
            with self.assertRaisesRegex(ValueError,'header identity'):study.trace_payload_parity(a,b,models)

    def test_quote_is_metadata_only_complete_and_reproducible(self):
        q=pricing.proposal();committed=study.load(study.SOURCE/study.PROPOSAL)
        self.assertEqual(q,committed);self.assertEqual(q['initial_hands'],1572864)
        self.assertEqual(q['reproduction_hands'],1572864)
        self.assertAlmostEqual(sum(x['central_seconds'] for x in q['components']),q['central_seconds'])
        self.assertAlmostEqual(sum(x['reserved_seconds'] for x in q['components']),q['reserved_seconds'])
        self.assertGreaterEqual(q['proposed_allocation_seconds'],q['reserved_seconds'])
        self.assertEqual(q['proposed_allocation_seconds'],36000)
        self.assertIn('unknown',q['limits'])
        self.assertEqual(q['storage']['requested_free_bytes'],sum(q['storage'][k] for k in ('model_derivatives_scenario_bytes','all_trace_scenario_bytes','manual_headroom_bytes')))


if __name__=='__main__':unittest.main()
