"""Owned integration qualification, cost calibration and explicitly admitted measurement."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

from scripts.river_whole_hand_pilot import read,write,sha
from scripts.run_river_continuation_qualification import thermal,resources,stop


def run(args):
    args.out.mkdir(parents=True,exist_ok=False)
    root=args.root.resolve();source=root/'source';python=root/'venv/bin/python'
    config=read(root/'control.json');config_sha=sha(root/'control.json');locks=[]
    for name in ('/tmp/cfr-cygnus-exclusive.lock','/tmp/cfr-pr393-arena-expectation.lock'):
        f=open(name,'a+');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    if actual!=args.source or subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True).strip():
        raise RuntimeError('source pin or clean checkout differs')
    names=subprocess.check_output(['git','ls-files'],cwd=source,text=True).splitlines()
    pins={p:sha(source/p) for p in names if (source/p).is_file()}
    write(args.out/'source-manifest.json',pins)
    write(args.out/'launch.json',{'pid':os.getpid(),'source':actual,'config_sha256':config_sha,'mode':args.mode,
        'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'cpu_stop_c':90,'thermistor15_stop_c':100,
        'no_other_resource_stops':True,'no_new_deals':True,'no_strength_run':True})
    target=root/'target';binary=target/'release/examples/nplayer_river_arena'
    env={**os.environ,'PATH':'/home/dberweger/.cargo/bin:'+os.environ.get('PATH',''),
         'PYTHONPATH':str(source),'CARGO_TARGET_DIR':str(target),'CARGO_BUILD_JOBS':'8','RAYON_NUM_THREADS':'1'}
    if args.mode=='qualify':
        stages=[('build',['cargo','build','--release','--locked','--manifest-path','native/hu20-trainer/Cargo.toml','--example','nplayer_river_arena']),
            ('native-tests',['cargo','test','--release','--locked','--manifest-path','native/hu20-trainer/Cargo.toml','--lib']),
            ('python-tests',[str(python),'-m','unittest','tests.test_river_arena_expectation','tests.test_river_conditional_evaluation','tests.test_river_whole_hand_pilot','-v'])]
    else:
        qual=root/'qualification-v1'
        if ((qual/'failure.json').exists() or read(qual/'status.json')['status']!='complete'
                or any(x['returncode'] for x in read(qual/'stage-costs.json'))
                or read(qual/'source-manifest.json')!=pins or read(qual/'launch.json')['config_sha256']!=config_sha
                or read(qual/'binary-pin.json')['sha256']!=sha(binary)):
            raise RuntimeError('successful unchanged source/config/binary qualification required')
        command=[str(python),'-m','scripts.river_arena_expectation',args.mode,'--out',str(args.out/args.mode),
                 '--source',actual,'--binary',str(binary)]
        for key in ('pilot','reference','focal','peer','k50'):command+=['--'+key,config[key]]
        if args.mode=='measure':
            cal=root/'calibration-v1'
            if ((cal/'failure.json').exists() or read(cal/'status.json')['status']!='complete'
                    or read(cal/'source-manifest.json')!=pins or read(cal/'launch.json')['config_sha256']!=config_sha
                    or read(cal/'binary-pin.json')['sha256']!=sha(binary)):
                raise RuntimeError('successful unchanged calibration required')
            command+=['--calibration',str(cal/'calibrate'),'--acceptance',str(root/'quote-accepted.json')]
        stages=[(args.mode,command)]
    costs=[]
    for phase,command in stages:
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
    if pins!={p:sha(source/p) for p in pins} or sha(root/'control.json')!=config_sha:
        raise RuntimeError('frozen source/config changed')
    write(args.out/'binary-pin.json',{'sha256':sha(binary)})
    write(args.out/'status.json',{'status':'complete','source':actual,'stages':len(stages)})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['qualify','calibrate','measure'])
    p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--source',required=True)
    args=p.parse_args()
    if args.out.exists():p.error('fresh output required; no automatic retry')
    def interrupted(signum,frame):raise InterruptedError('owner/process signal '+str(signum))
    signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
    try:run(args)
    except BaseException as e:
        if args.out.exists():
            write(args.out/'failure.json',{'error':str(e),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
            write(args.out/'status.json',{'status':'failed','reason':str(e)})
        raise


if __name__=='__main__':main()
