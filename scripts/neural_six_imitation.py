"""Matched-teacher 100 BB study; see docs/neural-six-imitation.md.

Reuses the existing trainer and Gate D reporting without changing either gate.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from scripts import neural_policy_everywhere as everywhere
from scripts import neural_policy_imitation as imitation
from scripts import neural_policy_samples as samples
from scripts import openpoker_phantom_depth as study

PINS = {
    'six': ('f894a59f8a92424d735438726d16834901a7dcaf6d560c98b950fb72a143c9ea',
            '806e7b9c92b7fbfd8f6ea2de30535d4dc7a525cc096091c458fe1e6c15000bda'),
    'peer': ('ab7f8e166448b51cd54be3c9163936126f2b6cff2925b2fa374e7a1db783488b',
             '366507548dfdd5d9fd4aa44386f02ac8838947766c8f9b6378878f3d0872188b'),
}
FIELDS = {'self': ['six'] * 6,
          'mixed': ['six'] + [f'bot={s}' for s in study.MIXED[6]]}
FIELDS.update({s: ['six'] + [f'bot={s}'] * 5
               for s in ('pot-pressure', 'tight-aggressive', 'check-call', 'random')})
EXPORT_ROOTS = {'train': 20261110000000, 'heldout': 20261111000000}
ARENA_ROOT = 20261113000000


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(value, f, indent=1)
        f.write('\n')


def catalog(inputs, verify=True):
    out = {}
    for name, (binary, mass) in PINS.items():
        path, folder = Path(inputs) / f'{name}.bin', Path(inputs) / f'{name}-mass'
        if verify and (imitation.sha_file(path) != binary or imitation.sha_file(folder / 'receipt.json') != mass):
            raise ValueError(f'{name}: input pin differs')
        out[name] = {'path': str(path), 'sha256': binary, 'mass': str(folder), 'mass_sha256': mass}
    return out


def export_manifest(out, inputs, tables, threads, qualification=False, verify=True):
    out = Path(out)
    jobs = []
    if qualification:
        for t in (1, threads):
            name = f'determinism-t{t}'
            jobs.append({'name': name, 'players': 6, 'stacks': [100] * 6,
                         'hands': 2000, 'root': 20261112000000,
                         'seats': FIELDS['mixed'], 'threads': t,
                         'out': str(out / f'{name}.npfeat')})
    else:
        for split, hands in (('train', 400000), ('heldout', 20000)):
            for i, (field, seats) in enumerate(FIELDS.items()):
                jobs.append({'name': f'{split}-6p-100bb-{field}', 'players': 6,
                             'stacks': [100] * 6, 'hands': hands,
                             'root': EXPORT_ROOTS[split] + 1000 * i, 'seats': seats,
                             'out': str(out / split / f'{field}.npfeat')})
    models = catalog(inputs, verify)
    return {'format': 'nplayer-feature-manifest-v1', 'tables': str(tables),
            'models': {'six': models['six']}, 'teachers': ['six'],
            'threads': threads, 'jobs': jobs}


def gate_tables(run):
    return [t for t in everywhere.tables(run) if t['study'] == 'deep']


def decide(paths):
    # Refuse incomplete/mixed studies before invoking the unchanged Gate D rule.
    for path in paths:
        r = json.loads(Path(path).read_text())
        if set(r['tables']) != {'6p-100bb'}:
            raise ValueError('expected Gate D only')
        entry = r['tables']['6p-100bb']
        if entry['primary'] != 'trained' or set(entry['fields']) != set(gate_tables(1)[0]['fields']):
            raise ValueError('Gate D fields differ')
    return {'format': 'neural-six-imitation-decision-v1',
            'gate_d': everywhere.decide(paths)['gate_d']}


def diagnostics(args):
    """Bounded-memory descriptive fidelity, no rescue test or model selection."""
    import torch
    meta = json.loads((args.model / 'model.json').read_text())
    net = imitation.network(torch, meta['features'], meta['hidden'])
    net.load_state_dict(torch.load(args.model / 'weights.pt', map_location='cpu', weights_only=True))
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    net.to(device).eval()
    groups = defaultdict(lambda: {'records': 0, 'positive': 0, 'zero': 0, 'missing': 0,
                                  'tv_sum': 0., 'ce_sum': 0., 'top_agreement_count': 0})
    for path in args.data:
        s = samples.load(path, layout_sha256=meta['layout_sha256'])
        count = min(len(s), args.limit) if args.limit else len(s)
        for start in range(0, count, 65536):
            stop = min(start + 65536, count)
            r = s.records[start:stop]
            target, status = s.teacher(0, slice(start, stop))
            mask = s.legal(slice(start, stop))
            p = imitation.predict(torch, net, device, r['features'], mask)
            tv = imitation.tv(p, target)
            ce = -(target * np.log(np.maximum(p, 1e-30))).sum(1)
            agree = p.argmax(1) == target.argmax(1)
            for street in (None, 0, 1, 2, 3):
                sel = np.ones(len(r), bool) if street is None else r['street'] == street
                key = f'{path.stem}/' + ('all' if street is None else imitation.STREETS[street])
                g = groups[key]
                g['records'] += int(sel.sum())
                for name, st in [('positive', samples.POSITIVE), ('zero', samples.ZERO_MASS), ('missing', samples.MISSING)]:
                    g[name] += int((sel & (status == st)).sum())
                positive = sel & (status == samples.POSITIVE)
                g['tv_sum'] += float(tv[positive].sum())
                g['ce_sum'] += float(ce[positive].sum())
                g['top_agreement_count'] += int(agree[positive].sum())
    for g in groups.values():
        n = g['positive']
        for dest, source in [('tv', 'tv_sum'), ('cross_entropy', 'ce_sum'), ('top_agreement', 'top_agreement_count')]:
            g[dest] = g.pop(source) / n if n else None
    write_json(args.out, {'format': 'neural-six-imitation-fidelity-v1', 'model': meta,
                          'limit_per_file': args.limit, 'groups': dict(groups)})


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ('export-manifest', 'diagnostics', 'decide'):
        p = argparse.ArgumentParser(description=__doc__)
        sub = p.add_subparsers(dest='command', required=True)
        m = sub.add_parser('export-manifest')
        m.add_argument('--out', type=Path, required=True)
        m.add_argument('--inputs', type=Path, required=True)
        m.add_argument('--tables', type=Path, required=True)
        m.add_argument('--threads', type=int, required=True)
        m.add_argument('--qualification', action='store_true')
        m.add_argument('--manifest', type=Path, required=True)
        d = sub.add_parser('diagnostics')
        d.add_argument('--model', type=Path, required=True)
        d.add_argument('--data', type=Path, nargs='+', required=True)
        d.add_argument('--limit', type=int, default=0)
        d.add_argument('--out', type=Path, required=True)
        q = sub.add_parser('decide')
        q.add_argument('--results', type=Path, nargs=3, required=True)
        q.add_argument('--out', type=Path, required=True)
        a = p.parse_args(argv)
        if a.command == 'export-manifest':
            value = export_manifest(a.out, a.inputs, a.tables, a.threads, a.qualification)
            for job in value['jobs']:
                Path(job['out']).parent.mkdir(parents=True, exist_ok=True)
            write_json(a.manifest, value)
        elif a.command == 'diagnostics':
            diagnostics(a)
        else:
            write_json(a.out, decide(a.results))
        return
    # The existing arena pipeline owns paired blocks, intervals, equity and replay.
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--seed-run', type=int, choices=(1, 2, 3), required=True)
    p.add_argument('--tables', type=Path, required=True)
    p.add_argument('--threads', type=int, required=True)
    a, rest = p.parse_known_args(argv)
    study.tables, study.verdict = lambda: gate_tables(a.seed_run), everywhere.verdict
    study.ROOT = ARENA_ROOT + 100000 * (a.seed_run - 1)
    study.TABLES, study.BANKS = str(a.tables), 4 if a.seed_run == 1 else 1
    study.HARM_STUDIES, study.MARGIN = ('deep',), everywhere.MARGIN
    study.FORMAT = 'neural-six-imitation-v1'
    old = sys.argv
    try:
        sys.argv = [old[0]] + rest
        study.main()
    finally:
        sys.argv = old
    if rest and rest[0] == 'manifest':
        out = Path(rest[rest.index('--out') + 1])
        for path in out.glob('arena-manifest-b*.json'):
            m = json.loads(path.read_text())
            m['threads'] = a.threads
            path.write_text(json.dumps(m, indent=1) + '\n')


if __name__ == '__main__':
    main()
