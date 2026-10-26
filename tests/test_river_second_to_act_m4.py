import gzip
import json
from pathlib import Path
import tempfile
import unittest

from scripts.qualify_river_second_to_act_m4 import (
    fixture_memory_admitted,
    inventory,
    test_receipt as native_test_receipt,
    verify_panel,
)


class M4QualificationTests(unittest.TestCase):
    def test_evidence_priced_fixture_admission_preserves_one_gib_headroom(self):
        self.assertTrue(fixture_memory_admitted(5 * 2**30))
        self.assertFalse(fixture_memory_admitted(5 * 2**30 - 1))

    def test_wrong_game_is_rejected_without_reading_policy_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'four.gz'
            with gzip.open(p, 'wb') as f:
                f.write(json.dumps(dict(format='nplayer-policy-v1', players=4, entries=20000)).encode()+b'\nnot-a-policy-row\n')
            row = inventory([p])['candidates'][0]
            self.assertEqual(row['disposition'], 'wrong-player-count')
            self.assertEqual(row['players'], 4)
            self.assertTrue(inventory([p])['no_model_loaded'])

    def test_potential_three_player_input_is_not_silently_admitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'three.gz'
            with gzip.open(p, 'wt') as f:
                f.write(json.dumps(dict(players=3))+'\n')
            x = inventory([p])
            self.assertFalse(x['compatible_model_admitted'])
            self.assertEqual(x['candidates'][0]['disposition'], 'requires-full-input-admission')

    def test_missing_or_skipped_tests_cannot_be_reported_as_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'stdout'
            for text in ('', 'test result: ok. 0 passed; 0 failed; 0 ignored',
                         'test result: ok. 2 passed; 0 failed; 1 ignored'):
                p.write_text(text)
                with self.assertRaises(ValueError):
                    native_test_receipt(p)
            p.write_text('test result: ok. 137 passed; 0 failed; 0 ignored')
            self.assertEqual(native_test_receipt(p)['passed'], 137)

    def test_incomplete_panel_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'panel'
            p.write_text('{}\n')
            with self.assertRaises(ValueError):
                verify_panel(p)
