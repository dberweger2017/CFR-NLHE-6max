import copy
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from scripts import run_nplayer_bb100_pilot as pilot


class PilotTests(unittest.TestCase):
    def test_disabled_swap_is_real_while_low_ram_still_stops(self):
        gib = pilot.guard.GIB
        initial = dict(SwapTotal=64*gib, SwapFree=41*gib, MemAvailable=100*gib)
        used = dict(initial, SwapFree=40*gib)
        low = dict(used, MemAvailable=7*gib)
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(pilot.guard, 'memory', side_effect=[initial, used, low]), \
                patch.object(pilot.guard, 'sensors', return_value={'Package id 0':60, 'Thermistor 15':70}), \
                patch.object(pilot.guard, 'fan_rpm', return_value=1000), \
                patch.object(pilot.guard.os, 'statvfs', return_value=SimpleNamespace(f_bavail=1000*gib, f_frsize=1)):
            s = pilot.PilotSupervisor(Path(directory), 0, cpus=range(16), max_seconds=1200,
                rss_limit=32*gib, cpu_limit=90, thermistor_limit=100, swap_limit_bytes=None)
            row = s.sample(None, 'train', 100000000)
            self.assertFalse(row['swap_guard_enabled'])
            self.assertEqual(row['swap_growth_bytes'], gib)
            self.assertEqual(row['swap_used_bytes'], 24*gib)
            with self.assertRaisesRegex(RuntimeError, 'memory stop'):
                s.sample(None, 'train', 100000000)

    def summary(self):
        return dict(identity=dict(players=3, stacks=[10000] * 3, small_blind=50, big_blind=100,
            menu='min-pot-conditional-jam-v1', schema='nplayer-button-live-actor-history-equity-k50-v1',
            utility_unit='big-blind'), stop_reason='nodes', counts=dict(nodes=100000017,
            discarded_keys=0, discarded_visits=0), entries=20000000, frozen_at=None)

    def test_fixed_recipe_and_resume_hash_are_explicit(self):
        args = pilot.command(dict(train='/qualified/native', tables='/pinned/k50'), '/fresh.gz', 200000000,
            resume=dict(checkpoint='/prefix.gz', sha256='a' * 64))
        for key, expected in [('--stack-bb', '100'), ('--players', '3'), ('--threads', '16'),
                ('--roots-per-seat', '8'), ('--last-average-street', '3'), ('--resume-sha256', 'a' * 64)]:
            self.assertEqual(args[args.index(key) + 1], expected)
        self.assertNotIn('--freeze-at-cap', args)
        self.assertNotIn('--prune-bb', args)
        self.assertNotIn('--fast-gzip', args)

    def test_refuses_20bb_or_another_game(self):
        pilot.validate(self.summary(), 100000000)
        for key, bad in [('stacks', [2000] * 3), ('players', 2), ('big_blind', 50), ('schema', 'compact')]:
            row = self.summary(); row['identity'][key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError):
                pilot.validate(row, 100000000)

    def test_time_capacity_freezing_or_missing_work_cannot_pass(self):
        for key, bad in [('stop_reason', 'time'), ('stop_reason', 'capacity'),
                ('frozen_at', 1), ('entries', pilot.CAP)]:
            row = self.summary(); row[key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError):pilot.validate(row, 100000000)
        for key, bad in [('nodes', 99999999), ('discarded_keys', 1), ('discarded_visits', 1)]:
            row = copy.deepcopy(self.summary()); row['counts'][key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError):pilot.validate(row, 100000000)
