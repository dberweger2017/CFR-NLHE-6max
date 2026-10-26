"""Six-player live-order key variants and a 10B-against-50B head-to-head.

Variant screen: each finer key variant's 10B (seed 2026102361001) against #431's
live-order 10B, on one new set of banks with the screens' fields and #417's 3B.
`combine` applies docs/nplayer-live-order-variants.md: a variant improves if its
trained-field lower bound clears zero with Bonferroni over the two variants.

Head-to-head (`h2h-*`): #431's 10B and #439's 50B each play the same deals against
five copies of the 10B and against five copies of the 50B.
"""
import argparse
import csv
import json
from pathlib import Path

from scripts import nplayer_admission_screen as admission
from scripts import nplayer_live_order_nodes as nodes
from scripts import nplayer_loss_diagnosis as diagnosis
from scripts import nplayer_pressure_screen as screen

ARM = 'variant'
FORMAT = 'nplayer-live-order-variant-v1'
ROOT = 20261027100000
H2H_ROOT = 20261027200000
PRIMARY = 'trained'
VARIANTS = 2
SCHEMAS = ('nplayer-live-order-seat-summary-equity-k50-v1', 'nplayer-live-order-street-exact-equity-k50-v1')
CONTROL_SCHEMA = 'nplayer-live-order-summary-equity-k50-v1'
H2H_FIELDS = ('vs-10b', 'vs-50b')


def manifest(args):
    screen.manifest(args, arm=ARM, control=screen.model(args.control_binary, args.control_mass), root=ROOT)


def training(args):
    result = {}
    for name, checkpoint, mass, schemas in (('control', args.control_checkpoint, args.control_mass, (CONTROL_SCHEMA,)),
                                            (ARM, args.checkpoint, args.mass, SCHEMAS)):
        h = admission.header(checkpoint)
        if h['game']['schema'] not in schemas:
            raise ValueError(f'{name}: unexpected key schema {h["game"]["schema"]}')
        result[name] = admission.telemetry(h, json.loads((mass / 'receipt.json').read_text()))
        result[name]['schema'] = h['game']['schema']
    diagnosis.create(args.out / 'training.json', json.dumps(result, indent=1) + '\n')
    print(json.dumps({a: {k: v for k, v in t.items() if k != 'by_street'} for a, t in result.items()}))


def combine(args):
    """Per variant: the trained field against a Bonferroni-over-variants interval; other fields
    as in the screens (seven-test family intervals, harm flags)."""
    variants = {}
    for spec in args.summary:
        name, path = spec.split('=', 1)
        variants[name] = json.loads(Path(path).read_text())
    if len(variants) != VARIANTS:
        raise ValueError(f'expected {VARIANTS} variant summaries')
    t = diagnosis.t_quantile(1 - 0.05 / (2 * VARIANTS), 4 * 4096 - 1)
    result, rows = {'format': 'nplayer-live-order-variants-v1', 'primary': PRIMARY, 'variants': {}}, []
    for name, s in variants.items():
        entry = {}
        for field in screen.FIELDS:
            f = s['fields'][field]
            adjusted = f['change']['adjusted']
            if field == PRIMARY:
                half = t * adjusted['standard_error_bb100']
                interval = [adjusted['mean_bb100'] - half, adjusted['mean_bb100'] + half]
                label = f'Bonferroni 95% over {VARIANTS} variants'
            else:
                interval, label = f['family_interval'], 'Bonferroni 95% over seven fields'
            verdict = nodes.verdict(*interval)
            entry[field] = {'change_bb100': adjusted['mean_bb100'], 'individual95': [adjusted['lower95_bb100'], adjusted['upper95_bb100']],
                            'decision_interval': interval, 'decision_interval_type': label, 'verdict': verdict,
                            'harm_flag': bool(f.get('harm_flag')),
                            'absolute': {k: v['adjusted']['mean_bb100'] for k, v in f['absolute'].items()}}
            rows.append({'variant': name, 'field': field, 'change_bb100': adjusted['mean_bb100'],
                         'individual_lower95': adjusted['lower95_bb100'], 'individual_upper95': adjusted['upper95_bb100'],
                         'decision_lower95': interval[0], 'decision_upper95': interval[1], 'decision_interval': label,
                         'verdict': verdict, 'harm_flag': entry[field]['harm_flag']})
        result['variants'][name] = {'verdict': 'improved' if entry[PRIMARY]['verdict'] == 'improved' else 'not shown', 'fields': entry}
    args.results.mkdir(parents=True, exist_ok=True)
    diagnosis.create(args.results / 'variants.json', json.dumps(result, indent=1) + '\n')
    with (args.results / 'variants.csv').open('x', newline='') as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({n: v['verdict'] for n, v in result['variants'].items()}))


def h2h_manifest(args):
    """Focals 10B ('ten') and 50B ('later'); one field each against five copies of either."""
    old = json.loads(Path(screen.CONTROL_MANIFEST).read_text())
    case = next(c for c in old['cases'] if c['name'] == 'trained')
    models = {'ten': screen.model(args.control_binary, args.control_mass), 'later': screen.model(args.binary, args.mass)}
    for bank in range(screen.BANKS):
        folder = args.out / 'arena' / f'b{bank}'
        folder.mkdir(parents=True, exist_ok=True)
        cases = []
        for index, (field, opponent) in enumerate(zip(H2H_FIELDS, ('ten', 'later'))):
            row = {k: case[k] for k in ('players', 'stack_bb', 'blocks', 'schedule')}
            row.update(name=f'b{bank}-{field}', root=H2H_ROOT + 100 * bank + index, focals=['ten', 'later'], opponents=[opponent] * 5,
                       traces=[str(folder / f'{field}-{a}.jsonl') for a in ('control', 'later')], summary=str(folder / f'{field}-cost.json'))
            cases.append(row)
        diagnosis.create(args.out / f'arena-manifest-b{bank}.json', json.dumps(
            {'format': 'nplayer-paired-manifest-v1', 'tables': old['tables'], 'threads': 16, 'models': models, 'cases': cases}, indent=1) + '\n')


def h2h_scan(args):
    arena = json.loads((args.out / 'arena-manifest-b0.json').read_text())
    pins = {'control': arena['models']['ten']['sha256'], 'later': arena['models']['later']['sha256']}
    for bank in range(screen.BANKS):
        for field in H2H_FIELDS:
            for arm, pin in pins.items():
                trace = args.out / 'arena' / f'b{bank}' / f'{field}-{arm}.jsonl'
                if trace.exists() and not (args.out / 'receipts' / f'{arm}-b{bank}--{field}.json').exists():
                    diagnosis.scan_file((str(trace), str(args.out), f'{arm}-b{bank}', field, None, pin, None))


def h2h_report(args):
    """50B minus 10B per field, all-in adjusted, with individual 95% intervals over 16,384 blocks."""
    receipts = {(r['label'], r['field']): r for r in (json.loads(p.read_text()) for p in (args.out / 'receipts').glob('*.json'))}
    result = {'format': 'nplayer-live-order-h2h-v1', 'fields': {}}
    for field in H2H_FIELDS:
        deltas, absolute = [], {'control': [], 'later': []}
        for bank in range(screen.BANKS):
            means = {}
            for arm in absolute:
                label = f'{arm}-b{bank}'
                hands = diagnosis.hand_rows(args.out, label, field)
                means[arm] = diagnosis.block_means(hands, 'adjusted', receipts[label, field]['seatings'], 100)
                absolute[arm] += means[arm]
            deltas += [b - a for a, b in zip(means['control'], means['later'])]
        result['fields'][field] = {'change_50b_minus_10b': diagnosis.interval(deltas),
                                   'absolute': {k: diagnosis.interval(v) for k, v in absolute.items()}}
    args.results.mkdir(parents=True, exist_ok=True)
    diagnosis.create(args.results / 'h2h.json', json.dumps(result, indent=1) + '\n')
    print(json.dumps({f: v['change_50b_minus_10b'] for f, v in result['fields'].items()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    commands = ('manifest', 'scan', 'equity', 'rows', 'training', 'report', 'combine', 'h2h-manifest', 'h2h-scan', 'h2h-report')
    for name in commands:
        p = sub.add_parser(name)
        if name == 'combine':
            p.add_argument('--summary', nargs=VARIANTS, required=True, help='NAME=summary.json per variant')
            p.add_argument('--results', type=Path, required=True)
            continue
        p.add_argument('--out', type=Path, required=True)
        if name in ('manifest', 'training', 'h2h-manifest'):
            p.add_argument('--mass', type=Path, required=True)
            p.add_argument('--control-mass', type=Path, required=True)
        if name in ('manifest', 'h2h-manifest'):
            p.add_argument('--binary', type=Path, required=True)
            p.add_argument('--control-binary', type=Path, required=True)
        if name in ('rows', 'training'):
            p.add_argument('--checkpoint', type=Path, required=True)
            p.add_argument('--control-checkpoint', type=Path, required=True)
        if name in ('scan', 'rows'):
            p.add_argument('--workers', type=int, default=12)
        if name == 'equity':
            p.add_argument('--binary', type=Path, required=True)
        if name in ('report', 'h2h-report'):
            p.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    {'manifest': manifest, 'scan': lambda a: screen.scan(a, arm=ARM), 'equity': diagnosis.equity,
     'rows': lambda a: admission.rows(a, arm=ARM, control=(a.control_checkpoint, screen.sha(a.control_checkpoint))),
     'training': training, 'report': lambda a: admission.report(a, arm=ARM, fmt=FORMAT), 'combine': combine,
     'h2h-manifest': h2h_manifest, 'h2h-scan': h2h_scan, 'h2h-report': h2h_report}[args.command](args)


if __name__ == '__main__':
    main()
