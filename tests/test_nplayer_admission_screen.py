import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts import nplayer_admission_screen as screen


def write_checkpoint(path, rows):
    with gzip.open(path, 'wt') as f:
        f.write(json.dumps({'format': 'nplayer-cfr-v1'}) + '\n')
        for key, visits in rows:
            f.write(json.dumps([key, 0, 0, 3, visits, [0.0, 0.0], [1.0, 1.0]], separators=(',', ':')) + '\n')


def write_trace(path, hands):
    with gzip.open(path, 'wt') as f:
        f.write(json.dumps({'format': 'nplayer-privileged-policy-replay-v1'}) + '\n')
        for lookups in hands:
            f.write(json.dumps({'lookups': lookups}) + '\n')


def lookup(identity, status, street, key='0' * 32):
    return {'identity': identity, 'key': key, 'position': 0, 'seat': 0, 'status': status, 'street': street}


class RowClassTests(unittest.TestCase):
    def test_opponent_only_rows_are_separated_from_learned_rows(self):
        learned, opponent_only = 'a' * 32, 'b' * 32
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint, trace = Path(tmp) / 'cp.gz', Path(tmp) / 't.jsonl.gz'
            write_checkpoint(checkpoint, [(learned, 3), (opponent_only, 0), ('c' * 32, 9)])
            write_trace(trace, [
                [lookup(0, 'positive_mass', 0, learned), lookup(1, 'positive_mass', 0, opponent_only), {'status': 'not_applicable'}],
                [lookup(0, 'positive_mass', 3, opponent_only), lookup(0, 'zero_mass', 3), lookup(0, 'missing', 1)],
            ])
            _, _, counts = screen.focal_lookups((str(trace), 'control-b0', 'pot-pressure'))
            keys = {k for _, _, k in counts if k}
            self.assertEqual(keys, {learned, opponent_only}, 'only the focal identity is counted')
            found = screen.visits(checkpoint, keys)
            self.assertEqual(found, {learned: 3, opponent_only: 0})
            by_street = screen.classify(counts, found)
            self.assertEqual(by_street['preflop'], {'learned': 1, 'opponent_only': 0, 'zero_mass': 0, 'missing': 0})
            self.assertEqual(by_street['flop']['missing'], 1)
            self.assertEqual(by_street['river'], {'learned': 0, 'opponent_only': 1, 'zero_mass': 1, 'missing': 0})
            shares = screen.shares(by_street)
            self.assertEqual(shares['all']['learned'], 0.25)
            self.assertIsNone(shares['turn']['learned'])

    def test_a_positive_mass_key_absent_from_the_checkpoint_is_an_error(self):
        with self.assertRaises(ValueError):
            screen.classify({(0, 'positive_mass', 'd' * 32): 1}, {})


if __name__ == '__main__':
    unittest.main()
