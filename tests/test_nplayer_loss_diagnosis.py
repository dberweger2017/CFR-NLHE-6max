import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

from scripts import nplayer_loss_diagnosis as diagnosis
from scripts import nplayer_paired_evidence as evidence

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'native/hu20-trainer/target/release/examples'
ARENA = EXAMPLES / 'nplayer_paired_arena'
EQUITY = EXAMPLES / 'nplayer_allin_equity'
_FIXTURE = tempfile.TemporaryDirectory()
FIXTURE = Path(_FIXTURE.name) / 'a.jsonl'


def setUpModule():
    """Play a small scripted four-player trace; raw traces are never committed."""
    if not ARENA.exists() or FIXTURE.exists():
        return
    folder = Path(_FIXTURE.name)
    case = {'name': 'fixture', 'players': 4, 'stack_bb': 100, 'blocks': 2, 'root': 20,
            'focals': ['bot=random', 'bot=random'], 'opponents': ['bot=tight-aggressive', 'bot=pot-pressure', 'bot=random'],
            'traces': [str(FIXTURE), str(folder / 'b.jsonl')], 'summary': str(folder / 'cost.json')}
    manifest = folder / 'manifest.json'
    manifest.write_text(json.dumps({'format': 'nplayer-paired-manifest-v1', 'tables': '/unused', 'threads': 1, 'models': {}, 'cases': [case]}))
    subprocess.run([str(ARENA), 'batch', str(manifest)], check=True, capture_output=True)


def tearDownModule():
    _FIXTURE.cleanup()


def fixture():
    rows = [json.loads(line) for line in FIXTURE.read_text().splitlines()]
    return rows[0], rows[1:]


class StatisticsTests(unittest.TestCase):
    def test_student_quantiles_match_reference_values(self):
        self.assertAlmostEqual(diagnosis.t_quantile(0.975, 10), 2.2281388519649385, places=8)
        self.assertAlmostEqual(diagnosis.t_quantile(0.975, 2), 4.302652729911275, places=8)
        # PR417's published tight-aggressive interval: -16.3923 with SE 7.9565 has lower bound -31.9914.
        self.assertAlmostEqual(-16.392333984375 - diagnosis.t_quantile(0.975, 4095) * 7.956500535156873,
                               -31.991399089829486, places=6)

    def test_cochran_q_for_three_banks(self):
        e = [{'mean_bb100': m, 'standard_error_bb100': 1.0} for m in (0.0, 0.0, 3.0)]
        q = diagnosis.cochran(e)
        self.assertAlmostEqual(q['q'], 6.0)
        self.assertAlmostEqual(q['p'], 0.049787068367863944)
        with self.assertRaises(ValueError):
            diagnosis.cochran(e[:2])


@unittest.skipUnless(ARENA.exists(), 'build nplayer_paired_arena first')
class ClassificationTests(unittest.TestCase):
    def test_every_dimension_partitions_the_focal_result(self):
        header, rows = fixture()
        n, schedule = evidence.header_check(header)
        records = []
        for index, row in enumerate(rows):
            evidence.validate_row(row, index, header, n, schedule)
            seat, record, _, request, showdown = diagnosis.classify(row, n)
            self.assertEqual(seat, row['identities'].index(0))
            self.assertEqual(request is not None, showdown)
            records.append(record)
        total = sum(r['reward'] for r in records)
        for dimension in diagnosis.DIMENSIONS:
            groups = defaultdict(int)
            for r in records:
                groups[r[dimension]] += r['reward']
            self.assertEqual(sum(groups.values()), total)
        # Each focal position appears once per block under the cyclic schedule.
        self.assertEqual(sorted(r['position'] for r in records), sorted(diagnosis.POSITIONS[4] * header['blocks']))
        lines = {r['preflop_line'] for r in records}
        self.assertTrue({'fold after investing', 'limped or checked pot', '3-bet+, raiser', '3-bet+, caller'} <= lines)
        self.assertIn('all-in showdown before river', {r['ending'] for r in records})

    def test_untrained_exposure_and_replacements_are_counted_for_the_focal_seat_only(self):
        _, rows = fixture()
        row = deepcopy(next(r for r in rows if sum(a == r['identities'].index(0) for a in r['actors']) >= 2))
        seat = row['identities'].index(0)
        mine = [i for i, a in enumerate(row['actors']) if a == seat]
        row['lookups'][mine[1]] = {'status': 'zero_mass', 'fallback_replaced': ['raise', 300]}
        for i, a in enumerate(row['actors']):
            if a != seat:
                row['lookups'][i] = {'status': 'missing'}
        _, record, decisions, _, _ = diagnosis.classify(row, 4)
        self.assertEqual((record['untrained_decisions'], record['replaced']), (1, 1))
        self.assertEqual(record['untrained_first'], row['states'][mine[1]]['street'])
        self.assertEqual(len(decisions), len(mine))

    def test_fallback_violations_follow_the_declared_mode(self):
        _, rows = fixture()
        row = deepcopy(next(r for r in rows if r['actions'][r['actors'].index(r['identities'].index(0))][0] in ('call', 'raise')))
        seat = row['identities'].index(0)
        first = row['actors'].index(seat)
        self.assertEqual(diagnosis.fallback_violations(row, seat, 'check-fold'), 0)
        row['lookups'][first] = {'status': 'missing'}
        self.assertEqual(diagnosis.fallback_violations(row, seat, 'uniform'), 0)
        self.assertEqual(diagnosis.fallback_violations(row, seat, 'check-fold'), 1)
        legal = row['states'][first]['legal']
        row['actions'][first] = ['check', 0] if legal['check'] else ['fold', 0]
        row['lookups'][first]['fallback_replaced'] = ['raise', 300]
        self.assertEqual(diagnosis.fallback_violations(row, seat, 'check-fold'), 0)
        self.assertEqual(diagnosis.fallback_violations(row, seat, 'uniform'), 1)

    def test_restricted_fallbacks_refuse_their_excluded_raises_at_untrained_rows(self):
        _, rows = fixture()
        row = deepcopy(next(r for r in rows if r['states'][r['actors'].index(r['identities'].index(0))]['legal']['raise_to']))
        seat = row['identities'].index(0)
        first = row['actors'].index(seat)
        low, high = row['states'][first]['legal']['raise_to']
        row['lookups'][first] = {'status': 'missing'}
        for mode, action, bad in (('no-all-in', ['raise', high], 1), ('no-raise', ['raise', low], 1),
                                  ('no-raise', ['call', 0], 0), ('no-all-in', ['raise', low], int(low == high))):
            row['actions'][first] = action
            self.assertEqual(diagnosis.fallback_violations(row, seat, mode), bad, (mode, action))
        row['lookups'][first] = {'status': 'positive_mass'}
        row['actions'][first] = ['raise', high]
        self.assertEqual(diagnosis.fallback_violations(row, seat, 'no-raise'), 0)

    def test_showdown_board_must_match_the_deck(self):
        _, rows = fixture()
        row = deepcopy(next(r for r in rows if len([p for p in r['states'][-1]['players'] if not p[3]]) > 1))
        row['deck'] = row['deck'][::-1]
        with self.assertRaisesRegex(ValueError, 'showdown board'):
            diagnosis.classify(row, 4)


@unittest.skipUnless(ARENA.exists() and EQUITY.exists(), 'build nplayer_paired_arena and nplayer_allin_equity first')
class PipelineTests(unittest.TestCase):
    def test_scan_equity_and_adjusted_rows_on_the_fixture(self):
        header, rows = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            sha = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
            receipt = diagnosis.scan_file((str(FIXTURE), tmp, 'fx', 'mixed', sha, None, None))
            self.assertTrue(receipt['hash_matches'])
            self.assertEqual(receipt['hands'], len(rows))
            self.assertAlmostEqual(receipt['mean_bb100'], sum(r['rewards'][r['identities'].index(0)] for r in rows) / len(rows))
            with self.assertRaises(FileExistsError):
                diagnosis.scan_file((str(FIXTURE), tmp, 'fx', 'mixed', sha, None, None))
            args = type('A', (), {'out': out, 'binary': EQUITY})
            diagnosis.equity(args)
            hands = diagnosis.hand_rows(out, 'fx', 'mixed')
            locked = [h for h in hands if h['locked'] and h['showdown_result'] != 'none']
            self.assertTrue(locked)
            self.assertTrue(any(h['adjusted'] != h['reward'] for h in locked))
            self.assertTrue(all(h['adjusted'] == h['reward'] for h in hands if not h['locked']))
            for line in (out / 'equity/fx/mixed.jsonl').read_text().splitlines():
                self.assertAlmostEqual(sum(json.loads(line)['expected']), 0.0, places=6)
            style = receipt['style']['focal']
            self.assertLessEqual(style['pfr'], style['vpip'])
            self.assertLessEqual(style.get('went_to_showdown', 0), style.get('saw_flop', 0))

    def test_reference_comparison_flags_any_difference(self):
        _, rows = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            changed = Path(tmp) / 'changed.jsonl'
            lines = FIXTURE.read_text().splitlines()
            row = json.loads(lines[3])
            row['actions'][0] = ['fold', 0] if row['actions'][0][0] != 'fold' else ['call', 0]
            lines[3] = json.dumps(row)
            changed.write_text('\n'.join(lines) + '\n')
            receipt = diagnosis.scan_file((str(FIXTURE), tmp, 'fx', 'mixed', None, None, str(changed)))
            self.assertEqual(receipt['reference']['matched_hands'], len(rows) - 1)
            self.assertFalse(receipt['reference']['all_matched'])


    def test_report_reproduces_published_means_and_reads_the_fallback_pairs(self):
        _, rows = fixture()
        mean = sum(r['rewards'][r['identities'].index(0)] for r in rows) / len(rows)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'published.csv').write_text(f'field,mean_bb100\nmixed,{mean!r}\n')
            banks = ['a', 'b', 'c']
            config = {'fields': ['mixed'], 'focus': ['mixed'], 'fallback': {'banks': banks, 'modes': ['uniform', 'check-fold']},
                      'inputs': [{'label': b, 'players': 6, 'published': {'csv': 'published.csv', 'where': {}, 'column': 'mean_bb100'}}
                                 for b in banks]}
            (tmp / 'config.json').write_text(json.dumps(config))
            out = tmp / 'out'
            for b in banks:
                diagnosis.scan_file((str(FIXTURE), str(out), b, 'mixed', None, None, None))
                diagnosis.scan_file((str(FIXTURE), str(out), f'B{b}-uniform', 'mixed', None, None, str(FIXTURE)))
                diagnosis.scan_file((str(FIXTURE), str(out), f'B{b}-check-fold', 'mixed', None, None, None))
            diagnosis.equity(type('A', (), {'out': out, 'binary': EQUITY}))
            args = type('A', (), {'config': tmp / 'config.json', 'out': out, 'repo': tmp, 'results': tmp / 'results'})
            diagnosis.report(args)
            summary = json.loads((tmp / 'results/summary.json').read_text())
            self.assertEqual(summary['failures'], [])
            self.assertTrue(all(summary['inputs'][b]['mixed']['reproduced'] for b in banks))
            self.assertAlmostEqual(summary['heterogeneity']['mixed']['realized']['q'], 0.0)
            self.assertEqual(summary['fallback']['pooled']['mixed']['realized']['mean_bb100'], 0.0)
            self.assertTrue(summary['fallback']['a']['mixed']['uniform_reproduces_history'])
            for name in ('partitions', 'luck', 'untrained', 'style', 'banks', 'table-size'):
                self.assertTrue((tmp / f'results/{name}.csv').exists())


class ManifestTests(unittest.TestCase):
    def test_fallback_manifest_pins_one_ten_billion_and_orders_trained_fields_last(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ten = {'path': '/m/10b.bin', 'sha256': 'a' * 64, 'mass': '/m/10b-mass', 'mass_sha256': 'b' * 64}
            three = {'path': '/m/3b.bin', 'sha256': 'c' * 64, 'mass': '/m/3b-mass', 'mass_sha256': 'd' * 64}
            fields = ['random', 'trained']
            inputs = []
            for bank, (focal, peer) in {'6p-417': ('candidate', 'baseline'), '6p-419': ('control', 'peer')}.items():
                cases = [{'name': f, 'players': 6, 'stack_bb': 100, 'blocks': 4, 'root': 7, 'schedule': [[0, 1, 2, 3, 4, 5]] * 1,
                          'focals': [peer, focal], 'opponents': [peer] * 5 if f == 'trained' else ['bot=random'] * 5}
                         for f in fields]
                models = {focal: dict(ten, checkpoint='/m/ckpt'), peer: three, 'composed': {'composition': 'x'},
                          'unused': {'path': '/m/500m.bin', 'sha256': 'e' * 64, 'mass': '/m/m', 'mass_sha256': 'f' * 64}}
                path = tmp / f'{bank}.json'
                path.write_text(json.dumps({'tables': '/k50', 'threads': 8, 'models': models, 'cases': cases}))
                inputs.append({'label': bank, 'players': 6, 'focal_sha256': 'a' * 64, 'manifest': str(path), 'focal_alias': focal})
            config = {'fields': fields, 'inputs': inputs,
                      'fallback': {'banks': ['6p-417', '6p-419'], 'modes': ['uniform', 'check-fold'], 'threads': 16}}
            (tmp / 'config.json').write_text(json.dumps(config))
            args = type('A', (), {'config': tmp / 'config.json', 'out': tmp / 'out'})
            diagnosis.fallback_manifest(args)
            manifest = json.loads((tmp / 'out/fallback-manifest.json').read_text())
            self.assertEqual(manifest['models'], {'ten': ten, 'three': three})
            self.assertEqual([c['name'] for c in manifest['cases']],
                             ['6p-417-random', '6p-419-random', '6p-417-trained', '6p-419-trained'])
            for case in manifest['cases']:
                self.assertEqual(case['focals'], ['ten', 'ten'])
                self.assertEqual(case['focal_untrained_fallback'], ['uniform', 'check-fold'])
            self.assertEqual(manifest['cases'][-1]['opponents'], ['three'] * 5)
            config['inputs'][0]['focal_alias'] = 'baseline'
            (tmp / 'config.json').write_text(json.dumps(config))
            args.out = tmp / 'again'
            with self.assertRaisesRegex(ValueError, 'pinned 10B'):
                diagnosis.fallback_manifest(args)


if __name__ == '__main__':
    unittest.main()
