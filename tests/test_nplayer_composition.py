import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch
from scripts import nplayer_composition_evidence as c
from scripts import nplayer_missing_row_composition as campaign


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

    def test_prospective_field_and_seating_inventory(self):
        fixed=campaign.fixed();self.assertEqual(fixed['blocks'],4096)
        self.assertEqual(len(fixed['fields']),8);self.assertEqual(len(fixed['schedule']),12)
        for identity in range(6):
            for seat in range(6):self.assertEqual(sum(row[seat]==identity for row in fixed['schedule']),2)
        self.assertEqual(fixed['fields'][0]['opponents'],['peer']*5)
        self.assertTrue(fixed['no_training_or_exports']);self.assertTrue(fixed['no_extension'])

    def test_unaccepted_budget_fails_before_model_access(self):
        with tempfile.TemporaryDirectory() as d:
            owner=Path(d)/'owner.json';owner.write_text('{}')
            config=dict(fixed=campaign.fixed(),proposal_sha256=campaign.tools.sha(campaign.PROPOSAL),owner=str(owner),owner_sha256=campaign.tools.sha(owner))
            with patch.object(campaign,'protected_models') as models:
                with self.assertRaisesRegex(ValueError,'accepted exact owner'):campaign.validate(config)
                models.assert_not_called()


if __name__=='__main__':unittest.main()
