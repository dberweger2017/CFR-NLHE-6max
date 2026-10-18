"""Prepare pinned sources, adapting the save API for the two historical arms."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

BASE = '3f9bfbdcb54b17ca530419b0e84e663fcf0d8b47'
COMPACT = '7bcbce9dcb2d65a3a6ac8e7721e83fb9a36f677e'
PARALLEL = '16dbe015436cfea8f582803b0befaca3a2b4ad38'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root)
    archive = git('archive', BASE, 'native')
    patches = {'pr331.patch':git('diff', '9b2a481a', COMPACT, '--', 'native'),
               'pr333.patch':git('diff', COMPACT, PARALLEL, '--', 'native')}
    for name, value in patches.items():
        (args.out/name).write_bytes(value)
    receipts = []
    for arm in ('baseline', 'compact', 'parallel'):
        dest = args.out/arm; dest.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
            stream.extractall(dest, filter='data')
        applied = [] if arm == 'baseline' else ['pr331.patch']
        if arm == 'parallel': applied += ['pr333.patch']
        for name in applied:
            subprocess.run(['patch', '--batch', '-p1', '-i', str((args.out/name).resolve())],
                           cwd=dest, check=True, stdout=subprocess.DEVNULL)
        common = root/'native/hu20-trainer/examples/nplayer_storage_bench.rs'
        target = dest/'native/hu20-trainer/examples/nplayer_storage_bench.rs'
        shutil.copy2(common, target)
        adapter = None
        if arm != 'parallel':
            text = target.read_text()
            before = 'multi_checkpoint::save(&trainer, &checkpoint, hu20_trainer::gz::Gzip::Compatible)?;'
            after = 'multi_checkpoint::save(&trainer, &checkpoint)?;'
            if text.count(before) != 1:
                raise ValueError('unexpected common harness save call')
            target.write_text(text.replace(before, after))
            adapter = dict(before=before, after=after,
                           reason='Before PR333 the save API uses default-compatible gzip implicitly')
        receipts.append(dict(arm=arm, baseline_commit=BASE, patches=applied,
            common_harness_sha256=hashlib.sha256(common.read_bytes()).hexdigest(),
            api_adapter=adapter, files={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(dest.rglob('*')) if p.is_file()}))
    (args.out/'source-manifest.json').write_text(json.dumps(receipts, indent=2)+'\n')


if __name__ == '__main__':
    main()
