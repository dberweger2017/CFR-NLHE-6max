import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import nplayer_blueprint_promotion as study
from scripts.analyze_nplayer_arena import sha


class PromotionTests(unittest.TestCase):
    def test_cross_seed_opponents_rotate_and_both_orientations_share_fresh_deals(self):
        matrix = study.cases()
        self.assertEqual(sum(c['blocks'] * 6 for c in matrix), 589824)
        pairs = list(zip(matrix[::2], matrix[1::2]))
        self.assertEqual(len({left['root'] for left, _ in pairs}), 6)
        for left, right in pairs:
            self.assertEqual((left['singleton'], left['pair']), (right['pair'], right['singleton']))
            self.assertEqual(left['root'], right['root'])
            self.assertEqual(left['seed'] == left['opponent_seed'], left['group'] == 'same')
        self.assertEqual([c['opponent_seed'] for c in matrix[6::2]], [2026101542, 2026101543, 2026101541])
        self.assertFalse({c['root'] for c in matrix} & {c['root'] for c in study.cases(True)})
        self.assertFalse({c['root'] for c in matrix} & set(range(20261018335101, 20261018335107)))

    def test_final_manifest_rejects_smoke_or_changed_policy_seed_size_and_workers(self):
        study.validate_manifest(study.manifest())
        with self.assertRaises(ValueError):
            study.validate_manifest(study.manifest(True))
        for field, value in [('blocks', 8193), ('root', 123), ('singleton', 'production-2026101541-1b')]:
            changed = study.manifest()
            changed['cases'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                study.validate_manifest(changed)
        changed = study.manifest()
        changed['workers'] = 16
        with self.assertRaises(ValueError):
            study.validate_manifest(changed)
        changed = study.manifest()
        changed['models']['fast-2026101541-clock']['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            study.validate_manifest(changed)

    def rows(self):
        return [dict(group=g, seed=s, advantage=dict(lower95_bb100=1 if g == 'same' else -4))
                for g in ('same', 'cross') for s in study.SEEDS]

    def test_promotion_requires_each_seed_and_strict_predeclared_margins(self):
        rows = self.rows()
        self.assertTrue(study.decision(rows)['promotion_gate_passed'])
        for index, boundary in [(0, 0), (3, -5)]:
            changed = copy.deepcopy(rows)
            changed[index]['advantage']['lower95_bb100'] = boundary
            self.assertFalse(study.decision(changed)['promotion_gate_passed'])
        with self.assertRaises(ValueError):
            study.decision(rows[:-1])
        with self.assertRaises(ValueError):
            study.decision(rows[:-1] + [rows[0]])

    def fixture(self, root):
        m = study.manifest()
        (root / 'evaluation-manifest.json').write_text(json.dumps(m))
        (root / 'status.json').write_text(json.dumps(dict(status='verified-readout-ready')))
        (root / 'evaluation-verified.json').write_text(json.dumps(dict(status='passed', cases=12,
            final_hands=589824, reproduction_hands=589824,
            manifest_sha256=sha(root / 'evaluation-manifest.json'))))
        for case in m['cases']:
            folder = root / 'evaluation' / case['name']
            folder.mkdir(parents=True)
            header = dict(seed=case['root'], blocks=8192, hands=49152,
                policies=[dict(sha256=m['models'][name]['sha256'], strategy='average', average_scope=3)
                          for name in [case['singleton'], case['pair'], case['pair']]])
            for repeat in (0, 1):
                (folder / f'play-{repeat}.jsonl').write_text(json.dumps(header) + '\n')
            digest = sha(folder / 'play-0.jsonl')
            (folder / 'result.json').write_text(json.dumps(dict(case=case, status='passed', hands=49152,
                trace_sha256=digest, operations=[dict(returncode=0)] * 2)))
            (folder / 'replay.json').write_text(json.dumps(dict(status='passed', hands=49152, trace_sha256=digest)))

    def test_global_barrier_rejects_missing_receipts_and_changed_reproduction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            study.global_gate(root)
            trace = next((root / 'evaluation').glob('*/play-1.jsonl'))
            trace.write_text(trace.read_text() + 'changed\n')
            with self.assertRaisesRegex(ValueError, 'trace verification'):
                study.global_gate(root)
            trace.unlink()
            with self.assertRaises(FileNotFoundError):
                study.global_gate(root)

    def test_failure_or_incomplete_barrier_prevents_outcome_read(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(study, 'paired_blocks') as paired:
            root = Path(directory)
            (root / 'failure.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'failed'):
                study.read(root)
            paired.assert_not_called()
            (root / 'failure.json').unlink()
            (root / 'status.json').write_text('{"status":"final-evaluation"}')
            with self.assertRaisesRegex(ValueError, 'barrier'):
                study.read(root)
            paired.assert_not_called()


if __name__ == '__main__':
    unittest.main()
