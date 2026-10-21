"""Exclusive, temperature-guarded PR382 stages. No runtime resource/time cutoff.

Previous science and source are read-only. Every attempt needs a fresh output;
no scientific retry or whole-hand continuation is performed automatically.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

from scripts.qualify_river_continuation import SHA, sha, write
from scripts.qualify_river_exact import inputs, PANEL_SHA
from scripts.run_river_continuation_qualification import thermal,resources,stop,MODEL,K50

PARENT=Path('/home/dberweger/river-continuation-qualification-20261021/main-v1')


def run(args):
    args.out.mkdir(parents=True,exist_ok=False)
    root=args.root.resolve();source=root/'source';python=root/'venv/bin/python';target=root/'target'
    locks=[]
    for path in ('/tmp/cfr-cygnus-exclusive.lock','/tmp/cfr-pr382-exact-river.lock'):
        f=open(path,'a+')
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('compute lock occupied: '+path)
        locks.append(f)
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    if actual!=args.source or subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True).strip():
        raise RuntimeError('source commit/clean checkout mismatch')
    cases,controls,old=inputs(PARENT)
    write(args.out/'parent-pins.json',{'root':str(PARENT),'panel_sha256':PANEL_SHA,'model_sha256':SHA,
        'controls':controls,'original_deployment_sha256':sha(PARENT/'initial/deployment/records.jsonl'),
        'parent_verification_sha256':sha(PARENT/'verification/verified.json')})
    paths=subprocess.check_output(['git','ls-files'],cwd=source,text=True).splitlines()
    write(args.out/'source-manifest.json',{p:sha(source/p) for p in paths if (source/p).is_file()})
    write(args.out/'launch.json',{'pid':os.getpid(),'source':actual,'mode':args.mode,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'model':str(MODEL),'model_sha256':SHA,'parent_panel_sha256':PANEL_SHA,'cpu_stop_c':90,'thermistor15_stop_c':100,
        'no_other_resource_stops':True})
    binary=target/'release/examples/river_live'
    driver=[str(python),'-m','scripts.qualify_river_exact']
    common=['--binary',str(binary),'--k50',str(K50),'--model',str(MODEL)]
    stages=[]
    if args.mode=='calibration':
        stages += [('build',['cargo','build','--release','--locked','--manifest-path','native/hu20-trainer/Cargo.toml','--example','river_live'],1),
            ('native-tests',['cargo','test','--release','--locked','--manifest-path','native/hu20-trainer/Cargo.toml','--lib'],1),
            ('python-tests',[str(python),'-m','pytest','-q','tests/test_qualify_river_exact.py','tests/test_summarize_river_continuation.py'],1)]
        for phase in ('controls','projected','exact'):
            stages.append((phase,driver+['calibrate','--inputs',str(PARENT),'--out',str(args.out/phase),'--phase',phase]+common,16 if phase=='controls' else 1))
        stages.append(('quote',driver+['quote','--inputs',str(args.out),'--out',str(args.out/'quote')],1))
    else:
        if not args.calibration or json.loads((args.calibration/'status.json').read_text())['status']!='complete' or (args.calibration/'failure.json').exists():
            raise RuntimeError('completed calibration required')
        quote=json.loads((args.calibration/'quote/quote.json').read_text())
        if quote['upper_seconds']>7200:raise RuntimeError('calibration exceeds quoted1–2h scope; report before main work')
        write(args.out/'calibration-pin.json',{'path':str(args.calibration),'quote':quote})
        for repetition in ('initial','repeat'):
            for phase in ('controls','projected','exact'):
                stages.append((repetition+'-'+phase,driver+['measure','--inputs',str(PARENT),'--out',str(args.out/repetition/phase),'--phase',phase]+common,16 if phase=='controls' else 1))
        stages.append(('verify',driver+['verify','--inputs',str(args.out),'--out',str(args.out/'verification')],1))
    env={**os.environ,'PATH':'/home/dberweger/.cargo/bin:'+os.environ.get('PATH',''),
        'PYTHONPATH':str(source),'CARGO_TARGET_DIR':str(target),'CARGO_BUILD_JOBS':'8'}
    write(args.out/'environment.json',{'python':sys.version,'rustc':subprocess.check_output(['rustc','-vV'],env=env,text=True).strip(),'cargo':subprocess.check_output(['cargo','-V'],env=env,text=True).strip(),'ordinary_rayon_threads':1,'control_rayon_threads':16})
    costs=[]
    for phase,command,threads in stages:
        write(args.out/'status.json',{'status':'running','phase':phase,'completed_stages':len(costs),'total_stages':len(stages)})
        tick=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
        with (args.out/(phase+'.stdout')).open('x') as stdout,(args.out/(phase+'.stderr')).open('x') as stderr:
            child=subprocess.Popen(command,cwd=source,env={**env,'RAYON_NUM_THREADS':str(threads)},stdout=stdout,stderr=stderr,start_new_session=True)
            try:
                with (args.out/'resources.jsonl').open('a') as log:
                    while child.poll() is None:
                        if (root/'STOP').exists() or (args.out/'STOP').exists():raise RuntimeError('owner STOP requested')
                        sample={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'phase':phase,**thermal(),**resources(child.pid)}
                        log.write(json.dumps(sample,allow_nan=False,separators=(',',':'))+'\n');log.flush()
                        if sample['cpu_c']>=90 or sample['thermistor15_c']>=100:
                            write(args.out/'thermal-crossing.json',sample);raise RuntimeError('thermal stop: '+json.dumps(sample))
                        time.sleep(2)
            finally:stop(child.pid);child.wait()
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        costs.append({'phase':phase,'command':command,'returncode':child.returncode,'wall_seconds':time.monotonic()-tick,
            'user_cpu_seconds':after.ru_utime-before.ru_utime,'system_cpu_seconds':after.ru_stime-before.ru_stime})
        write(args.out/'stage-costs.json',costs)
        if child.returncode:raise RuntimeError(f'{phase} failed with return code{child.returncode}')
    write(args.out/'binary-pin.json',{'river_live_sha256':sha(binary),'protocol_sha256':sha(source/'docs/river-exact-beliefs.md')})
    write(args.out/'status.json',{'status':'complete','stages':len(costs),'source':actual})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['calibration','main'])
    for name in ('root','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--source',required=True);p.add_argument('--calibration',type=Path);args=p.parse_args()
    if args.out.exists():p.error('fresh output root required; no automatic retry')
    def interrupted(signum,frame):raise InterruptedError('owner/process signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:run(args)
    except BaseException as error:
        if args.out.exists():
            write(args.out/'failure.json',{'error':str(error),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
            write(args.out/'status.json',{'status':'failed','reason':str(error)})
        raise

if __name__=='__main__':main()
