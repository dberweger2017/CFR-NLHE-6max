"""Export and independently audit a fixed list of models before final play."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import signal
import subprocess

from scripts.audit_nplayer_policy import audit, sha


def export_one(task):
    policy,m=task
    cp=Path(m['checkpoint'])
    if sha(cp)!=m['checkpoint_sha256']:raise ValueError('checkpoint mismatch')
    env=dict(os.environ,RAYON_NUM_THREADS='4')
    with Path(m['export']+'.log').open('x') as log:
        subprocess.run([policy,'export',str(cp),m['checkpoint_sha256'],'average',m['export']],stdout=log,stderr=subprocess.STDOUT,env=env,check=True)
    return m


def audit_one(m):
    result=audit(Path(m['checkpoint']),Path(m['export']))
    Path(m['export']+'.audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return dict(id=m['id'],path=m['export'],sha256=result['policy_sha256'],strategy='average',scope=3,
        checkpoint=m['checkpoint'],checkpoint_sha256=m['checkpoint_sha256'],rows=result['rows'])


def run(root):
    config=json.loads((root/'export-plan.json').read_text())
    try:
        with ProcessPoolExecutor(max_workers=3) as pool:
            exported=list(pool.map(export_one,[(config['policy'],m) for m in config['models']]))
        print(json.dumps(dict(event='progress',phase='exports-complete',models=len(exported))),flush=True)
        with ProcessPoolExecutor(max_workers=8) as pool:models=list(pool.map(audit_one,exported))
        result=dict(status='passed',models={m['id']:m for m in models})
        (root/'models-audited.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(dict(event='complete',models=len(models))),flush=True)
    except BaseException as error:
        (root/'model-preparation-failure.json').write_text(json.dumps(dict(error=repr(error)))+'\n')
        os.killpg(os.getpgrp(),signal.SIGTERM)
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);run(p.parse_args().root)
