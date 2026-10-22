"""Owned PR398 fixed assessment: qualify, admit, measure all focals, then read out."""
import argparse
import fcntl
import os
from pathlib import Path
import resource
import signal
import subprocess
import time
import json

from scripts.river_whole_hand_pilot import read, write, sha
from scripts.river_three_lineage_assessment import (
    ALLOWANCE, PREVIOUS_BINARY_SHA, BLOCKS, FINAL_ROOTS, POLICY_SHA, QUAL_ROOTS, SEEDS, native_identity, preflight_quote,
)
from scripts.run_river_continuation_qualification import thermal, resources, stop


def validate_config(config):
    expected = {'planning_allowance_seconds': ALLOWANCE, 'threads': 4, 'seeds': list(SEEDS),
        'fresh_roots': list(FINAL_ROOTS), 'qualification_roots': list(QUAL_ROOTS),
        'blocks': BLOCKS, 'policy_sha256s': list(POLICY_SHA),
        'scripted_margin_bb100': -5, 'final_assessment_no_extension': True}
    if any(config.get(k) != v for k,v in expected.items()) or len(config.get('models',[])) != 3:
        raise ValueError('owner-approved scope/config differs')
    if (not isinstance(config.get('binary_sha256'),str) or len(config['binary_sha256'])!=64
            or any(c not in '0123456789abcdef' for c in config['binary_sha256'])):
        raise ValueError('explicit rebuilt binary checksum required')
    if len(set(config['models'])) != 3:
        raise ValueError('three distinct model paths required')


def run(args):
    args.out.mkdir(parents=True,exist_ok=False)
    root=args.root.resolve(); source=root/'source'; python=root/'venv/bin/python'; binary=root/'bin/nplayer_river_arena'
    config=read(root/'control.json'); validate_config(config); config_sha=sha(root/'control.json'); binary_sha=config['binary_sha256']
    locks=[]
    for name in ('/tmp/cfr-cygnus-exclusive.lock','/tmp/cfr-pr398-three-lineage.lock'):
        f=open(name,'a+'); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); locks.append(f)
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    if actual != args.source or subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True).strip():
        raise RuntimeError('clean exact frozen source required')
    if sha(binary) != binary_sha:
        raise RuntimeError('qualified native binary differs')
    prior=Path(config['qualified_root']); q=prior/'qualification-v1'
    if read(q/'status.json')['status']!='complete' or (q/'failure.json').exists() or any(x['returncode'] for x in read(q/'stage-costs.json')):
        raise RuntimeError('prior optimized qualification incomplete')
    paths=subprocess.check_output(['git','ls-files','native/hu20-trainer'],cwd=source,text=True).splitlines()
    native={p:sha(source/p) for p in paths if (source/p).is_file()}
    identity=native_identity(source,prior/'source',list(native))
    if read(q/'binary-pin.json')['sha256'] != PREVIOUS_BINARY_SHA:
        raise RuntimeError('previous qualified binary pin differs')
    build=read(root/'preparation/build-receipt.json')
    if build['binary_sha256']!=binary_sha or build['native_library_tests_returncode']!=0:
        raise RuntimeError('count-limit rebuild/native tests incomplete')
    write(args.out/'native-identity.json',{**identity,'files':native,'binary_sha256':binary_sha,'prior':str(q)})
    models=[]
    for seed,path,pin in zip(SEEDS,config['models'],POLICY_SHA):
        if sha(path)!=pin: raise RuntimeError('frozen policy checksum differs')
        p=Path(path); models.append({'seed':seed,'path':str(p),'sha256':pin,'bytes':p.stat().st_size})
    write(args.out/'model-pins.json',models)
    names=subprocess.check_output(['git','ls-files'],cwd=source,text=True).splitlines()
    pins={p:sha(source/p) for p in names if (source/p).is_file()}; write(args.out/'source-manifest.json',pins)
    write(args.out/'launch.json',{'pid':os.getpid(),'source':actual,'config_sha256':config_sha,
        'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'cpu_stop_c':90,'thermistor15_stop_c':100,
        'planning_allowance_seconds':ALLOWANCE,'no_other_resource_stops':True,
        'fresh_roots':list(FINAL_ROOTS),'blocks':BLOCKS,'initial_hands':221184,'reproduction_hands':221184,
        'final_assessment_no_extension':True})
    common=[str(python),'-m','scripts.river_three_lineage_assessment','--config',str(root/'control.json')]
    stages=[('python-tests',[str(python),'-m','unittest','tests.test_river_three_lineage_assessment',
        'tests.test_river_fresh_screen','tests.test_river_arena_expectation','tests.test_river_conditional_evaluation',
        'tests.test_river_whole_hand_pilot','-v']),
        ('environment',[str(python),'-c','import scipy.stats,numpy,pokers; print("Pinned evaluator imports passed")'])]
    for i,seed in enumerate(SEEDS):
        stages.append((f'qualification-{seed}',common+['qualify','--focal',str(i),'--binary',str(binary),
            '--out',str(args.out/'qualification'/str(seed))]))
    for i,seed in enumerate(SEEDS):
        stages.append((f'measure-{seed}',common+['measure','--focal',str(i),'--binary',str(binary),
            '--out',str(args.out/'measurement'/str(seed))]))
    stages.append(('readout',common+['readout','--input',str(args.out/'measurement'),'--out',str(args.out/'readout')]))
    env={**os.environ,'PYTHONPATH':str(source),'RAYON_NUM_THREADS':'1'}; costs=[]
    for phase,command in stages:
        if phase == f'measure-{SEEDS[0]}':
            qualifications=[]
            for seed in SEEDS:
                d=args.out/'qualification'/str(seed); proof=read(d/'verified.json')
                if proof['status']!='passed' or (d/'failure.json').exists():
                    raise RuntimeError('alias qualification failed')
                qualifications.append(read(d/'costs.json'))
            proposal=read(source/'docs/reports/river-fresh-screen/followup-proposal.json')
            quote=preflight_quote(proposal,qualifications,time.monotonic()-args.preparation_start)
            write(args.out/'main-admission.json',quote)
            if quote['status']!='admitted':
                raise RuntimeError('revised quote exceeds accepted12h before final hands; no automatic resize/retry')
        if (pins != {p:sha(source/p) for p in pins} or sha(root/'control.json') != config_sha or sha(binary) != binary_sha):
            raise RuntimeError('frozen source/config/binary changed')
        write(args.out/'status.json',{'status':'running','phase':phase,'completed_stages':len(costs),'total_stages':len(stages)})
        tick=time.monotonic(); before=resource.getrusage(resource.RUSAGE_CHILDREN)
        with (args.out/(phase+'.stdout')).open('x') as o,(args.out/(phase+'.stderr')).open('x') as e:
            child=subprocess.Popen(command,cwd=source,env=env,stdout=o,stderr=e,start_new_session=True)
            try:
                with (args.out/'resources.jsonl').open('a') as log:
                    while child.poll() is None:
                        if (root/'STOP').exists() or (args.out/'STOP').exists():raise RuntimeError('owner STOP')
                        sample={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'phase':phase,**thermal(),**resources(child.pid)}
                        log.write(json.dumps(sample,allow_nan=False)+'\n'); log.flush()
                        if sample['cpu_c']>=90 or sample['thermistor15_c']>=100:
                            write(args.out/'thermal-crossing.json',sample);raise RuntimeError('thermal stop')
                        time.sleep(2)
            finally:
                stop(child.pid); child.wait()
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        costs.append({'phase':phase,'returncode':child.returncode,'wall_seconds':time.monotonic()-tick,
            'user_cpu_seconds':after.ru_utime-before.ru_utime,'system_cpu_seconds':after.ru_stime-before.ru_stime})
        write(args.out/'stage-costs.json',costs)
        if child.returncode:raise RuntimeError(f'{phase} failed with code{child.returncode}')
    if pins != {p:sha(source/p) for p in pins} or sha(root/'control.json')!=config_sha or sha(binary)!=binary_sha:
        raise RuntimeError('frozen source/config/binary changed')
    write(args.out/'status.json',{'status':'complete','source':actual,'stages':len(stages)})


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True); p.add_argument('--source',required=True)
    p.add_argument('--preparation-seconds',type=float,default=0,
        help='Recorded owned model staging/source preparation cost, counted in the quote.')
    a=p.parse_args(); a.preparation_start=time.monotonic()-a.preparation_seconds
    if a.out.exists():p.error('fresh output required, no automatic scientific retry')
    def interrupted(signum,frame):raise InterruptedError('owner/process signal '+str(signum))
    signal.signal(signal.SIGINT,interrupted); signal.signal(signal.SIGTERM,interrupted)
    try:run(a)
    except BaseException as e:
        if a.out.exists():
            write(a.out/'failure.json',{'error':str(e),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
            write(a.out/'status.json',{'status':'failed','reason':str(e)})
        raise


if __name__=='__main__':main()
