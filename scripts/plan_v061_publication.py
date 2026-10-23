"""Plan missing v0.6.1 GitHub assets from a live metadata snapshot; never upload.

Obtain the snapshot with `gh release view v0.6.1 --json assets`. No payload is
read here. Missing digests and conflicting names stop the plan; they never
trigger deletion, replacement, or a second blind upload.
"""
import argparse
import json
from pathlib import Path

from src.policies import v061_bundle as v


def inventory(bundles, source, *, allow_prepared=False):
    assets = {}
    for seed in v.MODELS:
        directory = Path(bundles) / seed
        manifest = v.read_manifest(directory, seed, source, require_publication=not allow_prepared)
        rows = {row['file']: row for row in manifest['parts']}
        rows.update(manifest['source_assets'])
        for name in v.names(seed):
            path = v.regular(directory / name)
            rows[name] = dict(bytes=path.stat().st_size, sha256=v.sha(path))
        for name, pin in rows.items():
            path = v.regular(directory / name)
            if path.stat().st_size != pin['bytes']:
                raise ValueError('asset length differs: ' + name)
            pin = dict(bytes=pin['bytes'], sha256=pin['sha256'])
            if name in assets and {k: assets[name][k] for k in pin} != pin:
                raise ValueError('common assets differ across seeds: ' + name)
            assets[name] = dict(pin, path=str(path))
    return assets


def plan(expected, observed):
    live = {}
    for asset in observed:
        name = asset['name']
        if name in live:
            raise ValueError('duplicate live asset name: ' + name)
        live[name] = asset
    result = []
    for name, pin in sorted(expected.items()):
        asset = live.get(name)
        if asset is None:
            result.append(dict(name=name, action='upload-after-owner-approval', **pin))
        elif (asset.get('size') == pin['bytes']
              and asset.get('digest') == 'sha256:' + pin['sha256']):
            result.append(dict(name=name, action='reuse', asset_id=asset['id'], **pin))
        else:
            raise ValueError('live asset size/digest conflicts or is unavailable: ' + name)
    extras = sorted(set(live) - set(expected))
    if extras:
        raise ValueError('unexpected live assets require review: ' + ', '.join(extras))
    return dict(status='planned-only', assets=result,
                payload_readback=False, publication_authorized=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundles', type=Path, required=True, help='Parent of three seed directories')
    parser.add_argument('--expect-source', required=True)
    parser.add_argument('--live-assets', type=Path, required=True, help='gh release view JSON; assets=[] before creation')
    parser.add_argument('--allow-prepared', action='store_true')
    args = parser.parse_args()
    live = json.loads(args.live_assets.read_text())
    print(json.dumps(plan(inventory(args.bundles, args.expect_source, allow_prepared=args.allow_prepared),
                          live['assets']), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
