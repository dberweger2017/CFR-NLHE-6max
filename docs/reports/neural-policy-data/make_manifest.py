"""Writes the measurement manifests for docs/neural-policy-data.md on bb128.

Teachers: #458's three widemix seeds and #461's first widecap, all pinned by binary and mass
receipt. widemix run 1, the live model, plays every model seat.
"""
import hashlib
import json
import sys
from pathlib import Path

W = Path(sys.argv[1])
TABLES = '/home/dberweger/cygnus-qualification-20261014/tables'
MODELS = {f'widemix{r}': f'/home/dberweger/openpoker-wide-stacks-20261106/main/run{r}/widemix' for r in (1, 2, 3)}
MODELS['widecap1'] = '/home/dberweger/openpoker-wide-capacity-20261107/main/run1/widecap'
TEACHERS = ['widemix1', 'widemix2', 'widemix3', 'widecap1']
ROOT = 20261108300000
MIXED = {3: ['bot=check-call', 'bot=pot-pressure'], 4: ['bot=check-call', 'bot=pot-pressure', 'bot=tight-aggressive'],
         5: ['bot=check-call', 'bot=pot-pressure', 'bot=tight-aggressive', 'bot=random'],
         6: ['bot=check-call', 'bot=check-call', 'bot=pot-pressure', 'bot=pot-pressure', 'bot=tight-aggressive']}
SCRIPTS = ['pot-pressure', 'tight-aggressive', 'check-call', 'random']
SHORT = {'3p-5bb': [5, 5, 5], '3p-short-deep': [4, 100, 100], '3p-unequal': [8, 40, 100], '4p-short-deep': [5, 100, 100, 100],
         '6p-5bb': [5] * 6, '6p-short-deep': [3, 100, 100, 100, 100, 100], '6p-unequal': [8, 100, 50, 100, 150, 100]}


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 24), b''):
            h.update(block)
    return h.hexdigest()


def models():
    out = {}
    for alias, d in MODELS.items():
        pins = json.loads(Path(d, 'pins.json').read_text())
        assert sha(Path(d, 'mass', 'receipt.json')) == pins['mass_receipt'], alias
        out[alias] = {'path': f'{d}/model.bin', 'sha256': pins['binary'], 'mass': f'{d}/mass', 'mass_sha256': pins['mass_receipt']}
    return out


def jobs(out):
    js = []

    def job(name, players, stacks, hands, seats):
        js.append({'name': name, 'players': players, 'stacks': stacks, 'hands': hands, 'seats': seats,
                   'root': ROOT + 1000 * len(js), 'out': str(out / f'{name}.npfeat')})
    for n in (3, 4, 5, 6):
        job(f'wide-{n}p-self', n, 'wide-depth-grid-v1', 8000 if n == 6 else 4000, ['widemix1'] * n)
        job(f'wide-{n}p-mixed', n, 'wide-depth-grid-v1', 8000 if n == 6 else 4000, ['widemix1'] + MIXED[n])
    for name, stacks in SHORT.items():
        n = len(stacks)
        fields = {'mixed': MIXED[n]} | {s: [f'bot={s}'] * (n - 1) for s in SCRIPTS}
        if n == 6:
            fields['copies'] = ['widemix1'] * 5
        for field, rest in fields.items():
            job(f'{name}-{field}', n, stacks, 1000, ['widemix1'] + rest)
    return js


def main():
    m = models()
    base = {'format': 'nplayer-feature-manifest-v1', 'tables': TABLES, 'models': m, 'teachers': TEACHERS}
    # One process loads the teachers once: the same job at 16 and 8 threads first, then the measurement.
    out = W / 'measure'
    out.mkdir(parents=True, exist_ok=True)
    det = {'players': 6, 'stacks': 'wide-depth-grid-v1', 'hands': 2000, 'root': ROOT - 1000,
           'seats': ['widemix1', 'bot=check-call', 'bot=pot-pressure', 'widemix1', 'bot=tight-aggressive', 'bot=random']}
    checks = [det | {'name': f'determinism-t{t}', 'threads': t, 'out': str(out / f'determinism-t{t}.npfeat')} for t in (16, 8)]
    (out / 'manifest.json').write_text(json.dumps(base | {'threads': 16, 'jobs': checks + jobs(out)}, indent=1))


if __name__ == '__main__':
    main()
