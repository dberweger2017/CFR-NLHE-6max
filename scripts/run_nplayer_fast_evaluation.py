"""Execute the frozen fast-mode matrix; withhold scores until global verification."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from scripts.analyze_nplayer_arena import sha
from scripts.check_nplayer_policy_replay import check


def case_run(task):
    case, manifest, root = task
    root=Path(root);out=root/'evaluation'/case['name'];out.mkdir(parents=True,exist_ok=False)
    models=manifest['models']
    def spec(name):
        m=models[name]
        if m['strategy']!='average' or m['scope']!=3:raise ValueError('full average required')
        return 'policy='+m['path']+'@'+m['sha256']
    command=[manifest['arena'],manifest['tables'],str(case['blocks']),str(case['root'])]
    operations=[]
    for repeat in range(2):
        trace=out/f'play-{repeat}.jsonl';tick=time.monotonic()
        with (out/f'play-{repeat}.log').open('x') as log:
            completed=subprocess.run(command+[str(trace),spec(case['singleton']),spec(case['pair'])],stdout=log,stderr=subprocess.STDOUT)
        operations.append(dict(repeat=repeat,seconds=time.monotonic()-tick,returncode=completed.returncode))
        if completed.returncode:raise RuntimeError(case['name']+' native play failed')
        operations[-1]['coverage']=json.loads((out/f'play-{repeat}.log').read_text())
    a,b=out/'play-0.jsonl',out/'play-1.jsonl'
    digest=sha(a)
    if digest!=sha(b):raise ValueError('reproduction mismatch: '+case['name'])
    tick=time.monotonic();replay=check(a)
    if replay['hands']!=6*case['blocks'] or replay['trace_sha256']!=digest:raise ValueError('replay identity mismatch')
    (out/'replay.json').write_text(json.dumps(replay,indent=2)+'\n')
    result=dict(status='passed',case=case,trace_sha256=digest,hands=replay['hands'],operations=operations,replay_seconds=time.monotonic()-tick)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def run(manifest_path,root):
    m=json.loads(manifest_path.read_text())
    from scripts.run_nplayer_fast_study import cases
    if m['format']=='nplayer-fast-strength-evaluation-v1':
        if m['cases']!=cases():raise ValueError('changed final matrix')
    elif m['format']!='nplayer-fast-strength-qualification-v1':
        raise ValueError('unknown matrix purpose')
    expected_hands=sum(6*c['blocks'] for c in m['cases'])
    if sha(Path(m['arena']))!=m['arena_sha256']:raise ValueError('arena binary mismatch')
    for model in m['models'].values():
        if sha(Path(model['path']))!=model['sha256']:raise ValueError('model input mismatch')
    (root/'evaluation').mkdir(exist_ok=False)
    pool=ProcessPoolExecutor(max_workers=8)
    try:
        pending=[pool.submit(case_run,(c,m,str(root))) for c in m['cases']]
        results=[]
        for future in as_completed(pending):
            results.append(future.result())
            progress=dict(event='progress',completed=len(results),total=len(m['cases']))
            (root/'evaluation-progress.json').write_text(json.dumps(progress)+'\n')
            print(json.dumps(progress),flush=True)
        pool.shutdown()
        if len(results)!=len(m['cases']) or sum(r['hands'] for r in results)!=expected_hands:raise ValueError('incomplete matrix')
        result=dict(status='passed',contrasts=len(results),final_hands=expected_hands,manifest_sha256=sha(manifest_path))
        (root/'evaluation-verified.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(dict(event='complete',**result)),flush=True)
    except BaseException as error:
        (root/'evaluation-failure.json').write_text(json.dumps(dict(error=repr(error),at=time.time()))+'\n')
        # This batch is the supervisor's fresh process group; terminate only its workers.
        os.killpg(os.getpgrp(),signal.SIGTERM)
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest',type=Path);p.add_argument('root',type=Path);a=p.parse_args();run(a.manifest,a.root)
