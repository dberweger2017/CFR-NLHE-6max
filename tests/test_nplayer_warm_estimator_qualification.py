"""Small fixtures only: no mature model, K50 load, native run or host probe."""
import io
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import nplayer_warm_estimator_qualification as q


class QualificationTests(unittest.TestCase):
    def test_extracts_balanced_prefix_but_hashes_unselected_tail(self):
        header = dict(format='nplayer-privileged-policy-replay-v1',
                      schedule=[list(x) for x in q.SCHEDULE], identity={'players': 4},
                      policies=[{'source_checkpoint_sha256': q.WARM_SHA}])
        rows = [dict(block=b, permutation=i, identities=list(p), button=b % 4)
                for b in range(3) for i, p in enumerate(q.SCHEDULE)]
        data = ''.join(json.dumps(x) + '\n' for x in [header] + rows)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'saved.jsonl'; source.write_text(data)
            digest = q.sha(source); out = io.StringIO()
            receipt = q.extract_one(source, digest, out, 'check-call', blocks=2)
            selected = list(map(json.loads, out.getvalue().splitlines()))
            self.assertEqual(receipt['hands'], 16)
            self.assertEqual({tuple(x['record']['identities']) for x in selected}, set(q.LEAN))
            self.assertEqual({x['record']['block'] for x in selected}, {0, 1})
            source.write_text(data + 'unselected tail corruption\n')
            with self.assertRaisesRegex(ValueError, 'hash/stat'):
                q.extract_one(source, digest, io.StringIO(), 'check-call', blocks=2)
            source.write_text(data.replace('"button": 0', '"button": 3', 1))
            with self.assertRaisesRegex(ValueError, 'order/seating/button'):
                q.extract_one(source, q.sha(source), io.StringIO(), 'check-call', blocks=2)

    def test_changed_scope_source_and_unreviewed_math_are_rejected(self):
        config = {**q.SCOPE, 'source': 'frozen', 'source_files': {'native/example.rs': 'abc'},
                  'checkpoint_sha256': q.WARM_SHA, 'historical_report_sha256': 'report',
                  'binary_sha256': 'binary'}
        review = dict(status='approved', source='frozen', binary_sha256='binary',
                      independent_reviewer='fixture reviewer, not an actual review',
                      scope='frozen-warm-estimator-and-information-boundary',
                      unresolved_correctness_questions=[])
        with patch.object(q, 'source_pins', return_value=config['source_files']), \
                patch.object(q, 'sha', return_value='report'):
            q.validate(config, review)
            for name, value in [('threads', 8), ('batches', 33), ('proposal_passive_fraction', .5),
                                ('source_files', {}), ('checkpoint_sha256', 'other')]:
                changed = {**config, name: value}
                with self.assertRaises(ValueError): q.validate(changed, review)
            for name, value in [('source', 'other'), ('status', 'pending'),
                                ('binary_sha256', 'other'), ('independent_reviewer', ''),
                                ('unresolved_correctness_questions', ['weight question'])]:
                with self.assertRaisesRegex(ValueError, 'review'):
                    q.validate(config, {**review, name: value})

    def fixture(self, root):
        (root / 'initial').mkdir(); (root / 'repeat').mkdir()
        for name in q.ARTIFACTS:
            path = root / 'initial' / name
            path.parent.mkdir(exist_ok=True)
            path.write_text('{}\n')
        summary = dict(status='complete-diagnostic-only', input_checkpoint_sha256=q.WARM_SHA,
                       no_training_or_strength_verdict=True)
        (root / 'initial/summary.json').write_text(json.dumps(summary))
        for mode in ('reference', 'passive'):
            path = root / 'initial' / mode / 'roots.jsonl'
            header = dict(format='nplayer-frozen-estimator-roots-v1', mode=mode,
                          root_seed=q.SCOPE['root_seed'], batches=32, players=4,
                          roots_per_seat=8, source_checkpoint_sha256=q.WARM_SHA)
            rows = [dict(batch=b, traverser=s, root=r)
                    for b, s, r in itertools.product(range(32), range(4), range(8))]
            path.write_text(''.join(json.dumps(x) + '\n' for x in [header] + rows))
        self.receipts(root)

    def receipts(self, root):
        manifest = {'format': 'nplayer-warm-artifact-receipts-v1',
                    'files': {n: dict(bytes=(root / 'initial' / n).stat().st_size,
                                     sha256=q.sha(root / 'initial' / n)) for n in q.ARTIFACTS}}
        for phase in ('initial', 'repeat'):
            q.write(root / phase / 'artifacts.json', manifest)

    def test_complete_reproduction_has_no_duplicate_raw_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            proof = q.verify(root)
            self.assertTrue(proof['byte_compared_reproduction'])
            self.assertEqual(proof['root_contexts_per_mode'], 1024)
            (root / 'repeat/summary.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'duplicate raw'):
                q.verify(root)

    def test_truncation_changed_digest_and_duplicate_root_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            roots = root / 'initial/reference/roots.jsonl'
            original = roots.read_text(); roots.write_text(original[:-10])
            with self.assertRaisesRegex(ValueError, 'artifact changed'):
                q.verify(root)
            roots.write_text(original)
            manifest = q.read(root / 'repeat/artifacts.json')
            manifest['files']['summary.json']['sha256'] = 'wrong'
            q.write(root / 'repeat/artifacts.json', manifest)
            with self.assertRaisesRegex(ValueError, 'inventory/hash/length'):
                q.verify(root)
            rows = original.splitlines(); rows[2] = rows[1]
            roots.write_text('\n'.join(rows) + '\n'); self.receipts(root)
            with self.assertRaisesRegex(ValueError, 'missing/duplicate/reordered'):
                q.verify(root)

    def test_readout_keeps_never_reached_zero_prefix_watch_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            key = 'ab' * 16
            prefix = dict(key=key, street=3, family='P0', target_counterfactual_prefix=0.)
            (root / 'initial/prefix-audit.jsonl').write_text('{}\n' + json.dumps(prefix) + '\n')
            summary = q.read(root / 'initial/summary.json')
            for mode in ('reference', 'passive'):
                summary[mode] = dict(summary=dict(nodes=100, roots=1024,
                    by_street_family=[dict(street=3, family='P0', replicated_positive_learning_proxy=0)]))
                row = dict(key=key, first_batch=None, admitted_batch=None,
                           potential={'zero_update': True}, retained={'zero_update': True})
                (root / 'initial' / mode / 'rows.jsonl').write_text(json.dumps(row) + '\n')
            q.write(root / 'initial/summary.json', summary); self.receipts(root)
            result = q.settle(root)
            self.assertTrue(result['no_automatic_training'])
            self.assertIn('not demonstrated', result['interpretation'])
            for mode in ('reference', 'passive'):
                watched = result['modes'][mode]['watched']
                self.assertEqual(len(watched), 1)
                self.assertFalse(watched[0]['encountered'])
                self.assertEqual(watched[0]['positive_target_prefixes'], 0)


if __name__ == '__main__':
    unittest.main()
