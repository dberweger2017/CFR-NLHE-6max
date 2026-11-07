"""The export manifest for docs/neural-policy-imitation.md: train, test-wide and test-short."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'neural-policy-data'))
import make_manifest as step1  # noqa: E402  (step 1's pinned models, fields and short tables)
import json  # noqa: E402

W = Path(sys.argv[1])
SCRIPTS = ['pot-pressure', 'tight-aggressive', 'check-call', 'random']
ROOTS = {'train': 20261108400000, 'test-wide': 20261108500000, 'test-short': 20261108600000}


def wide_jobs(split, base_hands):
    jobs = []
    for n in (3, 4, 5, 6):
        fields = {'self': ['widemix1'] * n, 'mixed': ['widemix1'] + step1.MIXED[n]}
        fields |= {s: ['widemix1'] + [f'bot={s}'] * (n - 1) for s in SCRIPTS}
        for field, seats in fields.items():
            jobs.append({'name': f'wide-{n}p-{field}', 'players': n, 'stacks': 'wide-depth-grid-v1',
                         'hands': base_hands * (2 if n == 6 else 1), 'seats': seats})
    return jobs


def short_jobs():
    jobs = []
    for name, stacks in step1.SHORT.items():
        n = len(stacks)
        fields = {'mixed': step1.MIXED[n]} | {s: [f'bot={s}'] * (n - 1) for s in SCRIPTS}
        if n == 6:
            fields['copies'] = ['widemix1'] * 5
        for field, rest in fields.items():
            jobs.append({'name': f'{name}-{field}', 'players': n, 'stacks': stacks, 'hands': 3000, 'seats': ['widemix1'] + rest})
    return jobs


def main():
    out = W / 'data'
    jobs = []
    for split, js in (('train', wide_jobs('train', 80000)), ('test-wide', wide_jobs('test-wide', 4000)), ('test-short', short_jobs())):
        (out / split).mkdir(parents=True, exist_ok=True)
        for i, j in enumerate(js):
            jobs.append(j | {'root': ROOTS[split] + 1000 * i, 'out': str(out / split / f"{j['name']}.npfeat")})
    manifest = {'format': 'nplayer-feature-manifest-v1', 'tables': step1.TABLES, 'models': step1.models(),
                'teachers': step1.TEACHERS, 'threads': 16, 'jobs': jobs}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=1))
    print(json.dumps({s: sum(j['hands'] for j in jobs if f'/{s}/' in j['out']) for s in ROOTS}))


if __name__ == '__main__':
    main()
