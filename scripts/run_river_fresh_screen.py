"""Owned PR396 qualification, fixed fresh screen and globally verified readout."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

from scripts.river_whole_hand_pilot import read, write, sha
from scripts.river_fresh_screen import BINARY_SHA, ROOTS
from scripts.run_river_continuation_qualification import thermal, resources, stop


def run(args):
    args.out.mkdir(parents=True,exist_ok=False)
    root=args.root.resolve();source=root/'source';python=root/'venv/bin/python';binary=root/'bin/nplayer_river_arena'
    config=read(root/'control.json');config_sha=sha(root/'control.json');locks=[]
    for name in ('/tmp/cfr-cygnus-exclusive.lock','/tmp/cfr-pr396-fresh-screen.lock'):
        f=open(name,'a+');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    if actual!=args.source or subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True).strip():
        raise RuntimeError('frozen clean source required')
    if config['planning_allowance_seconds']!=7200 or config['fresh_roots']!=list(ROOTS) or sha(binary)!=BINARY_SHA:
        raise RuntimeError('accepted scope/binary differs')
    prior=Path(config['qualified_root']);q=prior/'qualification-v1'
    if read(q/'status.json')['status']!='complete' or (q/'failure.json').exists() or any(x['returncode'] for x in read(q/'stage-costs.json')):
        raise RuntimeError('existing optimized native qualification required')
    paths=subprocess.check_output(['git','ls-files','native/hu20-trainer'],cwd=source,text=True).splitlines()
    native={p:sha(source/p) for p in paths if (source/p).is_file()}
    if native!={p:sha(prior/'source'/p) for p in native} or read(q/'binary-pin.json')['sha256']!=BINARY_SHA:
        raise RuntimeError('player/native code must remain exactly qualified')
    write(args.out/'native-identity.json',{'status':'passed','files':native,'qualified_binary_sha256':BINARY_SHA,'prior':str(q)})
    names=subprocess.check_output(['git','ls-files'],cwd=source,text=True).splitlines()
    pins={p:sha(source/p) for p in names if (source/p).is_file()};write(args.out/'source-manifest.json',pins)
    write(args.out/'launch.json',{'pid':os.getpid(),'source':actual,'config_sha256':config_sha,
        'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'cpu_stop_c':90,'thermistor15_stop_c':100,
        'planning_allowance_seconds':7200,'no_other_resource_stops':True,'fresh_roots':list(ROOTS),
        'blocks_per_lineup':1024,'initial_hands':24576,'reproduction_hands':24576,'no_followup_authorized':True})
    common=[str(python),'-m','scripts.river_fresh_screen']
    play_args=['--binary',str(binary)]
    for key in ('focal','peer','k50','pilot','reference'):play_args+=['--'+key,config[key]]
    stages=[('python-tests',[str(python),'-m','unittest','tests.test_river_fresh_screen','tests.test_river_arena_expectation',
                           'tests.test_river_conditional_evaluation','tests.test_river_whole_hand_pilot','-v']),
            ('environment',[str(python),'-c','import scipy.stats,numpy,pokers; print("Pinned evaluator environment imports passed")']),
            ('qualification',common+['qualify','--out',str(args.out/'qualification')]+play_args),
            ('screen',common+['measure','--out',str(args.out/'screen')]+play_args),
            ('readout',common+['readout','--input',str(args.out/'screen'),'--out',str(args.out/'readout')])]
    env={**os.environ,'PYTHONPATH':str(source),'RAYON_NUM_THREADS':'1'};costs=[]
    for phase,command in stages:
        # No outcomes are read by the controller; main runs only after all prior stages passed.
        if phase=='screen':
            fixture=read(args.out/'qualification/costs.json')
            previous=read(source/'docs/reports/river-arena-expectation/measurement-results.json')
            known_play=2*1024/128*max(sum(previous['work'][label]['cases'][name+'-'+arm]['play_and_write_seconds']
                for name in ('trained','call-pressure') for arm in ('on','off')) for label in ('initial','repeat'))
            fixture_play=sum(b['play_and_write_seconds'] for b in fixture['batches'].values())*256
            projected_play=max(known_play,fixture_play)
            loads=sum(b['startup']['model_and_k50_load_seconds'] for b in fixture['batches'].values())
            spent=sum(s['wall_seconds'] for s in costs)
            central=spent+loads+projected_play+600
            reserve=spent+2*loads+3*projected_play+1200
            write(args.out/'main-admission.json',{'status':'admitted' if reserve<=7200 else 'quote-exceeds-allowance',
                'central_seconds':central,'reserved_seconds':reserve,'accepted_planning_allowance_seconds':7200,
                'cost_only_no_outcomes':True,'main_started':False,
                'assumptions':'Max(old full panel rate, first4 fixture rate);3x play/2x startup,1200s proof/readout/report reserve including already-spent stages. No elapsed-time stop.'})
            if reserve>7200:raise RuntimeError('revised cost quote exceeds accepted planning allowance before fresh hands')
        if pins!={p:sha(source/p) for p in pins} or sha(root/'control.json')!=config_sha or sha(binary)!=BINARY_SHA:
            raise RuntimeError('frozen source/config/binary changed')
        write(args.out/'status.json',{'status':'running','phase':phase,'completed_stages':len(costs),'total_stages':len(stages)})
        tick=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
        with (args.out/(phase+'.stdout')).open('x') as o,(args.out/(phase+'.stderr')).open('x') as e:
            child=subprocess.Popen(command,cwd=source,env=env,stdout=o,stderr=e,start_new_session=True)
            try:
                with (args.out/'resources.jsonl').open('a') as log:
                    while child.poll() is None:
                        if (root/'STOP').exists() or (args.out/'STOP').exists():raise RuntimeError('owner STOP')
                        sample={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'phase':phase,**thermal(),**resources(child.pid)}
                        log.write(json.dumps(sample,allow_nan=False)+'\n');log.flush()
                        if sample['cpu_c']>=90 or sample['thermistor15_c']>=100:
                            write(args.out/'thermal-crossing.json',sample);raise RuntimeError('thermal stop')
                        time.sleep(2)
            finally:stop(child.pid);child.wait()
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        costs.append({'phase':phase,'returncode':child.returncode,'wall_seconds':time.monotonic()-tick,
            'user_cpu_seconds':after.ru_utime-before.ru_utime,'system_cpu_seconds':after.ru_stime-before.ru_stime})
        write(args.out/'stage-costs.json',costs)
        if child.returncode:raise RuntimeError(f'{phase} failed with code{child.returncode}')
    if pins!={p:sha(source/p) for p in pins} or sha(root/'control.json')!=config_sha or sha(binary)!=BINARY_SHA:
        raise RuntimeError('frozen source/config/binary changed')
    write(args.out/'status.json',{'status':'complete','source':actual,'stages':len(stages)})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--source',required=True);a=p.parse_args()
    if a.out.exists():p.error('fresh output required; no automatic retry')
    def interrupted(signum,frame):raise InterruptedError('owner/process signal '+str(signum))
    signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
    try:run(a)
    except BaseException as e:
        if a.out.exists():
            write(a.out/'failure.json',{'error':str(e),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
            write(a.out/'status.json',{'status':'failed','reason':str(e)})
        raise


if __name__=='__main__':main()
