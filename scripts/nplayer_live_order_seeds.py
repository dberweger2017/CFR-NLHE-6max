"""Six-player live-order seed confirmation: for each new seed, its history-key 10B against
its live-order 10B, both trained from scratch with #417's recipe.

Each seed uses the screens' fields with #417's 3B as the trained-field opponent,
on one new set of banks shared by both seeds, under its own output folder. The
per-seed steps reuse the opponent-pressure and admission screens; `combine`
applies the decision rule of docs/nplayer-live-order-seeds.md across the new
seeds and #431's.
"""
import argparse
import csv
import json
import math
from pathlib import Path

from scripts import nplayer_admission_screen as admission
from scripts import nplayer_loss_diagnosis as diagnosis
from scripts import nplayer_pressure_screen as screen

ARM = 'live'
FORMAT = 'nplayer-live-order-seed-v1'
ROOT = 20261026700000
PRIMARY = 'trained'
SCHEMAS = {'control': 'nplayer-button-live-actor-history-equity-k50-v1', ARM: 'nplayer-live-order-summary-equity-k50-v1'}


def manifest(args):
    screen.manifest(args, arm=ARM, control=screen.model(args.control_binary, args.control_mass), root=ROOT)


def training(args):
    result = {}
    for name, checkpoint, mass in (('control', args.control_checkpoint, args.control_mass), (ARM, args.checkpoint, args.mass)):
        h = admission.header(checkpoint)
        if h['game']['schema'] != SCHEMAS[name] or h['seed'] != args.seed:
            raise ValueError(f'{name}: schema or seed differs')
        result[name] = admission.telemetry(h, json.loads((mass / 'receipt.json').read_text()))
    diagnosis.create(args.out / 'training.json', json.dumps(result, indent=1) + '\n')
    print(json.dumps({a: {k: v for k, v in t.items() if k != 'by_street'} for a, t in result.items()}))


def t95(df):
    return diagnosis.t_quantile(0.975, df)


def combine(args):
    """Per-seed changes from each summary; across-seed mean with a Student-t interval over seeds."""
    seeds = {}
    for spec in args.summary:
        name, path = spec.split('=', 1)
        seeds[name] = json.loads(Path(path).read_text())
    new = [n for n in seeds if n != args.reference]
    fields, rows = {}, []
    for field in screen.FIELDS:
        per = {n: s['fields'][field]['change']['adjusted'] for n, s in seeds.items()}
        means = [p['mean_bb100'] for p in per.values()]
        mean = sum(means) / len(means)
        sd = math.sqrt(sum((m - mean) ** 2 for m in means) / (len(means) - 1))
        half = t95(len(means) - 1) * sd / math.sqrt(len(means))
        entry = {'per_seed': per, 'across_seeds': {'mean_bb100': mean, 'sd_bb100': sd, 'lower95_bb100': mean - half,
                                                    'upper95_bb100': mean + half, 'seeds': len(means)},
                 'harm_flags': [n for n, s in seeds.items() if s['fields'][field].get('harm_flag')]}
        fields[field] = entry
        for n, p in per.items():
            rows.append({'field': field, 'seed': n, 'change_bb100': p['mean_bb100'], 'lower95': p['lower95_bb100'],
                         'upper95': p['upper95_bb100'], 'harm_flag': bool(seeds[n]['fields'][field].get('harm_flag'))})
        rows.append({'field': field, 'seed': 'across seeds', 'change_bb100': mean, 'lower95': mean - half,
                     'upper95': mean + half, 'harm_flag': None})
    confirmed = all(seeds[n]['fields'][PRIMARY]['change']['adjusted']['lower95_bb100'] > 0 for n in new)
    result = {'format': 'nplayer-live-order-seeds-v1', 'primary': PRIMARY, 'new_seeds': new, 'reference': args.reference,
              'verdict': 'confirmed' if confirmed else 'not confirmed', 'fields': fields}
    args.results.mkdir(parents=True, exist_ok=True)
    diagnosis.create(args.results / 'seeds.json', json.dumps(result, indent=1) + '\n')
    with (args.results / 'seeds.csv').open('x', newline='') as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({'verdict': result['verdict'], 'primary': fields[PRIMARY]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('manifest', 'scan', 'equity', 'rows', 'training', 'report', 'combine'):
        p = sub.add_parser(name)
        if name == 'combine':
            p.add_argument('--summary', nargs='+', required=True, help='NAME=summary.json for every seed')
            p.add_argument('--reference', default='2026102361001', help='the seed already screened in #431')
            p.add_argument('--results', type=Path, required=True)
            continue
        p.add_argument('--out', type=Path, required=True)
        if name in ('manifest', 'training'):
            p.add_argument('--mass', type=Path, required=True)
            p.add_argument('--control-mass', type=Path, required=True)
        if name == 'manifest':
            p.add_argument('--binary', type=Path, required=True)
            p.add_argument('--control-binary', type=Path, required=True)
        if name in ('rows', 'training'):
            p.add_argument('--checkpoint', type=Path, required=True)
            p.add_argument('--control-checkpoint', type=Path, required=True)
        if name == 'training':
            p.add_argument('--seed', type=int, required=True)
        if name in ('scan', 'rows'):
            p.add_argument('--workers', type=int, default=12)
        if name == 'equity':
            p.add_argument('--binary', type=Path, required=True)
        if name == 'report':
            p.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    {'manifest': manifest, 'scan': lambda a: screen.scan(a, arm=ARM), 'equity': diagnosis.equity,
     'rows': lambda a: admission.rows(a, arm=ARM, control=(a.control_checkpoint, screen.sha(a.control_checkpoint))),
     'training': training, 'report': lambda a: admission.report(a, arm=ARM, fmt=FORMAT),
     'combine': combine}[args.command](args)


if __name__ == '__main__':
    main()
