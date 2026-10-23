"""Resume and publication conflicts are tested without network or model payloads."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import download_v061 as downloader
from scripts.plan_v061_publication import plan
from src.policies import v061_bundle as v


class Response(io.BytesIO):
    def __init__(self, data, status=200, content_range=None):
        super().__init__(data)
        self.status = status
        self.headers = {'Content-Range': content_range}


class DistributionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'part'
        self.data = b'exact qualified payload'
        self.pin = dict(bytes=len(self.data), sha256=hashlib.sha256(self.data).hexdigest())

    def test_resume_hashes_prefix_and_reuses_verified_complete_asset(self):
        partial = self.path.with_name('part.partial')
        partial.write_bytes(self.data[:6])
        with patch.object(downloader.urllib.request, 'urlopen',
                          return_value=Response(self.data[6:], 206, f'bytes 6-{len(self.data)-1}/{len(self.data)}')) as open_url:
            self.assertEqual(downloader.fetch('https://example.invalid/part', self.path, self.pin), 'downloaded')
            self.assertEqual(open_url.call_args.args[0].get_header('Range'), 'bytes=6-')
        self.assertEqual(self.path.read_bytes(), self.data)
        self.assertFalse(partial.exists())
        with patch.object(downloader.urllib.request, 'urlopen', side_effect=AssertionError('duplicate request')):
            self.assertEqual(downloader.fetch('https://example.invalid/part', self.path, self.pin), 'reused')

    def test_ignored_or_wrong_range_preserves_partial(self):
        partial = self.path.with_name('part.partial')
        partial.write_bytes(self.data[:6])
        for response in (Response(self.data), Response(self.data[6:], 206, 'bytes 0-1/2')):
            with patch.object(downloader.urllib.request, 'urlopen', return_value=response):
                with self.assertRaises(ValueError):
                    downloader.fetch('https://example.invalid/part', self.path, self.pin)
            self.assertEqual(partial.read_bytes(), self.data[:6])
            self.assertFalse(self.path.exists())

    def test_interrupted_empty_partial_resumes_and_corrupt_bytes_refuse(self):
        partial = self.path.with_name('part.partial')
        partial.touch()
        with patch.object(downloader.urllib.request, 'urlopen', return_value=Response(self.data)):
            downloader.fetch('https://example.invalid/part', self.path, self.pin)
        self.path.write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError, 'existing download differs'):
            downloader.fetch('https://example.invalid/part', self.path, self.pin)
        self.assertEqual(self.path.read_bytes(), b'wrong')

    def test_complete_partial_promotes_without_another_request(self):
        self.path.with_name('part.partial').write_bytes(self.data)
        with patch.object(downloader.urllib.request, 'urlopen', side_effect=AssertionError('duplicate request')):
            downloader.fetch('https://example.invalid/part', self.path, self.pin)
        self.assertEqual(self.path.read_bytes(), self.data)

    def test_rehashed_bad_partial_cannot_promote_and_symlinks_refuse(self):
        partial = self.path.with_name('part.partial')
        partial.write_bytes(b'x' * len(self.data))
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            downloader.fetch('https://example.invalid/part', self.path, self.pin)
        self.assertTrue(partial.exists())
        self.assertFalse(self.path.exists())
        self.path.symlink_to(partial)
        with self.assertRaisesRegex(ValueError, 'regular'):
            downloader.fetch('https://example.invalid/part', self.path, self.pin)

    def test_publication_reuses_lost_response_upload_and_refuses_conflicts(self):
        expected = {'part': self.pin}
        asset = dict(name='part', id=123, size=len(self.data), digest='sha256:' + self.pin['sha256'])
        self.assertEqual(plan(expected, [asset])['assets'][0]['action'], 'reuse')
        self.assertEqual(plan(expected, [])['assets'][0]['action'], 'upload-after-owner-approval')
        for bad in (dict(asset, size=1), dict(asset, digest=None), dict(asset, digest='sha256:' + '0'*64)):
            with self.assertRaises(ValueError):
                plan(expected, [bad])
        with self.assertRaises(ValueError):
            plan(expected, [asset, asset])
        with self.assertRaises(ValueError):
            plan(expected, [asset, dict(asset, name='unexpected')])

    def test_manifest_and_all_six_audits_match_committed_research(self):
        root = Path(__file__).resolve().parents[1]
        raw = (root/'docs/reports/nplayer-bb200-model-campaign/results.json').read_bytes()
        result = json.loads(raw)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), v.EVIDENCE['committed_results_sha256'])
        self.assertTrue(result['acceptance'])
        self.assertEqual(len(result['gates']), 30)
        self.assertTrue(all(g['score']['passed'] for g in result['gates']))
        manifest = json.loads((root/'docs/releases/v0.6.1/MODEL_MANIFEST.json').read_text())
        self.assertEqual(manifest['models'], v.MODELS)
        self.assertEqual(manifest['dependencies'], v.DEPENDENCIES)
        self.assertEqual(manifest['research_comparators_and_candidates'], v.RESEARCH)
        for key, origin in v.RESEARCH.items():
            model = result['models'][key]
            self.assertEqual(origin, {name: model[name] for name in origin})
            self.assertEqual(model['audit']['status'], 'passed')
            self.assertEqual(model['binary_audit']['status'], 'passed')
        for seed, model in v.MODELS.items():
            qualified = result['models']['candidate-' + seed]
            self.assertEqual(model['sha256'], qualified['sha256'])
            self.assertEqual(model['metadata']['policy']['source_checkpoint_sha256'], qualified['checkpoint_sha256'])
            self.assertEqual(model['metadata']['source_policy_sha256'], qualified['source_policy_sha256'])
            self.assertEqual(model['metadata']['mass']['receipt_sha256'], qualified['mass_sha256'])
            self.assertEqual(model['metadata']['policy']['identity']['stacks'], [20000]*3)


if __name__ == '__main__':
    unittest.main()
