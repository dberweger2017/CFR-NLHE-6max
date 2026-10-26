"""Six-player live-order key screen: #417's 10B against the live-order 10B.

Reuses the opponent-pressure screen's control, fields and fresh banks and the
traverser-admission screen's row classes, and applies the decision rule of
docs/nplayer-live-order-screen.md. `breakdown` is descriptive: it splits each
field's paired change into additive per-category contributions and tabulates
both runs' table growth.
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from scripts import nplayer_admission_screen as admission
from scripts import nplayer_loss_diagnosis as diagnosis
from scripts import nplayer_pressure_screen as screen

ARM = 'live'
FORMAT = 'nplayer-live-order-screen-v1'
SCHEMA = 'nplayer-live-order-summary-equity-k50-v1'


def training(args):
    control = admission.header(admission.CONTROL_CHECKPOINT)
    arm = admission.header(args.checkpoint)
    if arm['game']['schema'] != SCHEMA or control['game']['schema'] == SCHEMA:
        raise ValueError('arm must use live-order keys and the control history keys')
    result = {'control': admission.telemetry(control, json.loads(Path(admission.CONTROL_MASS).read_text())),
              ARM: admission.telemetry(arm, json.loads((args.mass / 'receipt.json').read_text()))}
    diagnosis.create(args.out / 'training.json', json.dumps(result, indent=1) + '\n')
    print(json.dumps({a: {k: v for k, v in t.items() if k != 'by_street'} for a, t in result.items()}))


CONTROL_PROGRESS = [f'/home/dberweger/nplayer-six-player-candidate-20261023/main-v1/{c}-train.gz.progress.jsonl' for c in ('3b', '6b', '10b')]
MILESTONES = (100_000_000, 200_000_000, 400_000_000, 600_000_000, 1_000_000_000, 2_000_000_000, 4_000_000_000,
              6_000_000_000, 8_000_000_000, 10_000_000_000)
DIMENSIONS = ('ending', 'position', 'preflop_line', 'untrained_first')


def growth(paths):
    rows = [json.loads(line) for path in paths for line in open(path)]
    rows = [r for r in rows if 'counts' in r and 'iteration' in r]
    out = []
    for target in MILESTONES:
        r = min((r for r in rows if r['counts']['nodes'] >= target), key=lambda r: r['counts']['nodes'], default=None)
        if r:
            c = r['counts']
            out.append({'nodes': c['nodes'], 'iteration': r['iteration'], 'entries': r['entries'], 'frozen_at': r['frozen_at'],
                        'missing_decision_share': sum(c['missing']) / sum(c['decisions']),
                        'discarded_traverser_visit_share': c['discarded_visits'] / sum(c['traverser'])})
    return out


def contributions(out, arm=ARM):
    """Each category's contribution is its summed adjusted result over all hands of the arm,
    so contributions add up to the arm's mean and their differences to the paired change.
    Returns per-field tables and the same rows flattened."""
    fields, flat = {}, []
    for field in screen.FIELDS:
        sums = {a: {d: defaultdict(lambda: [0, 0]) for d in DIMENSIONS} for a in ('control', arm)}
        hands = dict.fromkeys(('control', arm), 0)
        for a in ('control', arm):
            for bank in range(screen.BANKS):
                for r in diagnosis.hand_rows(out, f'{a}-b{bank}', field):
                    hands[a] += 1
                    for d in DIMENSIONS:
                        slot = sums[a][d][r[d]]
                        slot[0] += 1
                        slot[1] += r['adjusted']
        if hands['control'] != hands[arm]:
            raise ValueError(f'{field}: arms played different hand counts')
        n = hands['control']
        per_dimension = {}
        for d in DIMENSIONS:
            rows = []
            for category in sorted(set(sums['control'][d]) | set(sums[arm][d])):
                c, l = sums['control'][d].get(category, [0, 0]), sums[arm][d].get(category, [0, 0])
                # Chips per hand times 100 hands over a 100-chip big blind: BB/100.
                row = {'category': category, 'control_share': c[0] / n, f'{arm}_share': l[0] / n,
                       'control_bb100': c[1] / n, f'{arm}_bb100': l[1] / n, 'change_bb100': (l[1] - c[1]) / n}
                rows.append(row)
                flat.append({'field': field, 'dimension': d, **row})
            per_dimension[d] = sorted(rows, key=lambda r: r['change_bb100'])
        fields[field] = {'hands_per_arm': n, 'by': per_dimension}
    return fields, flat


def write_breakdown(results, result, flat):
    diagnosis.create(results / 'breakdown.json', json.dumps(result, indent=1) + '\n')
    with (results / 'breakdown.csv').open('x', newline='') as f:
        w = csv.DictWriter(f, list(flat[0]))
        w.writeheader()
        w.writerows(flat)


def breakdown(args):
    fields, flat = contributions(args.out)
    result = {'growth': {'control': growth(CONTROL_PROGRESS), ARM: growth([args.progress])}, 'fields': fields}
    write_breakdown(args.results, result, flat)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('manifest', 'scan', 'equity', 'rows', 'training', 'report', 'breakdown'):
        p = sub.add_parser(name)
        p.add_argument('--out', type=Path, required=True)
        if name == 'manifest':
            p.add_argument('--binary', type=Path, required=True)
        if name in ('manifest', 'training'):
            p.add_argument('--mass', type=Path, required=True)
        if name in ('rows', 'training'):
            p.add_argument('--checkpoint', type=Path, required=True)
        if name in ('scan', 'rows'):
            p.add_argument('--workers', type=int, default=12)
        if name == 'equity':
            p.add_argument('--binary', type=Path, required=True)
        if name in ('report', 'breakdown'):
            p.add_argument('--results', type=Path, required=True)
        if name == 'breakdown':
            p.add_argument('--progress', type=Path, required=True)
    args = parser.parse_args()
    {'manifest': lambda a: screen.manifest(a, arm=ARM), 'scan': lambda a: screen.scan(a, arm=ARM), 'equity': diagnosis.equity,
     'rows': lambda a: admission.rows(a, arm=ARM), 'training': training,
     'report': lambda a: admission.report(a, arm=ARM, fmt=FORMAT), 'breakdown': breakdown}[args.command](args)


if __name__ == '__main__':
    main()
