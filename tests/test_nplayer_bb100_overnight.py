import unittest
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

    def test_quote_includes_serialization_audits_and_replay(self):
        calibration = dict(wall_seconds=1000, sampled_peak_rss_by_phase={'all':20*study.guard.GIB}, events=[
            dict(event='frozen', nodes=1500000000, active_seconds=300),
            dict(event='complete', nodes=2000000000, active_seconds=400, monitor_seconds=1),
            dict(event='checkpoint', save_seconds=100), dict(event='exported', export_seconds=50)])
        quote = study.cost_quote(calibration, {'wall_seconds':200}, {'wall_seconds':300},
            dict(load_seconds=100, play_seconds=1), {'wall_seconds':2},
            dict(sampled_peak_rss_by_phase={'all':40*study.guard.GIB}))
        self.assertEqual(quote['saving_seconds'], 1200)
        self.assertEqual(quote['audit_seconds'], 1500)
        self.assertEqual(quote['post_freeze_nodes_per_second'], 5000000)
        self.assertGreater(quote['total_seconds_with_allowance'], quote['training_seconds'])
        self.assertGreater(quote['peak_rss_with_allowance_bytes'], 40*study.guard.GIB)

    def test_missing_completion_refuses(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            study.validate_trajectory({'events':[]}, study.CAP, 2000000000)
