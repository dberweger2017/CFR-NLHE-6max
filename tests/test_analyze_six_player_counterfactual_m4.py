import math
import unittest
from scripts.analyze_six_player_counterfactual_m4 import contrast, choose_discovery, root_summary, DISCOVERY, HELDOUT, FAMILY

class ReadoutTests(unittest.TestCase):
    def test_constant_exhaustive_action_values_and_frozen_mixture(self):
        root=dict(id='oracle',hero=0,street=3,stratum='oracle',actions=[['fold',0],['call',0]],probabilities=[.25,.75],status='positive_mass')
        discovery=[[2.,8.]]*DISCOVERY
        heldout=[dict(values=[2.,8.],lookups=[1,2,3]) for _ in range(HELDOUT)]
        r=root_summary(root,discovery,heldout)
        self.assertEqual(r['selected_action_index'],1)
        self.assertEqual(r['blueprint_value_bb'],6.5)
        self.assertEqual(r['selected_minus_blueprint']['mean_bb'],1.5)
        self.assertEqual(r['action_values'][0]['minus_blueprint']['mean_bb'],-4.5)
        self.assertEqual(r['heldout_continuation_lookups']['missing'],3*HELDOUT)
        self.assertEqual(r['action_values'][0]['minus_passive']['mean_bb'],-6.)
        self.assertEqual(r['action_values'][1]['minus_passive']['lower95_family_bb'],0.)
        self.assertLessEqual(r['action_values'][0]['minus_passive']['lower95_family_bb'],-6.)
        self.assertGreaterEqual(r['action_values'][0]['minus_passive']['upper95_family_bb'],-6.)
        self.assertEqual(r['selected_minus_blueprint']['standard_error_bb'],0.)
        width=600*(.25+.25)
        expected=7*width*math.log(4*FAMILY/.05)/(3*(HELDOUT-1))
        self.assertAlmostEqual(r['selected_minus_blueprint']['lower95_family_bb'],1.5-expected)

    def test_heldout_cannot_reselect_and_discovery_ties_use_menu_order(self):
        self.assertEqual(choose_discovery([[4.,4.]]*DISCOVERY),0)
        root=dict(id='test',hero=1,street=0,stratum='test',actions=[['fold',0],['call',0]],probabilities=[1.,0.],status='positive_mass')
        result=root_summary(root,[[1.,0.]]*DISCOVERY,[dict(values=[0.,100.],lookups=[0,0,0]) for _ in range(HELDOUT)])
        self.assertEqual(result['selected_action_index'],0)
        self.assertEqual(result['selected_minus_blueprint']['mean_bb'],0.)
        self.assertEqual(result['selected_minus_blueprint']['range_width_bb'],0.)

    def test_paired_common_noise_cancels_and_zero_contrast_is_exact(self):
        qs=[[(-1.)**i,2.+(-1.)**i] for i in range(HELDOUT)]
        r=contrast(qs,[-1.,1.])
        self.assertEqual(r['mean_bb'],2.)
        self.assertEqual(r['standard_error_bb'],0.)
        z=contrast(qs,[0.,0.])
        self.assertEqual((z['mean_bb'],z['lower95_family_bb'],z['upper95_family_bb']),(0.,0.,0.))

    def test_bad_counts_nonfinite_out_of_range_and_shapes_refuse(self):
        for qs in [[[0.,0.]]*(HELDOUT-1),[[math.nan,0.]]*HELDOUT,[[501.,0.]]*HELDOUT,[[0.]]*HELDOUT]:
            with self.assertRaises(ValueError):contrast(qs,[-1.,1.])
        with self.assertRaises(ValueError):choose_discovery([[1.,2.]]*(DISCOVERY-1))


class ProofReadoutTests(unittest.TestCase):
    def make_evidence(self, folder, defect=None):
        import json
        from pathlib import Path
        from scripts.six_player_counterfactual_m4 import sha
        root=Path(folder)
        native=root/'native';native.mkdir()
        profile=dict(id='fixture',hero=0,street=0,stratum='fixture',
                     actions=[['fold',0],['call',0]],probabilities=[.25,.75],
                     status='positive_mass')
        (native/'roots.jsonl').write_text(json.dumps(profile)+'\n')
        with (native/'worlds.jsonl').open('w') as f:
            for phase,count in [('discovery',DISCOVERY),('heldout',HELDOUT)]:
                for i in range(count):
                    index=0 if defect=='duplicate' and phase=='heldout' and i==1 else i
                    f.write(json.dumps(dict(id='fixture',phase=phase,world=index,values=[2.,8.],lookups=[0,0,0]))+'\n')
        (native/'worlds.repeat.jsonl').write_bytes((native/'worlds.jsonl').read_bytes())
        state_pin='d'*64
        receipt=dict(status='passed',full_panel_work=True,discovery_worlds=DISCOVERY,heldout_worlds=HELDOUT,
                     float64_and_work_reproduced=True,root_profiles_reproduced=True,
                     qualification_only=True,main_started=False,roots=1,states_sha256=state_pin)
        for name,key in [('roots.jsonl','roots_sha256'),('worlds.jsonl','worlds_sha256'),('worlds.repeat.jsonl','worlds_repeat_sha256')]:
            receipt[key]=sha(native/name)
        (native/'verified.json').write_text(json.dumps(receipt))
        inventory=root/'inventory.json';inventory.write_text(json.dumps(dict(roots=1,states_sha256=state_pin)))
        return native,inventory

    def test_complete_fixture_readout_and_hash_bound_csv(self):
        import tempfile
        from pathlib import Path
        from scripts.analyze_six_player_counterfactual_m4 import readout
        with tempfile.TemporaryDirectory() as folder:
            native,inventory=self.make_evidence(folder)
            r=readout(native,inventory,Path(folder)/'out',fixture=True)
            self.assertEqual(r['status'],'settled')
            self.assertEqual(r['roots'],1)
            self.assertEqual(r['panel'][0]['selected_minus_blueprint']['mean_bb'],1.5)
            self.assertTrue(r['no_whole_hand_strength_verdict'])

    def test_duplicate_worlds_and_unverified_bytes_refuse(self):
        import tempfile
        from pathlib import Path
        from scripts.analyze_six_player_counterfactual_m4 import readout
        for defect in ['duplicate','changed-bytes']:
            with self.subTest(defect=defect),tempfile.TemporaryDirectory() as folder:
                native,inventory=self.make_evidence(folder,defect)
                if defect=='changed-bytes':
                    with (native/'worlds.jsonl').open('a') as f:f.write('{}\n')
                with self.assertRaises(ValueError):
                    readout(native,inventory,Path(folder)/'out',fixture=True)

if __name__=='__main__':unittest.main()
