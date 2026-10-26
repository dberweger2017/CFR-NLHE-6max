from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import nplayer_six_player_candidate as study
from scripts import plan_nplayer_six_player_candidate as pricing


class SixPlayerCandidateTests(unittest.TestCase):
    def test_exact_targets_contrasts_and_balanced_seatings(self):
        c=study.fixed();self.assertEqual(c['targets'],[3e9,6e9,10e9,15e9]);self.assertEqual(len(c['contrasts']),5)
        self.assertEqual(c['seed'],2026102361001);self.assertEqual(len(study.evidence.seating(6,c['schedule'])),12)
        self.assertEqual(8*c['blocks']*12*2*3,2359296);self.assertEqual(8*c['blocks']*12*4,1572864)
        self.assertNotEqual(c['seed'],study.fixed(True)['seed'])
        for identity in range(6):
            for seat in range(6):self.assertEqual(sum(r[seat]==identity for r in c['schedule']),2)
    def test_fixed_five_opponent_fields_all_checkpoints(self):
        with tempfile.TemporaryDirectory() as t:
            models={tag:dict(path=tag,sha256=tag) for tag in study.TAGS};c=dict(study.fixed(),tables='/tables')
            for tag in study.TAGS[1:]:
                m=study.manifest(Path(t),c,models,tag,'initial')
                self.assertEqual(m['models']['baseline'],models['3b']);self.assertEqual(m['models']['candidate'],models[tag])
                self.assertEqual(len(m['cases']),8)
                for row,field in zip(m['cases'],c['fields']):self.assertEqual(row['opponents'],field['opponents']);self.assertEqual(len(row['opponents']),5)
                self.assertEqual(m['cases'][0]['opponents'],['baseline']*5)
    def test_cross_case_uses_candidate_arms_and_first_baseline(self):
        def record(tag):return dict(tag=tag,record=dict(initial=dict(traces=[tag+'a',tag+'b']),repeat=dict(traces=[tag+'ra',tag+'rb']),proofs=[tag+'pa',tag+'pb']))
        z=study.cross_case('trained',record('6b'),record('10b'));self.assertEqual(z['traces'],['6bb','10bb']);self.assertEqual(z['proofs'],['6bpb','10bpb'])
        z=study.cross_case('trained',record('3b'),record('15b'));self.assertEqual(z['traces'],['3ba','15bb'])
    def test_recipe_resume_and_only_temperature_resource_stops(self):
        c=dict(study.fixed(),tables='/tables',binaries=dict(nplayer_train='train'));parent=dict(checkpoint='/old',sha256='pin')
        args=study.four.train_command(c,Path('/out'),15_000_000_000,c['seed'],c['cap'],parent,16)
        for k,v in (('--players','6'),('--threads','16'),('--roots-per-seat','8'),('--max-entries','250000000'),('--resume-sha256','pin'),('--max-seconds','1e100')):self.assertEqual(args[args.index(k)+1],v)
        self.assertNotIn('--prune-bb',args);self.assertTrue(c['no_time_rss_disk_swap_stop'])
    def test_mutated_fixed_scope_fails_before_source_or_work(self):
        for k,v in [('players',5),('targets',[3e9,10e9]),('seed',1),('contrasts',[]),('blocks',8192),('fields',[]),('cap',500000000),('threads',8),('resource_stops','skip'),('no_time_rss_disk_swap_stop',False)]:
            c=dict(study.fixed(),fixed=study.fixed());c[k]=v
            with patch.object(study,'source') as s:
                with self.assertRaisesRegex(ValueError,'scope changed'):study.validate(c)
                s.assert_not_called()
    def test_existing_attempt_and_wrong_budget_never_launch(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);study.write(root/'launch.json',dict(pid=123))
            with patch.object(study,'validate') as v:
                with self.assertRaises(FileExistsError):study.run(root)
                v.assert_not_called()
            with self.assertRaisesRegex(ValueError,'allocation required'):study.configure(root/'next',None,False,accepted=1)
    def test_quote_exact_arithmetic_and_fixed12h_scope(self):
        q=pricing.proposal();self.assertEqual(q,study.load(study.SOURCE/study.PROPOSAL));self.assertLessEqual(q['reserved_seconds'],43200)
        self.assertEqual(q['accepted_planning_seconds'],43200);self.assertEqual(q['physical_initial_instances'],2359296)
        self.assertEqual(q['unique_initial_instances'],1572864);self.assertEqual(q['storage']['provisional_free_bytes'],240*2**30)
        self.assertAlmostEqual(sum(r['central_seconds'] for r in q['components']),q['central_seconds'])
        self.assertAlmostEqual(sum(r['reserved_seconds'] for r in q['components']),q['reserved_seconds'])
    def test_reproduction_failure_is_before_replay(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=Path(t)/'a',Path(t)/'b';a.write_text('a');b.write_text('b')
            class NoWork:
                def stage(self,*args):raise AssertionError('must reject first')
            with self.assertRaisesRegex(ValueError,'reproduction differs'):study.verify_case(Path(t),{},NoWork(),dict(traces=[a]),dict(traces=[b]),'test')
