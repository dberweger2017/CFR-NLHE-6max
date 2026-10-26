"""Six-player opponent-pressure screen: #417's 10B against the pressure-trained 10B.

`manifest` builds the paired arena on fresh banks, `scan` and `equity` reuse the
loss-diagnosis scanner and exact all-in tool, and `report` applies the decision
rule of docs/nplayer-opponent-pressure.md. Later one-arm screens against the same
control and banks reuse these steps with their own arm name and primary field.
"""
import argparse
import csv
import hashlib
import json
import math
from multiprocessing import Pool
from pathlib import Path

from scripts import nplayer_loss_diagnosis as diagnosis

CONTROL_MANIFEST = '/home/dberweger/nplayer-six-player-candidate-20261023/main-v1/10b-initial-manifest.json'
CONTROL_SHA = '086938a88f1b302688b00cf52666162350e02e3b1212aa590bb6bf4941c46178'
FIELDS = ('trained', 'random', 'check-call', 'tight-aggressive', 'pot-pressure', 'call-pressure', 'random-tight',
          'trained-call-pressure')
PRIMARY = 'pot-pressure'
BANKS = 4
ROOT = 20261025900000
ARMS = ('control', 'pressure')


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def model(binary, mass):
    return {'path': str(binary), 'sha256': sha(binary), 'mass': str(mass), 'mass_sha256': sha(Path(mass) / 'receipt.json')}


def manifest(args, arm='pressure', control=None, root=ROOT):
    """`control` replaces #417's 10B as the control focal; `root` places a new set of banks."""
    old = json.loads(Path(CONTROL_MANIFEST).read_text())
    keep = ('path', 'sha256', 'mass', 'mass_sha256')
    if old['models']['candidate']['sha256'] != CONTROL_SHA:
        raise ValueError('control 10B pin differs')
    receipt = args.mass / 'receipt.json'
    models = {'ten': control or {k: old['models']['candidate'][k] for k in keep},
              'three': {k: old['models']['baseline'][k] for k in keep},
              arm: {'path': str(args.binary), 'sha256': sha(args.binary), 'mass': str(args.mass), 'mass_sha256': sha(receipt)}}
    by_name = {c['name']: c for c in old['cases']}
    # One manifest per bank, so each bank's traces can be scanned and compressed before the next.
    for bank in range(BANKS):
        cases, late = [], []
        folder = args.out / 'arena' / f'b{bank}'
        folder.mkdir(parents=True, exist_ok=True)
        for index, field in enumerate(FIELDS):
            case = by_name[field]
            opponents = ['three' if o == 'baseline' else o for o in case['opponents']]
            row = {k: case[k] for k in ('players', 'stack_bb', 'blocks', 'schedule')}
            row.update(name=f'b{bank}-{field}', root=root + 100 * bank + index, focals=['ten', arm], opponents=opponents,
                       traces=[str(folder / f'{field}-{a}.jsonl') for a in ('control', arm)], summary=str(folder / f'{field}-cost.json'))
            (late if 'three' in opponents else cases).append(row)
        # 10B-only fields first so the 3B loads once, for the trained fields at the end.
        target = args.out / f'arena-manifest-b{bank}.json'
        diagnosis.create(target, json.dumps({'format': 'nplayer-paired-manifest-v1', 'tables': old['tables'], 'threads': 16,
                                             'models': models, 'cases': cases + late}, indent=1) + '\n')
    print(json.dumps({'manifests': BANKS, f'{arm}_sha256': models[arm]['sha256']}))


def jobs(out, arm='pressure'):
    arena = json.loads((out / 'arena-manifest-b0.json').read_text())
    pins = {'control': arena['models']['ten']['sha256'], arm: arena['models'][arm]['sha256']}
    work = []
    for bank in range(BANKS):
        for field in FIELDS:
            for arm in pins:
                trace = out / 'arena' / f'b{bank}' / f'{field}-{arm}.jsonl'
                if not trace.exists():
                    continue
                work.append((str(trace), str(out), f'{arm}-b{bank}', field, None, pins[arm], None))
    return work


def scan(args, arm='pressure'):
    work = [j for j in jobs(args.out, arm) if not (args.out / 'receipts' / f'{j[2]}--{j[3]}.json').exists()]
    with Pool(args.workers) as pool:
        for receipt in pool.imap_unordered(diagnosis.scan_file, work):
            print(json.dumps({k: receipt[k] for k in ('label', 'field', 'hands', 'mean_bb100')}), flush=True)


def untrained_share(receipts, arm, field):
    total, untrained = {s: 0 for s in diagnosis.STREETS}, {s: 0 for s in diagnosis.STREETS}
    for bank in range(BANKS):
        for key, (count, _) in receipts[f'{arm}-b{bank}', field]['decisions'].items():
            street, status = key.split('|')[:2]
            total[street] += count
            untrained[street] += count if status in diagnosis.UNTRAINED else 0
    shares = {s: untrained[s] / total[s] if total[s] else None for s in diagnosis.STREETS}
    shares['all'] = sum(untrained.values()) / sum(total.values())
    return shares


def report(args, arm='pressure', primary=PRIMARY, fmt='nplayer-pressure-screen-v1'):
    """Writes summary.json and fields.csv for `arm` minus control; returns the summary."""
    names = ('control', arm)
    receipts = {(r['label'], r['field']): r for r in (json.loads(p.read_text()) for p in (args.out / 'receipts').glob('*.json'))}
    family = diagnosis.t_quantile(1 - 0.05 / (2 * (len(FIELDS) - 1)), 4 * 4096 - 1)
    fields, rows = {}, []
    for field in FIELDS:
        deltas = {'realized': [], 'adjusted': []}
        absolute = {name: {'realized': [], 'adjusted': []} for name in names}
        per_bank = []
        for bank in range(BANKS):
            means = {}
            for name in names:
                label = f'{name}-b{bank}'
                hands = diagnosis.hand_rows(args.out, label, field)
                seatings = receipts[label, field]['seatings']
                means[name] = {key: diagnosis.block_means(hands, key, seatings, 100) for key in ('reward', 'adjusted')}
            bank_delta = {}
            for key, kind in (('reward', 'realized'), ('adjusted', 'adjusted')):
                d = [p - c for c, p in zip(means['control'][key], means[arm][key])]
                deltas[kind] += d
                bank_delta[kind] = sum(d) / len(d)
                for name in names:
                    absolute[name][kind] += means[name][key]
            per_bank.append(bank_delta)
        entry = {'change': {k: diagnosis.interval(v) for k, v in deltas.items()},
                 'absolute': {name: {k: diagnosis.interval(v) for k, v in values.items()} for name, values in absolute.items()},
                 'per_bank_change': per_bank,
                 'untrained_share': {name: untrained_share(receipts, name, field) for name in names}}
        adjusted = entry['change']['adjusted']
        if field == primary:
            entry['verdict'] = 'improved' if adjusted['lower95_bb100'] > 0 else 'not shown'
        else:
            half = family * adjusted['standard_error_bb100']
            entry['family_interval'] = [adjusted['mean_bb100'] - half, adjusted['mean_bb100'] + half]
            entry['harm_flag'] = adjusted['mean_bb100'] + half < 0
        fields[field] = entry
        rows.append({'field': field, 'change_adjusted_bb100': adjusted['mean_bb100'], 'lower95': adjusted['lower95_bb100'],
                     'upper95': adjusted['upper95_bb100'], 'change_realized_bb100': entry['change']['realized']['mean_bb100'],
                     'control_adjusted_bb100': entry['absolute']['control']['adjusted']['mean_bb100'],
                     f'{arm}_adjusted_bb100': entry['absolute'][arm]['adjusted']['mean_bb100'],
                     'control_untrained_share': entry['untrained_share']['control']['all'],
                     f'{arm}_untrained_share': entry['untrained_share'][arm]['all'],
                     'verdict_or_harm': entry.get('verdict', 'harm' if entry.get('harm_flag') else 'no harm flag')})
    summary = {'format': fmt, 'primary': primary, 'verdict': fields[primary]['verdict'],
               'harm_flags': [f for f in FIELDS if fields[f].get('harm_flag')], 'fields': fields,
               'traces': {f'{k[0]}/{k[1]}': v['sha256'] for k, v in sorted(receipts.items())}}
    args.results.mkdir(parents=True, exist_ok=True)
    (args.results / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    with (args.results / 'fields.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({'verdict': summary['verdict'], 'harm_flags': summary['harm_flags'], 'primary': fields[primary]['change']['adjusted']}))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    m = sub.add_parser('manifest')
    m.add_argument('--binary', type=Path, required=True)
    m.add_argument('--mass', type=Path, required=True)
    for name in ('manifest', 'scan', 'equity', 'report'):
        p = m if name == 'manifest' else sub.add_parser(name)
        p.add_argument('--out', type=Path, required=True)
        if name == 'scan':
            p.add_argument('--workers', type=int, default=12)
        if name == 'equity':
            p.add_argument('--binary', type=Path, required=True)
        if name == 'report':
            p.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    {'manifest': manifest, 'scan': scan, 'equity': diagnosis.equity, 'report': report}[args.command](args)


if __name__ == '__main__':
    main()
