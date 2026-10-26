"""Resume hash-pinned public v0.6.1 downloads; never upload or publish.

Use the reviewed checkout and the manifest SHA256 from the release verification
record. Completed assets are verified and reused. Failed partials stay in place.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.request

from src.policies import v061_bundle as v

BASE = 'https://github.com/dberweger2017/CFR-NLHE-6max/releases/download/v0.6.1/'


def promote(partial, path):
    os.link(partial, path)
    partial.unlink()


def fetch(url, path, pin):
    """Bounded HTTP Range resume, verifying both the retained prefix and suffix."""
    path = Path(path)
    if path.exists() or path.is_symlink():
        v.regular(path)
        if path.stat().st_size != pin['bytes'] or v.sha(path) != pin['sha256']:
            raise ValueError('existing download differs; preserved: ' + str(path))
        return 'reused'
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + '.partial')
    local = hashlib.sha256()
    offset = 0
    if partial.exists() or partial.is_symlink():
        v.regular(partial)
        with partial.open('rb') as prefix:
            for chunk in iter(lambda: prefix.read(4 * 1024**2), b''):
                local.update(chunk)
                offset += len(chunk)
    if offset > pin['bytes']:
        raise ValueError('oversized partial preserved')
    if offset < pin['bytes']:
        headers = {'User-Agent': 'CFR-v061-download'}
        if offset:
            headers['Range'] = f'bytes={offset}-'
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as response:
            expected = 206 if offset else 200
            if response.status != expected:
                raise ValueError('server did not honor resume; partial preserved')
            if offset and response.headers.get('Content-Range') != f"bytes {offset}-{pin['bytes']-1}/{pin['bytes']}":
                raise ValueError('wrong resume range; partial preserved')
            with partial.open('ab' if partial.exists() else 'xb') as output:
                for chunk in iter(lambda: response.read(4 * 1024**2), b''):
                    offset += len(chunk)
                    if offset > pin['bytes']:
                        raise ValueError('download exceeds pinned size; partial preserved')
                    local.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
    if offset != pin['bytes'] or local.hexdigest() != pin['sha256']:
        raise ValueError('download bytes/SHA256 differ; partial preserved')
    promote(partial, path)
    return 'downloaded'


def fetch_manifest(path, expected_sha):
    if not v.digest(expected_sha):
        raise ValueError('manifest SHA256 required from reviewed publication record')
    if path.exists() or path.is_symlink():
        v.regular(path)
        if path.stat().st_size > 262144 or v.sha(path) != expected_sha:
            raise ValueError('existing manifest differs; preserved')
        return
    with urllib.request.urlopen(BASE + path.name, timeout=60) as response:
        data = response.read(262145)
    if len(data) > 262144 or hashlib.sha256(data).hexdigest() != expected_sha:
        raise ValueError('manifest bound/SHA256 differs')
    partial = path.with_name(path.name + '.partial')
    with partial.open('xb') as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    promote(partial, path)


def download(directory, seed, source, manifest_sha, *, tables=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    manifest_name, sums_name = v.names(seed)
    fetch_manifest(directory / manifest_name, manifest_sha)
    manifest = v.read_manifest(directory, seed, source, require_publication=True)
    statuses = {}
    for name, pin in manifest['source_assets'].items():
        statuses[name] = fetch(BASE + name, directory / name, pin)
    table_dir = Path(tables) if tables is not None else directory
    for name, pin in v.DEPENDENCIES.items():
        statuses[name] = fetch(pin['url'], table_dir / name, pin)
    # SHA256SUMS is deterministic from the pinned manifest; no extra request or
    # trust in a second remotely supplied checksum list is needed.
    checks = {row['file']: row['sha256'] for row in manifest['parts']}
    checks.update({n: p['sha256'] for n, p in {**v.CARD_TABLES, **manifest['source_assets']}.items()})
    checks[manifest_name] = manifest_sha
    sums = ''.join(f'{pin}  {name}\n' for name, pin in sorted(checks.items()))
    path = directory / sums_name
    if path.exists() or path.is_symlink():
        if v.regular(path).read_text() != sums:
            raise ValueError('existing checksum list differs; preserved')
    else:
        with path.open('x') as output:
            output.write(sums)
    for part in manifest['parts']:
        statuses[part['file']] = fetch(BASE + part['file'], directory / part['file'], part)
    return dict(status='downloaded-and-hash-verified', seed=seed, assets=statuses,
                next_stage='Run verifier --assemble once, then play_v061; reconstruction still required')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', choices=v.MODELS, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--card-tables', type=Path)
    parser.add_argument('--expect-source', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(download(args.out, args.seed, args.expect_source, args.manifest_sha256,
                              tables=args.card_tables)))


if __name__ == '__main__':
    main()
