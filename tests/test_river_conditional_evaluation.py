import unittest

from scripts.river_conditional_evaluation import block_contrasts, calibration_roots


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


if __name__=='__main__':unittest.main()
