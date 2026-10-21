"""Owned PR388 stages: no automatic science retry, temperature-only resource stops."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

from scripts.river_whole_hand_pilot import read, write, sha, FOCAL_SHA, PEER_SHA
from scripts.run_river_continuation_qualification import thermal, resources, stop


def run(args):
    args.out.mkdir(parents=True, exist_ok=False)
    root=args.root.resolve();source=root/'source';python=root/'venv/bin/python'
    config=read(root/'control.json');config_sha=sha(root/'control.json')
    locks=[]
    for name in ('/tmp/cfr-cygnus-exclusive.lock','/tmp/cfr-pr388-river-whole-hand.lock'):
        f=open(name,'a+');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    if actual!=args.source or subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True).strip():
        raise RuntimeError('source pin or clean checkout mismatch')
    files=subprocess.check_output(['git','ls-files'],cwd=source,text=True).splitlines()
    pins={p:sha(source/p) for p in files if (source/p).is_file()}
    write(args.out/'source-manifest.json',pins)
    write(args.out/'launch.json',{'pid':os.getpid(),'source':actual,'config_sha256':config_sha,'mode':args.mode,
        'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'cpu_stop_c':90,'thermistor15_stop_c':100,
        'no_other_resource_stops':True,'focal_sha256':FOCAL_SHA,'peer_sha256':PEER_SHA})
    target=root/'target';binary=target/'release/examples/nplayer_river_arena'
    legacy=target/'release/examples/nplayer_arena'
    env={**os.environ,'PATH':'/home/dberweger/.cargo/bin:'+os.environ.get('PATH',''),
         'PYTHONPATH':str(source),'CARGO_TARGET_DIR':str(target),'CARGO_BUILD_JOBS':'8','RAYON_NUM_THREADS':'1'}
    driver=[str(python),'-m','scripts.river_whole_hand_pilot']
    common=['--binary',str(binary),'--legacy',str(legacy),'--k50',config['k50'],
            '--focal',config['focal'],'--peer',config['peer']]
    if args.mode=='qualify':
        stages=[('build',['cargo','build','--release','--locked','--manifest-path','native/hu20-trainer/Cargo.toml',
                         '--example','nplayer_river_arena','--example','nplayer_arena','--example','river_live']),
                ('native-tests',['cargo','test','--release','--locked','--manifest-path','native/hu20-trainer/Cargo.toml','--lib']),
                ('python-tests',[str(python),'-m','unittest','tests.test_river_whole_hand_pilot','-v']),
                ('fixture',driver+['fixture','--out',str(args.out/'fixture')]+common)]
    else:
        qualified=root/'qualification-v1'
        if (qualified/'failure.json').exists() or read(qualified/'status.json')['status']!='complete':
            raise RuntimeError('successful original qualification required')
        if read(qualified/'source-manifest.json')!=pins or read(qualified/'launch.json')['config_sha256']!=config_sha:
            raise RuntimeError('qualified source/config changed')
        if read(qualified/'binary-pin.json')['sha256']!=sha(binary):
            raise RuntimeError('qualified native binary changed')
        if args.mode=='calibrate':
            stages=[('calibrate',driver+['calibrate','--out',str(args.out/'calibrate')]+common)]
        else:
            calibration=root/'calibration-v1'
            if (calibration/'failure.json').exists() or read(calibration/'status.json')['status']!='complete':
                raise RuntimeError('successful calibration required')
            if read(calibration/'source-manifest.json')!=pins or read(calibration/'launch.json')['config_sha256']!=config_sha:
                raise RuntimeError('calibrated source/config changed')
            quote=calibration/'calibrate/quote.json'
            if not read(quote)['main_admitted'] or read(quote)['upper_seconds']>10800:
                raise RuntimeError('quoted upper cost exceeds accepted pilot')
            receipt=read(root/'quote-published.json')
            if receipt['quote_sha256']!=sha(quote) or receipt['source']!=actual:
                raise RuntimeError('quote must be published before main')
            stages=[('measure',driver+['measure','--out',str(args.out/'measure'),
                      '--calibration',str(calibration/'calibrate')]+common),
                    ('readout',driver+['readout','--inputs',str(args.out/'measure'),'--out',str(args.out/'readout')])]
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
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['qualify','calibrate','main'])
    p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--source',required=True);args=p.parse_args()
    if args.out.exists():p.error('fresh output required; no automatic retry')
    def interrupted(signum,frame):raise InterruptedError('owner/process signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:run(args)
    except BaseException as error:
        if args.out.exists():
            write(args.out/'failure.json',{'error':str(error),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
            write(args.out/'status.json',{'status':'failed','reason':str(error)})
        raise


if __name__=='__main__':main()
