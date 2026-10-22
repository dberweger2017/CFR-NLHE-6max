import copy
import math
import unittest

from scripts.river_fresh_screen import block_values, describe, expectation_proof, tail_blocks


class FreshScreenTests(unittest.TestCase):
    def fixture(self):
        key='trained/0003/0002'
        expected={key:{'hand':3,'block':0,'permutation':3,'expected':{'installed':True,'profile_sha256':'fixed'}}}
        arm={'complete':True,'expected_chips':5.,'visited':3,'terminals':2,'policy_rows':{'blueprint':1}}
        row={'id':key,'method':'full-positive-support-enumeration','complete_contrast':True,
             'contrast_chips':6.,'profile_sha256':'fixed','on':{**arm,'expected_chips':11.},'off':arm,
             'solver_advances':0,'profile_reconstructions':0}
        return expected,row

    def test_noneligible_hands_and_blocks_are_kept_in_denominator(self):
        expected,row=self.fixture()
        values=block_values(expected,[row],2)
        self.assertEqual(values,[1.,0.])
        self.assertEqual(describe(values,2.,3.)['mean_bb100'],.5)
        bad=copy.deepcopy(expected);next(iter(bad.values()))['permutation']=2
        with self.assertRaises(ValueError):block_values(bad,[row],2)

    def test_required_complete_unique_finite_values_and_exact_profile(self):
        expected,row=self.fixture()
        for rows in ([],[row,row]):
            with self.assertRaises(ValueError):expectation_proof(expected,rows)
        for k,v in [('profile_sha256','wrong'),('solver_advances',1),('contrast_chips',math.inf),('complete_contrast',False)]:
            bad=copy.deepcopy(row);bad[k]=v
            with self.assertRaises(ValueError):expectation_proof(expected,[bad])
        bad=copy.deepcopy(row);bad['on']['complete']=False
        with self.assertRaises(ValueError):expectation_proof(expected,[bad])

    def test_quality_fallback_cancels_only_identical_policies(self):
        expected,row=self.fixture();next(iter(expected.values()))['expected']['installed']=False
        row.update(method='identical-blueprint-policy-cancellation',on=None,off=None,contrast_chips=0.)
        self.assertEqual(block_values(expected,[row],2),[0.,0.])
        row['contrast_chips']=1.
        with self.assertRaises(ValueError):expectation_proof(expected,[row])

    def test_known_intervals_variation_shares_and_zero_variance_not_pass(self):
        result=describe([-1.,1.],2.,3.)
        self.assertEqual(result['pointwise95_bb100'],[-2.,2.])
        self.assertEqual(result['family95_bb100'],[-3.,3.])
        self.assertEqual(result['centered_square_concentration']['1'],.5)
        zero=describe([0.,0.],2.,3.)
        self.assertIsNone(zero['family95_bb100']);self.assertTrue(zero['zero_variance_is_not_a_pass'])

    def test_predeclared_positive_negative_tail_selection_and_empty_root_examples(self):
        values=[-5.,10.,0.,-7.,2.,1.]
        tails=tail_blocks(values,{}, {})
        self.assertEqual([x['block'] for x in tails],[1,4,5,3,0])
        self.assertTrue(all(x['examples']==[] for x in tails))
        self.assertAlmostEqual(tails[0]['uncentered_square_share'],100/179)
        mean=sum(values)/6;denominator=sum((x-mean)**2 for x in values)
        self.assertAlmostEqual(tails[0]['centered_square_share'],(10-mean)**2/denominator)


if __name__=='__main__':unittest.main()
