"""Negative CLI tests and exact old-format/play compatibility for PR344 fixtures."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess

from scripts.run_nplayer_key_benchmark import SCHEMAS, SEED, load
from scripts.run_nplayer_storage_benchmark import sha, write


def qualify(root):
    config = load(root / 'config.json')
    binaries = root / 'target/release/examples'
    trainer, policy, arena = (str(binaries / name) for name in ('nplayer_train', 'nplayer_policy', 'nplayer_arena'))
    base = [trainer, '--players', '3', '--stack-bb', '20', '--card-buckets', config['tables'],
        '--nodes', '3000000', '--max-entries', '150000000', '--max-seconds', '600',
        '--last-average-street', '3', '--seed', str(SEED), '--fast', '--threads', '16']
    receipts = []

    def command(args, filename, success=True, contains=None):
        with (root / filename).open('x') as log:
            result = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT)
        if (result.returncode == 0) != success:
            raise ValueError('unexpected qualification command status: ' + filename)
        if contains is not None and contains not in (root / filename).read_text():
            raise ValueError('wrong rejection reason: ' + filename)
        receipts.append(dict(command=args, returncode=result.returncode, log=filename))

    for schema in SCHEMAS:
        fixture = root / ('fixture-' + schema + '-16') / '3000000.gz'
        output = root / ('cli-' + schema + '.gz')
        command(base + ['--key-schema', schema, '--out', str(output)], 'cli-' + schema + '.log')
        if sha(output) != sha(fixture):
            raise ValueError('CLI and benchmark differ: ' + schema)
        for other in SCHEMAS:
            if other != schema:
                bad = root / f'refused-{schema}-to-{other}.gz'
                resumed_base = base.copy()
                resumed_base[resumed_base.index('--nodes') + 1] = '4000000'
                command(resumed_base + ['--key-schema', other, '--resume', str(fixture),
                    '--resume-sha256', sha(fixture), '--out', str(bad)],
                    f'refused-{schema}-to-{other}.log', False, 'resume configuration mismatch')
                if bad.exists():
                    raise ValueError('refused schema wrote a checkpoint')
    # The rejected command must contain a single target option, not fail at duplicate parsing.
    if any('duplicate' in (root / r['log']).read_text() for r in receipts if 'refused-' in r['log']):
        raise ValueError('negative test rejected argument syntax instead of schema mismatch')

    legacy_policy = config['legacy_policy']
    legacy_arena = config['legacy_arena']
    for key in ('legacy_policy', 'legacy_arena'):
        if sha(config[key]) != config[key + '_sha256']:
            raise ValueError('legacy binary pin changed')
    fixture = root / 'legacy-fixture.gz'
    exported = root / 'legacy-export.gz'
    command([legacy_policy, 'export', str(fixture), sha(fixture), 'average', str(exported)], 'legacy-export.log')
    if sha(exported) != sha(root / 'fixture-v1-average.gz'):
        raise ValueError('legacy inference export bytes changed')
    spec = 'policy=' + str(exported) + '@' + sha(exported)
    trace = root / 'legacy-play.jsonl'
    command([legacy_arena, config['tables'], '16', '202610183270101', str(trace), spec, spec], 'legacy-play.log')
    if sha(trace) != sha(root / 'smoke-v1.jsonl'):
        raise ValueError('legacy v1 play bytes changed')

    for tag, change in [('unknown-schema', lambda h: h['identity'].__setitem__('schema', 'unknown-v99')),
                        ('wrong-stacks', lambda h: h['identity'].__setitem__('stacks', [2000, 3000, 2000]))]:
        corrupted = root / (tag + '.gz')
        with gzip.open(root / 'fixture-v1-average.gz', 'rt') as src, gzip.open(corrupted, 'wt') as dst:
            header = json.loads(next(src));change(header)
            dst.write(json.dumps(header) + '\n')
            for row in src:
                dst.write(row)
        bad_spec = 'policy=' + str(corrupted) + '@' + sha(corrupted)
        command([arena, config['tables'], '2', '202610183270102', str(root / (tag + '.jsonl')),
            bad_spec, spec], tag + '.log', False)
    result = dict(status='passed', checks=len(receipts), commands=receipts)
    write(root / 'cli-qualification.json', result)
    print(json.dumps(dict(event='complete', status='passed', checks=len(receipts))))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    qualify(p.parse_args().root)
