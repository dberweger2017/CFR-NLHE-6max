"""Six-player traverser-admission screen: #417's 10B against the traverser-admission 10B.

Reuses the opponent-pressure screen's control, fields and fresh banks. `rows`
classifies every focal lookup by its training row: a positive-mass row whose
`visits` is zero was stored only from opponent updates, so its regrets are zero
and it plays exactly the uniform fallback. `training` gathers both checkpoints'
telemetry and row composition, and `report` applies the decision rule of
docs/nplayer-traverser-admission.md.
"""
import argparse
import csv
import gzip
import json
import subprocess
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

from scripts import nplayer_loss_diagnosis as diagnosis
from scripts import nplayer_pressure_screen as screen

ARM = 'admission'
PRIMARY = 'trained'
FORMAT = 'nplayer-admission-screen-v1'
CONTROL_CHECKPOINT = '/home/dberweger/nplayer-six-player-candidate-20261023/main-v1/10b-train.gz'
CONTROL_CHECKPOINT_SHA = '4c10ded3a1f8289cd8483da543cd577ed15f98d80047a524ce41c3990cfe7edd'
CONTROL_MASS = '/home/dberweger/nplayer-six-player-candidate-20261023/main-v1/2026102361001-10b-mass/receipt.json'
CLASSES = ('learned', 'opponent_only', 'zero_mass', 'missing')


def trace_path(out, bank, field, arm):
    plain = out / 'arena' / f'b{bank}' / f'{field}-{arm}.jsonl'
    return plain if plain.exists() else plain.with_name(plain.name + '.gz')


def focal_lookups(job):
    """Counts of (street, status, key) over the focal identity's lookups in one trace."""
    path, label, field = job
    counts = defaultdict(int)
    with (gzip.open if path.endswith('.gz') else open)(path, 'rt') as f:
        next(f)
        for line in f:
            for lookup in json.loads(line)['lookups']:
                if lookup.get('identity') == 0:
                    key = lookup['key'] if lookup['status'] == 'positive_mass' else ''
                    counts[lookup['street'], lookup['status'], key] += 1
    return label, field, dict(counts)


def visits(checkpoint, keys):
    """Visits of each key in `keys` that the checkpoint stores, streaming its rows once."""
    wanted = {k.encode() for k in keys}
    found = {}
    with subprocess.Popen(['gzip', '-dc', str(checkpoint)], stdout=subprocess.PIPE) as proc:
        next(proc.stdout)
        for line in proc.stdout:
            # Rows are ["<32 hex key>",owner,street,code,visits,regrets,average].
            if line[2:34] in wanted:
                found[line[2:34].decode()] = json.loads(line)[4]
    if proc.returncode:
        raise ValueError(f'{checkpoint}: decompression failed')
    return found


def classify(counts, row_visits):
    by_street = {s: dict.fromkeys(CLASSES, 0) for s in diagnosis.STREETS}
    for (street, status, key), n in counts.items():
        if status == 'positive_mass':
            if key not in row_visits:
                raise ValueError(f'positive-mass key {key} absent from the training checkpoint')
            cls = 'learned' if row_visits[key] > 0 else 'opponent_only'
        elif status in ('zero_mass', 'missing'):
            cls = status
        else:
            raise ValueError(f'unexpected focal lookup status {status}')
        by_street[diagnosis.STREETS[street]][cls] += n
    return by_street


def rows(args, arm=ARM, control=(CONTROL_CHECKPOINT, CONTROL_CHECKPOINT_SHA)):
    """`control` is the control's training checkpoint and its pinned SHA256."""
    checkpoints = {'control': Path(control[0]), arm: args.checkpoint}
    if screen.sha(checkpoints['control']) != control[1]:
        raise ValueError('control checkpoint pin differs')
    work = [(str(trace_path(args.out, bank, field, a)), f'{a}-b{bank}', field)
            for bank in range(screen.BANKS) for field in screen.FIELDS for a in checkpoints]
    with Pool(args.workers) as pool:
        traces = pool.map(focal_lookups, work)
        keys = {a: {k for label, _, c in traces if label.startswith(a + '-') for _, _, k in c if k} for a in checkpoints}
        found = dict(zip(checkpoints, pool.starmap(visits, [(checkpoints[a], keys[a]) for a in checkpoints])))
    result = {a: {field: {s: dict.fromkeys(CLASSES, 0) for s in diagnosis.STREETS} for field in screen.FIELDS} for a in checkpoints}
    for label, field, counts in traces:
        a = label.rsplit('-b', 1)[0]
        for street, by_class in classify(counts, found[a]).items():
            for cls, n in by_class.items():
                result[a][field][street][cls] += n
    receipt = {'format': 'nplayer-admission-rows-v1', 'checkpoints': {a: screen.sha(p) for a, p in checkpoints.items()},
               'distinct_positive_keys': {a: len(keys[a]) for a in checkpoints}, 'decisions': result}
    diagnosis.create(args.out / 'rows.json', json.dumps(receipt, indent=1) + '\n')
    print(json.dumps(receipt['distinct_positive_keys']))


def header(checkpoint):
    with gzip.open(checkpoint, 'rt') as f:
        return json.loads(f.readline())


def telemetry(h, mass):
    c = h['counts']
    zero_visit = sum(s['zero_visit_entries'] for s in mass['by_street'])
    return {'iterations': h['iteration'], 'nodes': c['nodes'], 'entries': h['entries'], 'frozen_at': h['frozen_at'],
            'declined_keys': h.get('admission', {}).get('declined_keys'),
            'missing_decision_share': sum(c['missing']) / sum(c['decisions']),
            'discarded_traverser_visit_share': c['discarded_visits'] / sum(c['traverser']),
            'opponent_only_rows': zero_visit, 'zero_mass_rows': mass['zero_mass_rows'],
            'learned_rows': h['entries'] - zero_visit - mass['zero_mass_rows'],
            'by_street': mass['by_street']}


def training(args):
    control = header(CONTROL_CHECKPOINT)
    arm = header(args.checkpoint)
    if arm.get('admission', {}).get('rule') != 'traverser-admission-v1' or 'admission' in control:
        raise ValueError('arm must record traverser admission and the control must not')
    result = {'control': telemetry(control, json.loads(Path(CONTROL_MASS).read_text())),
              ARM: telemetry(arm, json.loads((args.mass / 'receipt.json').read_text()))}
    diagnosis.create(args.out / 'training.json', json.dumps(result, indent=1) + '\n')
    print(json.dumps({a: {k: v for k, v in t.items() if k != 'by_street'} for a, t in result.items()}))


def shares(by_street):
    out = {}
    for street, counts in by_street.items():
        total = sum(counts.values())
        out[street] = {cls: counts[cls] / total if total else None for cls in CLASSES}
    every = {cls: sum(c[cls] for c in by_street.values()) for cls in CLASSES}
    out['all'] = {cls: every[cls] / sum(every.values()) for cls in CLASSES}
    return out


def report(args, arm=ARM, fmt=FORMAT):
    summary = screen.report(args, arm=arm, primary=PRIMARY, fmt=fmt)
    decisions = json.loads((args.out / 'rows.json').read_text())['decisions']
    summary['training'] = json.loads((args.out / 'training.json').read_text())
    rows_out = []
    for field in screen.FIELDS:
        summary['fields'][field]['row_classes'] = {a: shares(decisions[a][field]) for a in ('control', arm)}
        for a in ('control', arm):
            for street, s in summary['fields'][field]['row_classes'][a].items():
                rows_out.append({'field': field, 'arm': a, 'street': street, **s})
    (args.results / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    with (args.results / 'rows.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, list(rows_out[0]))
        w.writeheader()
        w.writerows(rows_out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('manifest', 'scan', 'equity', 'rows', 'training', 'report'):
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
        if name == 'report':
            p.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    {'manifest': lambda a: screen.manifest(a, arm=ARM), 'scan': lambda a: screen.scan(a, arm=ARM), 'equity': diagnosis.equity,
     'rows': rows, 'training': training, 'report': report}[args.command](args)


if __name__ == '__main__':
    main()
