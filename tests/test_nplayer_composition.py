import unittest
from scripts import nplayer_composition_evidence as c


class CompositionEvidence(unittest.TestCase):
    def test_all_presence_mass_combinations(self):
        positive=(0,0,5,[0.75,0.25],'positive_mass')
        zero=(0,0,5,[0.5,0.5],'zero_mass')
        for base in [positive,zero,None]:
            for donor in [positive,zero,None]:
                result,status=c.selection(base,donor,2)
                if base is not None:
                    self.assertEqual(result['source'],'base');self.assertEqual(result['probabilities'],base[3]);self.assertEqual(status,base[-1])
                elif donor is positive:self.assertEqual(result['source'],'donor')
                else:self.assertEqual(result['source'],'uniform');self.assertEqual(status,'missing')

    def test_original_mass_not_distribution_shape(self):
        learned_uniform=(0,0,5,[0.5,0.5],'positive_mass')
        self.assertEqual(c.selection(None,learned_uniform,2)[0]['source'],'donor')
        self.assertEqual(c.selection((0,0,5,[0.5,0.5],'zero_mass'),learned_uniform,2)[0]['source'],'base')

    def test_exact_float64_including_sign_of_zero(self):
        self.assertTrue(c.same_float64([0.25,0.75],[0.25,0.75]))
        self.assertFalse(c.same_float64([0.],[float('-0')]))
        self.assertFalse(c.same_float64([0.5],[0.5+1e-15]))

    def test_empty_menu_refuses(self):
        with self.assertRaises(ValueError):c.selection(None,None,0)


if __name__=='__main__':unittest.main()
