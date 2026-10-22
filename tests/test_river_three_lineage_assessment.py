import copy
import json
from pathlib import Path
import statistics
import tempfile
import unittest
from unittest.mock import patch

from scripts.river_three_lineage_assessment import (
    ALLOWANCE, BLOCKS, FINAL_ROOTS, LINEUPS, POLICY_SHA, QUAL_ROOTS, SEEDS,
    bounds, decision, make_manifest, native_identity, preflight_quote, summarize_lineup, validate_cases,
)
from scripts.run_river_three_lineage_assessment import admit_quote, execution_authorization, validate_config
from scripts.river_whole_hand_pilot import manifest, read
from types import SimpleNamespace


class ThreeLineageTests(unittest.TestCase):
    def config(self):
        return {'models':['/nvme/003.bin','/nvme/601.bin','/nvme/602.bin'],'k50':'/k50',
            'planning_allowance_seconds':ALLOWANCE,'threads':4,'seeds':list(SEEDS),
            'fresh_roots':list(FINAL_ROOTS),'qualification_roots':list(QUAL_ROOTS),
            'blocks':BLOCKS,'policy_sha256s':list(POLICY_SHA),'scripted_margin_bb100':-5,
            'final_assessment_no_extension':True,'binary_sha256':'a'*64}

    def test_all_models_roots_counts_and_unchanged_native_settings(self):
        config=self.config(); all_roots=set(); total=0
        reference=manifest(SimpleNamespace(focal=Path('/unused'),peer=Path('/unused2'),k50=Path('/k50')),Path('/out'),'main',4,4)
        for i in range(3):
            m=make_manifest(config,Path('/out'),i)
            validate_cases(m,config,Path('/out'),i)
            self.assertEqual(m['threads'],4)
            self.assertEqual(m['models']['focal']['sha256'],POLICY_SHA[i])
            self.assertEqual(m['models']['peer']['sha256'],POLICY_SHA[(i+1)%3])
            for c in m['cases']:
                old=next(x for x in reference['cases'] if x['name']==c['name'])
                changed={k for k in set(c)|set(old) if c.get(k)!=old.get(k)}
                self.assertTrue(changed<= {'blocks','root','expectations'})
                self.assertEqual(c['opponents'],['peer','peer'] if c['name'].startswith('trained') else ['bot=check-call','bot=pot-pressure'])
                all_roots.add(c['root']); total+=c['blocks']*6
        self.assertEqual(all_roots,set(FINAL_ROOTS)); self.assertEqual(total,221184)
        self.assertEqual(2*total,442368)
        self.assertFalse(set(QUAL_ROOTS)&set(FINAL_ROOTS))

    def test_qualification_is_disjoint_and_manifest_mutation_rejected(self):
        c=self.config()
        for i in (1,2):
            m=make_manifest(c,Path('/out'),i,True)
            self.assertEqual({x['blocks'] for x in m['cases']},{4})
            self.assertTrue({x['root'] for x in m['cases']}<=set(QUAL_ROOTS))
            changed=copy.deepcopy(m);changed['cases'][0]['blocks']=2048
            with self.assertRaises(ValueError):validate_cases(changed,c,Path('/out'),i,True)
        known=make_manifest(c,Path('/out'),0,True)
        self.assertEqual({x['root'] for x in known['cases']},{2026102138801,2026102138805})

    def test_literal_pins_match_accepted_proposal_and_config_rejects_scope_change(self):
        proposal=read(Path(__file__).resolve().parents[1]/'docs/reports/river-fresh-screen/followup-proposal.json')
        self.assertEqual(tuple(proposal['lineages']),SEEDS)
        self.assertEqual(tuple(proposal['fresh_roots_by_focal_then_lineup']),FINAL_ROOTS)
        self.assertTrue(all(len(x)==64 for x in POLICY_SHA))
        c=self.config();validate_config(c)
        for k,v in [('threads',8),('scripted_margin_bb100',-10),('planning_allowance_seconds',50000),
                    ('final_assessment_no_extension',False),('fresh_roots',list(QUAL_ROOTS))]:
            bad=copy.deepcopy(c);bad[k]=v
            with self.assertRaises(ValueError):validate_config(bad)

    def test_separate_one_sided_three_test_bounds_and_zero_variance_not_pass(self):
        from scipy.stats import t
        values=[-1.,1.,2.,4.];x=bounds(values)
        expected=statistics.mean(values)-t.ppf(1-.05/3,3)*statistics.stdev(values)/2
        self.assertAlmostEqual(x['family_one_sided95_lower_bb100'],expected)
        self.assertNotIn('family95_bb100',x)
        self.assertEqual(x['family_size'],3)
        self.assertIsNone(bounds([2.,2.])['family_one_sided95_lower_bb100'])

    def test_final_closeout_no_cherry_picked_lineages_or_extension(self):
        rows=[{'focal_seed':s,'lineup':n,'gate_passed':True,'material_harm_established':False} for s in SEEDS for n in LINEUPS]
        self.assertTrue(decision(rows)['all_six_gates_passed'])
        rows[2]['gate_passed']=False
        self.assertEqual(decision(rows)['project_decision'],'defer-frozen-candidate-resume-blueprint-progress')
        rows[2]['material_harm_established']=True
        self.assertEqual(decision(rows)['project_decision'],'reject-frozen-candidate')
        with self.assertRaises(ValueError):decision(rows[:-1])
        with self.assertRaises(ValueError):decision(rows[:-1]+[rows[0]])

    def test_per_seat_and_whole_hand_expected_accounting_keeps_zero_hands(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);(base/'initial').mkdir();cases=[];expected={};evaluated={}
            permutations=[(0,1,2),(0,2,1),(1,0,2),(1,2,0),(2,0,1),(2,1,0)]
            for enabled in (False,True):
                trace=base/('on.jsonl' if enabled else 'off.jsonl');metrics=base/'metrics.jsonl'
                hands=[]
                for h in range(12):
                    ledger=None
                    if enabled and h in (0,8):
                        key=f'trained/{h:04d}/0000';value=12. if h==0 else -6.
                        search={'installed':True,'profile_sha256':key,'fallback_reason':None}
                        ledger={'mode':'root','search':search,'eligibility':'supported','blueprint_found':True,
                            'actions':[['check',0]],'probabilities':[1.],'blueprint_action':['check',0]}
                        expected[key]={'id':key,'hand':h,'block':h//6,'permutation':h%6,'decision':0,
                            'expected':search,'ledger':ledger,'public_state':{'board':[],'pot':100},
                            'focal_hole':[0,1],'chosen_action':['check',0],'blueprint_probabilities':[1.]}
                        arm={'complete':True,'expected_chips':0.,'visited':1,'terminals':1,'policy_rows':{}}
                        evaluated[key]={'id':key,'method':'full-positive-support-enumeration','complete_contrast':True,
                            'contrast_chips':value,'profile_sha256':key,'on':{**arm,'expected_chips':value},'off':arm,
                            'solver_advances':0,'profile_reconstructions':0}
                    hands.append({'hand':h,'block':h//6,'identities':permutations[h%6],
                        'rewards':[0,0,0],'search_ledgers':[ledger]})
                trace.write_text('{}\n'+''.join(json.dumps(h)+'\n' for h in hands))
                cases.append({'name':'trained-'+('on' if enabled else 'off'),'search':enabled,
                    'trace':str(trace),'metrics':str(metrics)})
            metrics.write_text(''.join(json.dumps({'mode':'root','seconds':1.})+'\n' for _ in range(2)))
            (base/'initial/manifest.json').write_text(json.dumps({'cases':cases}))
            with patch.dict(BLOCKS,{'trained':2}):
                result=summarize_lineup(base,'trained',expected,evaluated)
            self.assertEqual(result['integrated']['mean_bb100'],.5)
            self.assertEqual(result['per_seat']['0']['integrated_descriptive']['mean_bb100'],3.)
            self.assertEqual(result['per_seat']['1']['integrated_descriptive']['mean_bb100'],-1.5)
            self.assertEqual(result['per_seat']['2']['integrated_descriptive']['mean_bb100'],0.)
            self.assertEqual(result['sampled']['mean_bb100'],0.)
            self.assertEqual(result['counts']['root_installed'],2)

    def test_native_identity_only_allows_the_harness_count_limit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);a=root/'new';b=root/'old';name='native/hu20-trainer/examples/nplayer_river_arena.rs'
            (a/name).parent.mkdir(parents=True);(b/name).parent.mkdir(parents=True)
            (b/name).write_text('if !(1..=1024).contains(&blocks) {}')
            (a/name).write_text('if !(1..=4096).contains(&blocks) {}')
            self.assertTrue(native_identity(a,b,[name])['player_solver_library_byte_identical'])
            (a/name).write_text('if !(1..=4096).contains(&blocks) { change_player(); }')
            with self.assertRaises(ValueError):native_identity(a,b,[name])

    def test_explicit_owner_override_is_source_bound_and_does_not_change_counts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertIsNone(execution_authorization(root,'same','same'))
            with self.assertRaises(RuntimeError):execution_authorization(root,'old','new')
            quote={'status':'quote-exceeds-allowance','reserved_seconds':50000}
            with self.assertRaises(RuntimeError):admit_quote(quote,None)
            path=root/'owner-budget-authorization.json'
            approval={'pr':398,'approved':True,'fixed_counts_unchanged':True,'bootstrap_source':'old',
                'execution_source':'new','proceed_regardless_of_preflight_quote':True,
                'approval_text':'Owner is sleeping: run the fixed run regardless.'}
            path.write_text(json.dumps(approval))
            authorization=execution_authorization(root,'old','new')
            admitted=admit_quote(quote,authorization)
            self.assertEqual(admitted['status'],'admitted-owner-override')
            self.assertEqual(admitted['reserved_seconds'],50000)
            self.assertFalse(admitted['within_original_planning_allowance'])
            self.assertEqual(BLOCKS,{'trained':2048,'call-pressure':4096})
            for field,value in [('execution_source','other'),('fixed_counts_unchanged',False),('approved',False)]:
                path.write_text(json.dumps({**approval,field:value}))
                with self.assertRaises(RuntimeError):execution_authorization(root,'old','new')

    def test_cost_only_admission_uses_slowest_lineage_and_refuses_overbudget(self):
        p=read(Path(__file__).resolve().parents[1]/'docs/reports/river-fresh-screen/followup-proposal.json')
        q={'batches':{arm:{'startup':{'model_and_k50_load_seconds':200},
            'case_play_seconds':{n+'-'+a:.01 for n in LINEUPS for a in ('on','off')}} for arm in ('initial','repeat')}}
        costs=[copy.deepcopy(q) for _ in range(3)]
        admitted=preflight_quote(p,costs,1000)
        self.assertEqual(admitted['status'],'admitted')
        self.assertAlmostEqual(admitted['reserved_seconds'],p['reserved_seconds'])
        costs[2]['batches']['repeat']['case_play_seconds']['call-pressure-on']=20
        rejected=preflight_quote(p,costs,1000)
        self.assertEqual(rejected['status'],'quote-exceeds-allowance')
        self.assertTrue(rejected['cost_only_no_outcomes'])
        self.assertFalse(rejected['main_started'])
        with self.assertRaises(ValueError):preflight_quote(p,costs[:2],1000)


if __name__=='__main__':unittest.main()
