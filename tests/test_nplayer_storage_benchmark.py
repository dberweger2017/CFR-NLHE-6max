import copy
import unittest

from scripts.run_nplayer_storage_benchmark import GIB, check_event, compare, enforce


def reference():
    rows = []
    for target in [1100, 1200, 1300]:
        rows += [dict(event='trained', target=target, nodes=target+7,
                      iteration=target//2, entries=target//3),
                 dict(event='verified', target=target, sha256=str(target))]
    return dict(events=rows)


class IdentityTests(unittest.TestCase):
    def test_matching_milestones_ignore_different_performance(self):
        a = reference()
        b = copy.deepcopy(a)
        for event in b['events']:
            event['seconds'] = 99
        compare(a, b)

    def test_first_wrong_hash_is_rejected_before_later_milestones(self):
        event = dict(event='verified', target=1100, sha256='wrong')
        with self.assertRaisesRegex(ValueError, '1100'):
            check_event(reference(), event)

    def test_wrong_counts_or_missing_milestone_rejected(self):
        b = reference()
        b['events'][0]['iteration'] += 1
        with self.assertRaises(ValueError):
            compare(reference(), b)
        with self.assertRaises(ValueError):
            compare(reference(), dict(events=b['events'][:-1]))


class GuardTests(unittest.TestCase):
    def row(self):
        return dict(temperatures_c={'Package id 0':60, 'Thermistor 15':65},
            available_ram_bytes=50*GIB, rss_bytes=10*GIB,
            swap_growth_bytes=0, free_disk_bytes=80_000_000_000)

    def test_admitted_with_remaining_reservation(self):
        enforce(self.row(), 20_000_000_000, 100)

    def test_resource_breaches_refuse_continuation(self):
        changes = [dict(available_ram_bytes=7*GIB), dict(rss_bytes=25*GIB),
                   dict(swap_growth_bytes=300*1024**2),
                   dict(free_disk_bytes=65_000_000_000),
                   dict(temperatures_c={'Package id 0':80, 'Thermistor 15':65})]
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(RuntimeError):
                    enforce(dict(self.row(), **change), 20_000_000_000, 100)

    def test_fail_safe_and_output_budget(self):
        with self.assertRaises(RuntimeError):
            enforce(self.row(), 0, 14400)
        with self.assertRaises(RuntimeError):
            enforce(self.row(), -1, 0)
