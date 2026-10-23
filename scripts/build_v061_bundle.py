"""Split an audited v0.6.1 binary once, or rebind existing parts to reviewed source.

This prepares local assets only. It never converts models, stages research,
uploads assets, creates tags, or publishes releases. Independent reconstruction
is a separate verification stage, rather than a hidden second payload pass.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

from src.policies import v061_bundle as v

SOURCE = Path(__file__).resolve().parents[1]


def checked_source(source):
    if not v.digest(source, 40) or subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip() != source:
        raise ValueError('full checked-out source commit required')
    subprocess.run(['git', 'diff', '--exit-code', source, '--'], cwd=SOURCE,
                   check=True, stdout=subprocess.DEVNULL)
    return SOURCE


def stamp(stat):
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def split(seed, model, out):
    pin = v.MODELS[seed]
    model = v.regular(model)
    parts, whole = [], hashlib.sha256()
    with model.open('rb') as source:
        before = stamp(os.fstat(source.fileno()))
        if before[2] != pin['bytes']:
            raise ValueError('qualified model length differs')
        prefix = source.read(128)
        if len(prefix) != 128:
            raise ValueError('short binary prefix')
        length = struct.unpack_from('<Q', prefix, 8)[0]
        if not 0 < length <= 65536:
            raise ValueError('binary header bound')
        v.check_header(prefix, source.read(length), seed)
        source.seek(0)
        for row in v.layout(seed):
            local, remaining = hashlib.sha256(), row['bytes']
            with (out / row['file']).open('xb') as target:
                while remaining:
                    chunk = source.read(min(4 * 1024**2, remaining))
                    if not chunk:
                        raise ValueError('source ended inside part')
                    target.write(chunk)
                    local.update(chunk)
                    whole.update(chunk)
                    remaining -= len(chunk)
                target.flush()
                os.fsync(target.fileno())
            parts.append(dict(row, sha256=local.hexdigest()))
        if (source.read(1) or whole.hexdigest() != pin['sha256']
                or stamp(os.fstat(source.fileno())) != before or stamp(model.stat()) != before):
            raise ValueError('qualified source changed or SHA256 differs')
    return parts


def build(seed, model, tables, out, source, *, publication_approved=False,
          reuse_bundle=None, reuse_source=None):
    repo = checked_source(source)
    if (model is None) == (reuse_bundle is None):
        raise ValueError('choose model or reuse_bundle')
    if reuse_bundle is not None and reuse_source is None:
        raise ValueError('reuse requires the prior source commit')
    # Tables stay at their existing location. Clients can reuse a verified K50
    # directory; publishing identical dependency bytes again adds no integrity.
    for name, pin in v.CARD_TABLES.items():
        path = v.regular(Path(tables) / name)
        if path.stat().st_size != pin['bytes'] or v.sha(path) != pin['sha256']:
            raise ValueError('wrong K50 table: ' + name)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    if reuse_bundle is None:
        parts = split(seed, model, out)
    else:
        prior = v.read_manifest(reuse_bundle, seed, reuse_source)
        parts = prior['parts']
        for row in parts:
            path = v.regular(Path(reuse_bundle) / row['file'])
            if path.stat().st_size != row['bytes']:
                raise ValueError('reused part length differs')
            os.link(path, out / row['file'])
    for name in v.DOCS:
        shutil.copyfile(repo / 'docs/releases/v0.6.1' / name, out / name)
    shutil.copyfile(repo / 'src/policies/v061_bundle.py', out / v.VERIFIER)
    assets = {name: dict(bytes=(out / name).stat().st_size, sha256=v.sha(out / name))
              for name in v.DOCS + (v.VERIFIER,)}
    manifest = dict(format='nplayer-v061-release-v1', version=v.VERSION, seed=seed,
                    source_commit=source, publication_approved=publication_approved,
                    evidence=v.EVIDENCE, model=v.MODELS[seed], parts=parts,
                    card_tables=v.CARD_TABLES, dependencies=v.DEPENDENCIES,
                    table=dict(players=3, stack_bb=200, small_blind=50, big_blind=100, search=False),
                    source_assets=assets)
    name, sums = v.names(seed)
    (out / name).write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    checks = {row['file']: row['sha256'] for row in parts}
    checks.update({n: p['sha256'] for n, p in {**v.CARD_TABLES, **assets}.items()})
    checks[name] = v.sha(out / name)
    (out / sums).write_text(''.join(f'{pin}  {n}\n' for n, pin in sorted(checks.items())))
    v.read_manifest(out, seed, source)
    return dict(status='prepared', seed=seed, manifest_sha256=v.sha(out / name),
                source_model_verified=reuse_bundle is None, reused_parts=reuse_bundle is not None,
                independent_part_readback=False,
                next_stage='Standalone --assemble, then check_v061_runtime; no conversion')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', choices=v.MODELS, required=True)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--model', type=Path)
    inputs.add_argument('--reuse-bundle', type=Path)
    parser.add_argument('--reuse-source')
    parser.add_argument('--card-tables', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--publication-approved', action='store_true')
    args = parser.parse_args()
    print(json.dumps(build(args.seed, args.model, args.card_tables, args.out, args.source_sha,
                           publication_approved=args.publication_approved,
                           reuse_bundle=args.reuse_bundle, reuse_source=args.reuse_source)))


if __name__ == '__main__':
    main()
