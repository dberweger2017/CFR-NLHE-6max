import unittest
from copy import deepcopy
import random

from scripts.river_conditional_evaluation import block_contrasts, calibration_roots
from scripts.assess_river_conditional_evaluation import admission, QUOTE_SHA, ratio_stats, verified_rows


class EstimatorTests(unittest.TestCase):
    def test_whole_hand_blocks_include_noneligible_zeros_and_unchanged_actions(self):
        roots=[{'id':'a','lineup':'trained','hand':0,'block':0,'permutation':0},
               {'id':'b','lineup':'trained','hand':8,'block':1,'permutation':2}]
        results={key:{'identity_verified':True,'complete_contrast':True,'contrast_chips':value}
                 for key,value in [('a',60.),('b',-30.)]}
        values=block_contrasts(roots,results)
        self.assertEqual(values['trained'][:3],[10.,-5.,0.])
        self.assertEqual(len(values['trained']),128)
        self.assertEqual(sum(values['call']),0.)
        self.assertEqual(sum(values['trained'])/128,5/128)

    def test_partial_coverage_partial_values_and_duplicate_hands_are_rejected(self):
        roots=[{'id':'a','lineup':'trained','hand':0,'block':0,'permutation':0}]
        result={'identity_verified':True,'complete_contrast':True,'contrast_chips':1.}
        with self.assertRaises(ValueError):block_contrasts(roots,{})
        with self.assertRaises(ValueError):block_contrasts(roots,{'a':{**result,'complete_contrast':False}})
        with self.assertRaises(ValueError):block_contrasts(roots+[dict(roots[0],id='b')],{'a':result,'b':result})

    def test_calibration_selects_public_ids_and_all_quality_misses_only(self):
        roots=[{'id':str(i),'lineup':'trained','expected':{'installed':i!=4},'sample_changed':False}
               for i in range(6)]
        self.assertEqual([r['id'] for r in calibration_roots(roots)],['0','1','4'])

    def test_assessment_requires_the_exact_accepted_quote_and_sufficient_allowance(self):
        q={'status':'calibrated','complete_roots':13,'incomplete_ids':[],
           'profile_identities_passed':True,'all384_two_pass_reserved_upper_seconds':13378.681089182908}
        self.assertTrue(admission(q,QUOTE_SHA,QUOTE_SHA,13379)['budget_is_not_elapsed_kill_guard'])
        for actual,accepted,budget in [(QUOTE_SHA,'wrong',13379),('wrong','wrong',13379),
                                      (QUOTE_SHA,QUOTE_SHA,13378),(QUOTE_SHA,QUOTE_SHA,float('inf'))]:
            with self.assertRaises(ValueError):admission(q,actual,accepted,budget)
        with self.assertRaises(ValueError):admission({**q,'incomplete_ids':['a']},QUOTE_SHA,QUOTE_SHA,13379)

    def expectation_rows(self):
        roots=[{'id':'a','expected':{'installed':True,'profile_sha256':'profile-a'}},
               {'id':'b','expected':{'installed':False,'profile_sha256':'profile-b'}}]
        arms={name:{'complete':True,'expected_chips':value,'visited':7,'seconds':.01}
              for name,value in [('on',12.),('off',10.)]}
        rows=[{'id':'a','identity_verified':True,'complete_contrast':True,'profile_sha256':'profile-a',
               'method':'full-positive-support-enumeration','contrast_chips':2.,**arms},
              {'id':'b','identity_verified':True,'complete_contrast':True,'profile_sha256':'profile-b',
               'method':'identical-blueprint-policy-cancellation','contrast_chips':0.,'on':None,'off':None}]
        return roots,rows

    def test_reproduction_checks_every_original_profile_and_float64_value_not_timing(self):
        roots,a=self.expectation_rows();b=deepcopy(a);b[0]['on']['seconds']=2.
        self.assertEqual(set(verified_rows(roots,a,b)),{'a','b'})
        for key,value in [('complete_contrast',False),('profile_sha256','changed'),('contrast_chips',2.000000000000001)]:
            b=deepcopy(a);b[0][key]=value
            with self.assertRaises(ValueError):verified_rows(roots,a,b)
        b=deepcopy(a);b[1]['contrast_chips']=-0.
        with self.assertRaises(ValueError):verified_rows(roots,a,b)
        with self.assertRaises(ValueError):verified_rows(roots,a,a[:1])

    def test_work_limit_or_nonfinite_values_cannot_reach_global_readout(self):
        roots,a=self.expectation_rows()
        for field,value in [('complete',False),('visited',200001),('expected_chips',float('nan'))]:
            b=deepcopy(a);b[0]['on'][field]=value
            with self.assertRaises(ValueError):verified_rows(roots,b,b)
        b=deepcopy(a);b[1]['method']='full-positive-support-enumeration'
        with self.assertRaises(ValueError):verified_rows(roots,b,b)

    def test_paired_bootstrap_keeps_block_count_and_no_intervention_is_undefined(self):
        x=[-30.,-10.,0.,10.,30.];y=[v/2 for v in x]
        result=ratio_stats(x,y,random.Random(2026102239001),100)
        self.assertEqual(result['blocks'],5)
        self.assertEqual(result['integrated_over_sampled_variance'],.25)
        self.assertEqual(result['variance_ratio_bootstrap95'],[.25,.25])
        zero=ratio_stats([0.]*128,[0.]*128,random.Random(2026102239001),10)
        self.assertIsNone(zero['integrated_over_sampled_variance'])
        self.assertIsNone(zero['variance_ratio_bootstrap95'])
        with self.assertRaises(ValueError):ratio_stats(x,y[:2],random.Random(1),10)


if __name__=='__main__':unittest.main()
