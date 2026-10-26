"""Guarded, fixture-only M4 qualification. Never loads the mature PR431 model."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from scripts.nplayer_four_player_feasibility import Supervisor, TABLES, sample, sha, write

SOURCE = Path(__file__).resolve().parents[1]


def qualify(root, tables, thermal):
    if platform.system() != 'Darwin' or 'Apple M4' not in subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True):
        raise ValueError('M4 only')
    if 'AC Power' not in subprocess.check_output(['pmset','-g','batt'],text=True):
        raise ValueError('AC required')
    root=Path(root);root.mkdir(exist_ok=False,parents=True)
    locks=[]
    try:
        for name in (Path.home()/'Local/.hu20-m4-research.lock',root.parent/'.six-player-counterfactual.lock'):
            f=name.open('a+');locks.append(f)
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for name,pin in TABLES.items():
            if sha(Path(tables)/name)!=pin:
                raise ValueError('K50 changed')
        before=sample(root,thermal)
        write(root/'admission.json',dict(sample=before,fixture_only=True,
              forecast_family_rss_bytes=4*2**30,ram_headroom_bytes=2**30,
              forecast_new_disk_bytes=3*2**30,disk_headroom_bytes=4*2**30))
        if before['available_ram_bytes'] < 5*2**30 or before['disk_free_bytes'] < 7*2**30:
            raise ValueError('fixture forecast + headroom not available')
        env=dict(os.environ,CARGO_BUILD_JOBS='2',RAYON_NUM_THREADS='2')
        sup=Supervisor(root,env,thermal)
        manifest=SOURCE/'native/hu20-trainer/Cargo.toml'
        sup.stage('library-tests',['cargo','test','--locked','--manifest-path',manifest,'--lib'])
        sup.stage('example-tests',['cargo','test','--locked','--manifest-path',manifest,'--example','six_player_counterfactual'])
        sup.stage('python-tests',[sys.executable,'-m','unittest','tests.test_six_player_counterfactual_m4','-v'])
        sup.stage('build',['cargo','build','--locked','--release','--manifest-path',manifest,'--example','six_player_counterfactual'])
        binary=SOURCE/'native/hu20-trainer/target/release/examples/six_player_counterfactual'
        sup.stage('fixture-prepare',[binary,'fixture',tables,root/'fixture'])
        m=root/'fixture/manifest.json'
        sup.stage('fixture-run',[binary,m])
        receipt=json.loads((root/'fixture/run-v1/verified.json').read_text())
        if receipt['status']!='passed' or receipt['roots']!=24 or not receipt['qualification_only'] or not receipt['float64_and_work_reproduced']:
            raise ValueError('incomplete fixture proof')
        write(root/'COMPLETE.json',dict(status='passed',fixture_only=True,mature_model_loaded=False,
              main_started=False,roots=24,worlds_per_root=8,reproductions=1,
              binary_sha256=sha(binary),fixture_receipt_sha256=sha(root/'fixture/run-v1/verified.json'),
              stages=sup.costs,after=sample(root,thermal)))
        write(root/'status.json',dict(status='complete',fixture_only=True,main_started=False))
    except BaseException as e:
        write(root/'failure.json',dict(status='failed',error=repr(e),no_retry=True))
        raise
    finally:
        for f in reversed(locks):f.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('root',type=Path);p.add_argument('--tables',type=Path,required=True)
    p.add_argument('--thermal',type=Path,required=True)
    a=p.parse_args();qualify(a.root,a.tables,a.thermal)

if __name__=='__main__': main()
