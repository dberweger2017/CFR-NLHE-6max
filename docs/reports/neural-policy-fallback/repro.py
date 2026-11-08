"""Qualification 3 for docs/neural-policy-fallback.md: with uniform fallback in both arms, the new
host must reproduce two of #461's run 1 cases byte for byte. Writes a manifest of those cases
with fresh output paths; `check` compares the new traces' hashes with #461's recorded ones."""
import hashlib
import json
import sys
from pathlib import Path

SOURCE = Path('/home/dberweger/openpoker-wide-capacity-20261107/main/run1/out/arena-manifest-b0.json')
CASES = ('b0-3p-5bb-mixed', 'b0-6p-5bb-mixed')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 24), b''):
            h.update(block)
    return h.hexdigest()


def manifest(out):
    m = json.loads(SOURCE.read_text())
    cases = []
    for c in m['cases']:
        if c['name'] in CASES:
            cost = json.loads(Path(c['summary']).read_text())
            c = c | {'traces': [str(out / f"{c['name']}-a{arm}.jsonl") for arm in (0, 1)], 'summary': str(out / f"{c['name']}-cost.json"),
                     'focal_untrained_fallback': ['uniform', 'uniform'], 'expected_trace_sha256': cost['trace_sha256']}
            cases.append(c)
    assert [c['name'] for c in cases] == list(CASES)
    expected = {c['name']: c.pop('expected_trace_sha256') for c in cases}
    (out / 'expected.json').write_text(json.dumps(expected, indent=1))
    (out / 'manifest.json').write_text(json.dumps(m | {'cases': cases}, indent=1))


def check(out):
    expected = json.loads((out / 'expected.json').read_text())
    result = {name: [sha(out / f'{name}-a{arm}.jsonl') == want[arm] for arm in (0, 1)] for name, want in expected.items()}
    (out / 'receipt.json').write_text(json.dumps({'matches': result, 'passed': all(all(v) for v in result.values())}, indent=1))
    if not all(all(v) for v in result.values()):
        raise SystemExit(f'reproduction failed: {result}')
    print(json.dumps(result))


if __name__ == '__main__':
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    {'manifest': manifest, 'check': check}[sys.argv[1]](out)
