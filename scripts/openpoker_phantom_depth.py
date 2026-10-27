"""Phantom folds and stack depth for Open Poker tables (docs/openpoker-phantom-depth.md).

Phantom study: at 3, 4 and 5 players, a dedicated live-order 10B and #431's six-player 10B
seen through phantom early-position folds play the same deals. Depth study: #431's 100 BB 10B
and a 50 BB six-player 10B play the same deals at 50 BB, at 100 BB and at an unequal-stack
table, each through a projected view where it was not trained. Every contrast is arm 1 minus
arm 0, all-in adjusted, over blocks.
"""
import argparse
import csv
import json
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

from scripts import nplayer_loss_diagnosis as diagnosis
from scripts import nplayer_paired_evidence as evidence
from scripts.nplayer_pressure_screen import sha

TABLES = '/home/dberweger/cygnus-qualification-20261014/tables'
ROOT = 20261027300000
BANKS = 4
BLOCKS = 4096
SCRIPTS = ('random', 'check-call', 'tight-aggressive', 'pot-pressure')
MIXED = {3: ('check-call', 'pot-pressure'), 4: ('check-call', 'pot-pressure', 'tight-aggressive'),
         5: ('check-call', 'pot-pressure', 'tight-aggressive', 'random'),
         6: ('check-call', 'check-call', 'pot-pressure', 'pot-pressure', 'tight-aggressive')}
UNEQUAL_BB = (100, 50, 150, 75, 100, 200)
PHANTOM_SIZES = (3, 4, 5)
MARGIN = 10.0
ARMS = ('a0', 'a1')


def tables():
    """Each table: its study, game, focals (arm 0, arm 1), views and fields; the first field is primary."""
    out = []
    for n in PHANTOM_SIZES:
        fields = {'dedicated': [f'p{n}'] * (n - 1)}
        fields.update({s: [s] * (n - 1) for s in SCRIPTS})
        fields['mixed'] = list(MIXED[n])
        out.append(dict(study='phantom', table=f'{n}p', players=n, stack_bb=100, stacks_bb=None,
                        focals=[f'p{n}', 'six'], views=['native', 'projected'], fields=fields))
    for table, stack, views, trained in (('50bb', 50, ['projected', 'native'], 'six50'),
                                         ('100bb', 100, ['native', 'projected'], 'six')):
        fields = {'trained': [trained] * 5}
        fields.update({s: [s] * 5 for s in SCRIPTS})
        fields['mixed'] = list(MIXED[6])
        out.append(dict(study='depth', table=table, players=6, stack_bb=stack, stacks_bb=None,
                        focals=['six', 'six50'], views=views, fields=fields))
    fields = {'mixed': list(MIXED[6])}
    fields.update({s: [s] * 5 for s in SCRIPTS})
    out.append(dict(study='depth', table='unequal', players=6, stack_bb=100, stacks_bb=list(UNEQUAL_BB),
                    focals=['six', 'six50'], views=['projected', 'projected'], fields=fields))
    return out


def opponent(spec):
    return f'bot={spec}' if spec in SCRIPTS else spec


def manifest(args):
    models = json.loads(args.models.read_text())
    for alias, m in models.items():
        if sha(m['path']) != m['sha256']:
            raise ValueError(f'{alias}: binary pin differs')
    index = 0
    for bank in range(BANKS):
        cases = []
        for t in tables():
            folder = args.out / 'arena' / f'b{bank}' / t['table']
            folder.mkdir(parents=True, exist_ok=True)
            for field, opponents in t['fields'].items():
                row = dict(name=f"b{bank}-{t['table']}-{field}", players=t['players'], stack_bb=t['stack_bb'], blocks=BLOCKS,
                           schedule=None, root=ROOT + 1000 * bank + index, focals=t['focals'], focal_views=t['views'],
                           opponents=[opponent(o) for o in opponents],
                           traces=[str(folder / f'{field}-{a}.jsonl') for a in ARMS], summary=str(folder / f'{field}-cost.json'))
                if t['stacks_bb']:
                    row['stacks_bb'] = t['stacks_bb']
                cases.append(row)
                index += 1
        index = 0
        diagnosis.create(args.out / f'arena-manifest-b{bank}.json', json.dumps(
            {'format': 'nplayer-paired-manifest-v1', 'tables': TABLES, 'threads': 16, 'models': models, 'cases': cases}, indent=1) + '\n')
    print(json.dumps({'manifests': BANKS, 'cases_per_bank': len(cases)}))


def jobs(out):
    arena = json.loads((out / 'arena-manifest-b0.json').read_text())
    work = []
    for bank in range(BANKS):
        for t in tables():
            for field in t['fields']:
                for arm, focal in zip(ARMS, t['focals']):
                    trace = out / 'arena' / f'b{bank}' / t['table'] / f'{field}-{arm}.jsonl'
                    label = f"{arm}-{t['table']}-b{bank}"
                    if trace.exists() and not (out / 'receipts' / f'{label}--{field}.json').exists():
                        work.append((str(trace), str(out), label, field, None, arena['models'][focal]['sha256'], None))
    return work


def scan(args):
    with Pool(args.workers) as pool:
        for receipt in pool.imap_unordered(diagnosis.scan_file, jobs(args.out)):
            print(json.dumps({k: receipt[k] for k in ('label', 'field', 'hands', 'mean_bb100', 'fallback_violations')}), flush=True)


def replay_one(path):
    result = evidence.replay(path)
    result['path'] = path
    return result


def replay(args):
    """Independent engine replay of every bank-0 trace (actions, states, history, settlement)."""
    paths = sorted(str(p) for p in (args.out / 'arena' / 'b0').glob('*/*.jsonl'))
    with Pool(args.workers) as pool:
        results = list(pool.imap_unordered(replay_one, paths))
    if len(results) != sum(len(t['fields']) * 2 for t in tables()):
        raise ValueError('bank-0 traces missing')
    diagnosis.create(args.out / 'replay-b0.json', json.dumps(sorted(results, key=lambda r: r['path']), indent=1) + '\n')
    print(json.dumps({'replayed': len(results), 'hands': sum(r['hands'] for r in results)}))


def missing(receipts, arm, table, fields):
    """Share of the focal's decisions without a positive-mass row, by street, over a table's fields."""
    total, untrained = defaultdict(int), defaultdict(int)
    for bank in range(BANKS):
        for field in fields:
            for key, (count, _) in receipts[f'{arm}-{table}-b{bank}', field]['decisions'].items():
                street, status = key.split('|')[:2]
                total[street] += count
                untrained[street] += count if status in diagnosis.UNTRAINED else 0
    shares = {s: untrained[s] / total[s] if total[s] else None for s in diagnosis.STREETS}
    shares['all'] = sum(untrained.values()) / sum(total.values())
    return shares


def verdict(study, lower, upper):
    if study == 'phantom':
        if lower > -MARGIN:
            return 'phantom adequate'
        return 'dedicated needed' if upper < -MARGIN else 'inconclusive'
    if lower > 0:
        return '50 BB model better'
    return '100 BB model better' if upper < 0 else 'no difference shown'


def report(args):
    receipts = {(r['label'], r['field']): r for r in (json.loads(p.read_text()) for p in (args.out / 'receipts').glob('*.json'))}
    failures = [list(k) for k, r in receipts.items() if r['fallback_violations']]
    expected = sum(len(t['fields']) * 2 * BANKS for t in tables())
    if len(receipts) != expected or failures:
        raise ValueError(f'receipts {len(receipts)}/{expected}, failures {failures}')
    df = BANKS * BLOCKS - 1
    primary_t = {s: diagnosis.t_quantile(1 - 0.05 / (2 * 3), df) for s in ('phantom', 'depth')}
    if BANKS * BLOCKS < 64:
        raise ValueError('too few blocks')
    result = {'format': 'openpoker-phantom-depth-v1', 'contrast': 'arm 1 minus arm 0, all-in adjusted BB/100',
              'margin_bb100': MARGIN, 'tables': {}}
    rows = []
    for t in tables():
        fields = list(t['fields'])
        harm_t = diagnosis.t_quantile(1 - 0.05 / (2 * (len(fields) - 1)), df)
        entry = {'study': t['study'], 'players': t['players'], 'stacks_bb': t['stacks_bb'] or [t['stack_bb']] * t['players'],
                 'arms': {a: {'focal': f, 'view': v} for a, f, v in zip(ARMS, t['focals'], t['views'])},
                 'primary': fields[0], 'fields': {},
                 'missing_share': {a: missing(receipts, a, t['table'], fields) for a in ARMS}}
        for k, field in enumerate(fields):
            deltas = {'adjusted': [], 'reward': []}
            absolute = {a: {'adjusted': [], 'reward': []} for a in ARMS}
            for bank in range(BANKS):
                means = {}
                for arm in ARMS:
                    label = f"{arm}-{t['table']}-b{bank}"
                    hands = diagnosis.hand_rows(args.out, label, field)
                    seatings = receipts[label, field]['seatings']
                    means[arm] = {key: diagnosis.block_means(hands, key, seatings, 100) for key in deltas}
                    for key in deltas:
                        absolute[arm][key] += means[arm][key]
                for key in deltas:
                    deltas[key] += [b - a for a, b in zip(means['a0'][key], means['a1'][key])]
            change = {key: diagnosis.interval(v) for key, v in deltas.items()}
            adjusted = change['adjusted']
            q = primary_t[t['study']] if k == 0 else harm_t
            half = q * adjusted['standard_error_bb100']
            decision = [adjusted['mean_bb100'] - half, adjusted['mean_bb100'] + half]
            f = {'change': change, 'decision_interval': decision,
                 'decision_interval_type': 'Bonferroni 95% over three tables' if k == 0 else f'Bonferroni 95% over {len(fields) - 1} fields',
                 'absolute': {a: {key: diagnosis.interval(v) for key, v in absolute[a].items()} for a in ARMS}}
            if k == 0:
                f['verdict'] = verdict(t['study'], *decision)
            elif t['study'] == 'phantom':
                f['harm_flag'] = decision[1] < -MARGIN
            entry['fields'][field] = f
            rows.append({'study': t['study'], 'table': t['table'], 'field': field, 'primary': k == 0,
                         'change_bb100': adjusted['mean_bb100'], 'lower95': adjusted['lower95_bb100'], 'upper95': adjusted['upper95_bb100'],
                         'decision_lower': decision[0], 'decision_upper': decision[1], 'verdict': f.get('verdict', ''),
                         'harm_flag': f.get('harm_flag', ''),
                         'a0_bb100': f['absolute']['a0']['adjusted']['mean_bb100'], 'a1_bb100': f['absolute']['a1']['adjusted']['mean_bb100']})
        result['tables'][t['table']] = entry
    args.results.mkdir(parents=True, exist_ok=True)
    diagnosis.create(args.results / 'results.json', json.dumps(result, indent=1) + '\n')
    with (args.results / 'fields.csv').open('x', newline='') as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({name: e['fields'][e['primary']].get('verdict') for name, e in result['tables'].items()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('manifest', 'scan', 'equity', 'replay', 'report'):
        p = sub.add_parser(name)
        p.add_argument('--out', type=Path, required=True)
        if name == 'manifest':
            p.add_argument('--models', type=Path, required=True, help='alias -> {path, sha256, mass, mass_sha256}')
        if name in ('scan', 'replay'):
            p.add_argument('--workers', type=int, default=12)
        if name == 'equity':
            p.add_argument('--binary', type=Path, required=True)
        if name == 'report':
            p.add_argument('--results', type=Path, required=True)
        # Qualification only: one bank of 64 blocks on roots the main run never uses.
        p.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    if args.smoke:
        global ROOT, BANKS, BLOCKS
        ROOT, BANKS, BLOCKS = ROOT + 500, 1, 64
    {'manifest': manifest, 'scan': scan, 'equity': diagnosis.equity, 'replay': replay, 'report': report}[args.command](args)


if __name__ == '__main__':
    main()
