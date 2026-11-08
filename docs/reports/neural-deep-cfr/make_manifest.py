"""The warm-start export manifest for docs/neural-deep-cfr.md: step 2's training recipe, at half its
hands, with `widemix` run 1 as the only teacher and its training checkpoint's regrets."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'neural-policy-data'))
import make_manifest as step1  # noqa: E402  (step 1's pinned models and fields)

W, CHECKPOINT, CHECKPOINT_SHA, LIVE = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
SCRIPTS = ['pot-pressure', 'tight-aggressive', 'check-call', 'random']
ROOT = 20261109300000
BASE_HANDS = 40000


def main():
    out = W / 'warm'
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for n in (3, 4, 5, 6):
        fields = {'self': ['widemix1'] * n, 'mixed': ['widemix1'] + step1.MIXED[n]}
        fields |= {s: ['widemix1'] + [f'bot={s}'] * (n - 1) for s in SCRIPTS}
        for field, seats in fields.items():
            name = f'wide-{n}p-{field}'
            jobs.append({'name': name, 'players': n, 'stacks': 'wide-depth-grid-v1', 'hands': BASE_HANDS * (2 if n == 6 else 1),
                         'seats': seats, 'root': ROOT + 1000 * len(jobs), 'out': str(out / f'{name}.npfeat')})
    pins = json.loads((LIVE / 'pins.json').read_text())
    if pins['checkpoint'] != CHECKPOINT_SHA:
        raise ValueError('checkpoint is not widemix run 1\'s')
    models = {'widemix1': {'path': str(LIVE / 'model.bin'), 'sha256': pins['binary'], 'mass': str(LIVE / 'mass'),
                           'mass_sha256': pins['mass_receipt']}}
    manifest = {'format': 'nplayer-feature-manifest-v1', 'tables': step1.TABLES, 'models': models, 'teachers': ['widemix1'],
                'regrets': {'teacher': 'widemix1', 'checkpoint': CHECKPOINT, 'sha256': CHECKPOINT_SHA}, 'threads': 16, 'jobs': jobs}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=1))
    print(json.dumps({'jobs': len(jobs), 'hands': sum(j['hands'] for j in jobs)}))


if __name__ == '__main__':
    main()
