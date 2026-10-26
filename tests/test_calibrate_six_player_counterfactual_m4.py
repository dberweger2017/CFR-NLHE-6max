import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import calibrate_six_player_counterfactual_m4 as c
from scripts.six_player_counterfactual_m4 import MODEL

class CalibrationGuardTests(unittest.TestCase):
    def sample(self, **changes):
        row=dict(thermal_state='nominal',worker_family_rss_bytes=100,
                 available_ram_bytes=8*2**30,disk_free_bytes=20*2**30,pressure=1)
        row.update(changes)
        return row

    def test_unresolved_review_cannot_admit_calibration(self):
        cfg=dict(format='six-player-conditional-calibration-v1',mode='calibrate',
                 belief_root=20261026437002,threads=2,model_sha256=MODEL,
                 independent_review=dict(resolved=False,receipt_sha256='a'*64))
        with self.assertRaisesRegex(ValueError,'review unresolved'):
            c.validate_config(cfg)

    def test_resource_or_thermal_stop_reaps_only_owned_child_and_records_cost(self):
        for change in [dict(pressure=4),dict(available_ram_bytes=1),
                       dict(disk_free_bytes=1),dict(thermal_state='serious')]:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as folder:
                root=Path(folder)
                (root/'config.json').write_text('{}')
                (root/'manifest.json').write_text('import time\ntime.sleep(30)\n')
                config=dict(binary=sys.executable,thermal='mock')
                with patch.object(c,'sample',return_value=self.sample(**change)):
                    with self.assertRaises(RuntimeError):c.run_guarded(root,config)
                cost=json.loads((root/'stage-costs.json').read_text())[0]
                self.assertIsNotNone(cost['returncode'])
                self.assertNotEqual(cost['returncode'],0)
                self.assertLess(cost['wall_seconds'],10)
                self.assertTrue((root/'resources.jsonl').is_file())

    def test_guard_retains_successful_child_exit_and_stdout(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'config.json').write_text('{}')
            (root/'manifest.json').write_text('print("finished")\n')
            with patch.object(c,'sample',return_value=self.sample()):
                cost=c.run_guarded(root,dict(binary=sys.executable,thermal='mock'))
            self.assertEqual(cost['returncode'],0)
            self.assertEqual((root/'measurements/mature-calibration/stdout.log').read_text(),'finished\n')

if __name__=='__main__':unittest.main()
