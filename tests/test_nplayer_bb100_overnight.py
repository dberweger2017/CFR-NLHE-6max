import unittest
import tempfile
from pathlib import Path
from scripts import nplayer_bb100_overnight as study


class CampaignTests(unittest.TestCase):
    def test_matrix_is_paired_and_disjoint_from_smoke_and_monitors(self):
        rows, smoke = study.cases(), study.cases(True)
        self.assertEqual(len(rows), 36)
        self.assertEqual(sum(r['blocks']*6 for r in rows), 1769472)
        self.assertEqual(len({r['name'] for r in rows}), 36)
        self.assertFalse({r['root'] for r in rows} & {r['root'] for r in smoke})
        for a, b in zip(rows[::2], rows[1::2]):
            self.assertEqual(a['root'], b['root'])
            if a['group'] != 'bot':
                self.assertEqual((a['singleton'], a['pair']), (b['pair'], b['singleton']))
            else:
                self.assertEqual(a['pair'], b['pair'])
        self.assertEqual(sorted(r['name'] for r in rows), sorted(r['name'] for r in study.execution_order(rows)))

    def test_execution_order_keeps_same_seed_models_resident(self):
        order = study.execution_order(study.cases())
        self.assertEqual([r['group'] for r in order[-6:]], ['cross']*6)
        for i, seed in enumerate(study.SEEDS):
            self.assertTrue(all(r['seed'] == seed for r in order[i*10:(i+1)*10]))

    def test_quote_includes_serialization_audits_and_measured_parallel_replay(self):
        with tempfile.TemporaryDirectory() as d:
            export=Path(d)/'average.gz';export.write_bytes(b'x'*100)
            calibration = dict(wall_seconds=1000, sampled_peak_rss_by_phase={'all':20*study.guard.GIB}, events=[
                dict(event='frozen', nodes=1500000000, active_seconds=300),
                dict(event='complete', nodes=2000000000, active_seconds=400, monitor_seconds=1),
                dict(event='checkpoint', save_seconds=100, bytes=200), dict(event='exported', export_seconds=50, path=str(export))])
            performance=dict(blocks=128,cases=36,policy_loads=12,native_load_seconds=100,
                native_wall_seconds=150,native_play_seconds=20,replay_wall_seconds=10,
                input_verification_seconds=2,trace_bytes=1000,json_scan_seconds=3)
            quote=study.cost_quote(calibration,{'wall_seconds':200},{'wall_seconds':300},performance,
                dict(sampled_peak_rss_by_phase={'all':40*study.guard.GIB}))
            self.assertEqual(quote['saving_seconds'],1200)
            self.assertEqual(quote['audit_seconds'],1500)
            self.assertEqual(quote['post_freeze_nodes_per_second'],5000000)
            self.assertEqual(quote['play_seconds'],50*64)  # includes post-play trace hashes.
            self.assertEqual(quote['replay_seconds'],10*64)  # measured8-worker wall, no assumed8x.
            self.assertGreater(quote['main_output_bytes_with_allowance'],1000*64)
            self.assertGreater(quote['total_seconds_with_allowance'],quote['training_seconds'])

    def test_matrix_smoke_uses_six_distinct_cache_identities(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=root/'average.gz';path.write_bytes(b'fixture')
            m=dict(path=str(path),sha256='fixture')
            aliases=study.aliased_models(root,m,m)
            self.assertEqual(len({v['path'] for v in aliases.values()}),6)
            self.assertTrue(all(Path(v['path']).samefile(path) for v in aliases.values()))
            self.assertFalse({r['root'] for r in study.cases(calibration=True)} &
                             {r['root'] for r in study.cases()})

    def test_missing_completion_refuses(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            study.validate_trajectory({'events':[]}, study.CAP, 2000000000)
