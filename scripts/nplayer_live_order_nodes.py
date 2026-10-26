"""Six-player live-order node ladder: one lineage's earlier checkpoint against its later one.

Each contrast (10B against 30B, 30B against 50B of #431's live-order lineage)
plays the screens' fields with #417's 3B as the trained-field opponent on one
new set of banks, under its own output folder. The earlier checkpoint is the
`control` arm. `ladder` applies the decision rule of docs/nplayer-live-order-nodes.md.
"""
import argparse
import csv
import json
from pathlib import Path

from scripts import nplayer_admission_screen as admission
from scripts import nplayer_live_order_screen as live
from scripts import nplayer_loss_diagnosis as diagnosis
from scripts import nplayer_pressure_screen as screen

ARM = 'later'
FORMAT = 'nplayer-live-order-nodes-v1'
ROOT = 20261026800000
PRIMARY = 'trained'
SCHEMA = 'nplayer-live-order-summary-equity-k50-v1'


def manifest(args):
    screen.manifest(args, arm=ARM, control=screen.model(args.control_binary, args.control_mass), root=ROOT)


def training(args):
    result = {}
    for name, checkpoint, mass in (('control', args.control_checkpoint, args.control_mass), (ARM, args.checkpoint, args.mass)):
        h = admission.header(checkpoint)
        if h['game']['schema'] != SCHEMA:
            raise ValueError(f'{name}: not a live-order checkpoint')
        result[name] = admission.telemetry(h, json.loads((mass / 'receipt.json').read_text()))
    if result['control']['nodes'] >= result[ARM]['nodes']:
        raise ValueError('the later checkpoint must have more nodes')
    diagnosis.create(args.out / 'training.json', json.dumps(result, indent=1) + '\n')
    print(json.dumps({a: {k: v for k, v in t.items() if k != 'by_street'} for a, t in result.items()}))


def breakdown(args):
    """Descriptive per-category contributions to one contrast's changes."""
    fields, flat = live.contributions(args.out, arm=ARM)
    live.write_breakdown(args.results, {'fields': fields}, flat)


def verdict(adjusted):
    if adjusted['lower95_bb100'] > 0:
        return 'improved'
    return 'worse' if adjusted['upper95_bb100'] < 0 else 'not resolved'


def ladder(args):
    """Both contrasts' changes per field; the primary is the first contrast's trained field."""
    contrasts = {}
    for spec in args.summary:
        name, path = spec.split('=', 1)
        contrasts[name] = json.loads(Path(path).read_text())
    first, second = list(contrasts)
    fields, rows = {}, []
    for field in screen.FIELDS:
        entry = {}
        for name, s in contrasts.items():
            adjusted = s['fields'][field]['change']['adjusted']
            entry[name] = {'change': adjusted, 'verdict': verdict(adjusted), 'harm_flag': bool(s['fields'][field].get('harm_flag')),
                           'absolute': {k: v['adjusted']['mean_bb100'] for k, v in s['fields'][field]['absolute'].items()}}
            rows.append({'field': field, 'contrast': name, 'change_bb100': adjusted['mean_bb100'], 'lower95': adjusted['lower95_bb100'],
                         'upper95': adjusted['upper95_bb100'], 'verdict': entry[name]['verdict'], 'harm_flag': entry[name]['harm_flag']})
        fields[field] = entry
    result = {'format': FORMAT, 'primary': PRIMARY, 'contrasts': list(contrasts),
              'verdict': 'improved' if fields[PRIMARY][first]['verdict'] == 'improved' else 'not shown',
              'second_contrast': fields[PRIMARY][second]['verdict'], 'fields': fields}
    args.results.mkdir(parents=True, exist_ok=True)
    diagnosis.create(args.results / 'ladder.json', json.dumps(result, indent=1) + '\n')
    with (args.results / 'ladder.csv').open('x', newline='') as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({'verdict': result['verdict'], 'second_contrast': result['second_contrast']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('manifest', 'scan', 'equity', 'rows', 'training', 'report', 'ladder', 'breakdown'):
        p = sub.add_parser(name)
        if name == 'ladder':
            p.add_argument('--summary', nargs=2, required=True, help='NAME=summary.json for the first, then the second contrast')
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
        if name in ('scan', 'rows'):
            p.add_argument('--workers', type=int, default=12)
        if name == 'equity':
            p.add_argument('--binary', type=Path, required=True)
        if name in ('report', 'breakdown'):
            p.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    {'manifest': manifest, 'scan': lambda a: screen.scan(a, arm=ARM), 'equity': diagnosis.equity,
     'rows': lambda a: admission.rows(a, arm=ARM, control=(a.control_checkpoint, screen.sha(a.control_checkpoint))),
     'training': training, 'report': lambda a: admission.report(a, arm=ARM, fmt=FORMAT), 'ladder': ladder, 'breakdown': breakdown}[args.command](args)


if __name__ == '__main__':
    main()
