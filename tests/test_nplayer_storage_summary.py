import json
from pathlib import Path
import tempfile
import unittest

from scripts.run_nplayer_storage_benchmark import TARGETS
from scripts.summarize_nplayer_storage_benchmark import summarize


class SummaryTests(unittest.TestCase):
    def fixture(self, root):
        for arm, train_time, save_time, rss in [('baseline', 5, 10, 100),
                                               ('compact', 6, 10, 40),
                                               ('parallel', 6, 2, 50)]:
            events = [dict(event='loaded', seconds=3), dict(event='complete', seconds=99)]
            peaks = {'load/0':200}
            for target in TARGETS:
                events += [dict(event='trained', target=target, nodes=target+7,
                    entries=30_000_000, iteration=target//100, seconds=train_time,
                    nodes_per_second=100_000_000/train_time),
                    dict(event='saved', target=target, bytes=1_000_000_000, seconds=save_time),
                    dict(event='verified', target=target, sha256=str(target), seconds=1)]
                peaks[f'train/{target}'] = rss
                peaks[f'save/{target}'] = rss+10
            folder=root/'measurements'/('arm-'+arm)
            folder.mkdir(parents=True)
            (folder/'result.json').write_text(json.dumps(dict(returncode=0, events=events,
                sampled_peak_rss_by_phase=peaks, wall_seconds=100, cpu_seconds=50)))

    def test_reports_each_phase_and_ratios_without_assuming_training_gain(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.fixture(root)
            result=summarize(root)
            self.assertEqual(len(result['rows']), 9)
            compact=result['rows'][3]
            parallel=result['rows'][6]
            self.assertAlmostEqual(compact['training_speed_ratio'], 5/6)
            self.assertAlmostEqual(compact['training_rss_ratio'], .4)
            self.assertEqual(parallel['save_speed_ratio'], 5)
            self.assertEqual(parallel['compressed_save_mb_per_second'], 500)
            self.assertTrue(all(r['checkpoint_identical'] for r in result['rows']))

    def test_missing_phase_samples_prevent_a_complete_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.fixture(root)
            p=root/'measurements/arm-parallel/result.json'
            data=json.loads(p.read_text()); data['sampled_peak_rss_by_phase']={}
            p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'memory samples'):
                summarize(root)
