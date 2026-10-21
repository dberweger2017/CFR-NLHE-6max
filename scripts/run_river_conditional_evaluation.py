"""Qualification/calibration; full assessment needs an accepted measured quote."""
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
from scripts.run_river_continuation_qualification import thermal, resources, stop


def run(args):
    args.out.mkdir(parents=True,exist_ok=False)
    root=args.root.resolve();source=(args.implementation_root or root/'source').resolve();python=root/'venv/bin/python'
    if args.implementation_root and args.mode!='assess':
        raise RuntimeError('original qualification/calibration use their unchanged source')
    if args.mode=='assess' and source==(root/'source').resolve():
        raise RuntimeError('use a separate pinned assessment checkout; preserve qualified source')
    config=read(root/'control.json');config_sha=sha(root/'control.json')
    locks=[]
    for name in ('/tmp/cfr-cygnus-exclusive.lock','/tmp/cfr-pr390-conditional.lock'):
        f=open(name,'a+');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    if actual!=args.source or subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True).strip():
        raise RuntimeError('source pin or clean checkout differs')
    names=subprocess.check_output(['git','ls-files'],cwd=source,text=True).splitlines()
    pins={p:sha(source/p) for p in names if (source/p).is_file()}
    write(args.out/'source-manifest.json',pins)
    write(args.out/'launch.json',{'pid':os.getpid(),'source':actual,'config_sha256':config_sha,
        'mode':args.mode,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'cpu_stop_c':90,'thermistor15_stop_c':100,'no_other_resource_stops':True,
        'new_deals':False,'training':False,'main_inventory_requested':args.mode=='assess',
        'main_inventory_started':False})
    target=root/'target';binary=target/'release/examples/nplayer_river_expectation'
    env={**os.environ,'PATH':'/home/dberweger/.cargo/bin:'+os.environ.get('PATH',''),
         'PYTHONPATH':str(source),'CARGO_TARGET_DIR':str(target),'CARGO_BUILD_JOBS':'8','RAYON_NUM_THREADS':'1'}
    driver=[str(python),'-m','scripts.river_conditional_evaluation']
    if args.mode=='qualify':
        stages=[('build',['cargo','build','--release','--locked','--manifest-path','native/hu20-trainer/Cargo.toml','--example','nplayer_river_expectation']),
            ('native-tests',['cargo','test','--release','--locked','--manifest-path','native/hu20-trainer/Cargo.toml','--lib']),
            ('script-tests',['cargo','test','--release','--locked','--manifest-path','native/hu20-trainer/Cargo.toml','--example','nplayer_river_expectation']),
            ('python-tests',[str(python),'-m','unittest','tests.test_river_conditional_evaluation','tests.test_river_whole_hand_pilot','-v']),
            ('freeze',driver+['freeze','--pilot',config['pilot'],'--out',str(args.out/'inventory')])]
    else:
        qual=root/'qualification-v1'
        if ((qual/'failure.json').exists() or read(qual/'status.json')['status']!='complete'
                or any(c['returncode'] for c in read(qual/'stage-costs.json'))):
            raise RuntimeError('complete original qualification required')
        qualified=read(qual/'source-manifest.json')
        if read(qual/'launch.json')['config_sha256']!=config_sha:
            raise RuntimeError('qualified config changed')
        if args.mode=='calibrate' and qualified!=pins:
            raise RuntimeError('qualified source changed')
        if read(qual/'binary-pin.json')['sha256']!=sha(binary):
            raise RuntimeError('qualified binary changed')
        if args.mode=='calibrate':
            stages=[('calibrate',driver+['calibrate','--inventory',str(qual/'inventory/inventory.json'),
                '--binary',str(binary),'--out',str(args.out/'calibrate')])]
        else:
            # Measurement binary and native source remain exactly qualified;
            # only the separately pinned orchestration/readout may differ.
            critical=lambda p:p.startswith('native/') or p in ('scripts/river_whole_hand_pilot.py',
                'scripts/run_river_continuation_qualification.py')
            if {p:v for p,v in qualified.items() if critical(p)}!={p:v for p,v in pins.items() if critical(p)}:
                raise RuntimeError('qualified native/helper source changed')
            cal=root/'calibration-v1'
            if ((cal/'failure.json').exists() or read(cal/'status.json')['status']!='complete'
                    or any(c['returncode'] for c in read(cal/'stage-costs.json'))
                    or read(cal/'source-manifest.json')!=qualified
                    or read(cal/'launch.json')['config_sha256']!=config_sha
                    or read(cal/'binary-pin.json')['sha256']!=sha(binary)):
                raise RuntimeError('unchanged successful original calibration required')
            from scripts.assess_river_conditional_evaluation import admission
            admission(read(cal/'calibrate/quote.json'),sha(cal/'calibrate/quote.json'),
                      args.accepted_quote_sha256,args.accepted_budget_seconds)
            stages=[('assessment-tests',[str(python),'-m','unittest','tests.test_river_conditional_evaluation','-v']),
                ('assess',[str(python),'-m','scripts.assess_river_conditional_evaluation',
                    '--inventory',str(qual/'inventory/inventory.json'),'--calibration',str(cal/'calibrate'),
                    '--binary',str(binary),'--out',str(args.out/'assess'),
                    '--accepted-quote-sha256',args.accepted_quote_sha256,
                    '--accepted-budget-seconds',str(args.accepted_budget_seconds)])]
    costs=[]
    for phase,command in stages:
        write(args.out/'status.json',{'status':'running','phase':phase,'completed_stages':len(costs),
            'total_stages':len(stages),'main_inventory_started':phase=='assess'})
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
    p.add_argument('mode',choices=['qualify','calibrate','assess'])
    p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--implementation-root',type=Path)
    p.add_argument('--accepted-quote-sha256')
    p.add_argument('--accepted-budget-seconds',type=float)
    p.add_argument('--source',required=True);args=p.parse_args()
    if args.mode=='assess' and (args.accepted_quote_sha256 is None or args.accepted_budget_seconds is None):
        p.error('assessment requires explicit accepted quote SHA256 and planning allowance')
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
