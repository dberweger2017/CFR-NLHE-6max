"""Decision/report integrity checks; estimator mathematics is exhaustively tested in Rust."""
import json
import importlib.util
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.deep_cfr_variance_probe import root_rows, ratios, verdict


class VarianceProbeTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('torch'), 'torch is in the research/CI environment')
    def test_fit_and_export_preserve_action_targets_and_bb_units(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            data = root / 'data'
            data.mkdir()
            target = [-100., -20., 0., 10., 100., 200.]
            with (data / 'train.bin').open('wb') as f:
                for i in range(600):
                    f.write(bytes(670) + bytes([i % 6]) + struct.pack('<f', target[i % 6]))
            (data / 'summary.json').write_text(json.dumps({'policy_layout': 'synthetic-layout'}))
            subprocess.run([sys.executable, '-m', 'scripts.deep_cfr_variance_probe', 'fit', '--device', 'cpu',
                            '--data', str(data), '--out', str(root / 'fit')], check=True, capture_output=True, text=True)
            critic = json.loads((root / 'fit' / 'critic.json').read_text())
            self.assertEqual(critic['format'], 'variance-probe-critic-v1')
            self.assertEqual((len(critic['w']), len(critic['v'])), (670 * 64, 64 * 6))
            # At zero input the first layer is its bias; evaluate the exported arrays
            # independently, including the BB scaling used by the native reader.
            for a in range(6):
                value = 100 * (critic['c'][a] + sum(critic['v'][64*a+k] * max(0, critic['b'][k]) for k in range(64)))
                self.assertAlmostEqual(value, target[a], delta=.1)

    def test_cost_can_reverse_a_variance_gain(self):
        rows = [{'stratum': 'flop', 'variance': [10., 2.], 'seconds': [1., 2.]},
                {'stratum': 'river', 'variance': [20., 4.], 'seconds': [1., 2.]}]
        result = ratios(rows, overhead=20., resamples=50)
        self.assertAlmostEqual(result['variance_ratio'], .2)
        self.assertAlmostEqual(result['cost_ratio'], 2.4)

    def test_advance_requires_uncertainty_batches_and_no_street_harm(self):
        good = {'cost_interval': [.3, .6], 'cost_ratio': .5}
        self.assertEqual(verdict(good, [good, good], [good]), 'advance')
        noisy = {'cost_interval': [.3, .9], 'cost_ratio': .5}
        self.assertEqual(verdict(noisy, [good, good], [good]), 'inconclusive')
        self.assertEqual(verdict(good, [good, {**good, 'cost_ratio': .8}], [good]), 'inconclusive')
        self.assertTrue(verdict(good, [good, good], [{'cost_interval': [1.1, 2.]}]).startswith('reject'))

    def test_zero_sampled_variance_does_not_manufacture_an_improvement(self):
        result = ratios([{'stratum': 'river', 'variance': [0., 0.], 'seconds': [1., 1.]}], 0., resamples=10)
        self.assertIsNone(result['cost_interval'])
        self.assertTrue(verdict(result, [result], [result]).startswith('inconclusive'))

    def test_reject_partial_duplicate_or_changed_tree_evidence(self):
        arms = [{'arm': a, 'advantages': [0.] * 6, 'legal': 3, 'nodes': 5, 'seconds': .01} for a in (0, 1)]
        row = {'root': '3p100-1-0', 'batch': 0, 'repeat': 0, 'arms': arms}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'rows.jsonl'
            p.write_text(json.dumps(row) + '\n')
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                root_rows(p, 64)
            p.write_text((json.dumps(row) + '\n') * 2)
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                root_rows(p, 64)
            row['arms'][1]['nodes'] = 6
            p.write_text(json.dumps(row) + '\n')
            with self.assertRaisesRegex(ValueError, 'sampled tree'):
                root_rows(p, 64)


if __name__ == '__main__':
    unittest.main()
