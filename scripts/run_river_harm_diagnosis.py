"""PR384 owned, fixed stages. Temperature-only resource stops; no retries."""
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

from scripts.qualify_river_continuation import write,sha
from scripts.run_river_continuation_qualification import MODEL,K50,thermal,resources,stop

PARENT=Path('/home/dberweger/river-exact-beliefs-20261021/main-v1')
PANEL=Path('/home/dberweger/river-continuation-qualification-20261021/main-v1')


def run(args):
    args.out.mkdir(parents=True);root=args.root.resolve();source=root/'source';python=root/'venv/bin/python'
    target=root/'target';locks=[]
    for name in ('/tmp/cfr-cygnus-exclusive.lock','/tmp/cfr-pr384-river-harms.lock'):
        f=open(name,'a+');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    if actual!=args.source or subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True).strip():raise RuntimeError('source pin/clean checkout mismatch')
    env={**os.environ,'PATH':'/home/dberweger/.cargo/bin:'+os.environ.get('PATH',''),'PYTHONPATH':str(source),
        'CARGO_TARGET_DIR':str(target),'CARGO_BUILD_JOBS':'8','RAYON_NUM_THREADS':'1'}
    binary=target/'release/examples/river_live'
    write(args.out/'launch.json',{'source':actual,'pid':os.getpid(),'mode':args.mode,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'cpu_stop_c':90,'thermistor15_stop_c':100,'no_other_resource_stops':True,'workers':1,'rayon':1})
    paths=subprocess.check_output(['git','ls-files'],cwd=source,text=True).splitlines()
    manifest={p:sha(source/p) for p in paths if (source/p).is_file()};write(args.out/'source-manifest.json',manifest)
    driver=[str(python),'-m','scripts.diagnose_river_harms']
    common=['--parent',str(PARENT),'--panel',str(PANEL),'--binary',str(binary),'--k50',str(K50),'--model',str(MODEL)]
    if args.mode=='calibration':
        stages=[('build',['cargo','build','--release','--locked','--manifest-path','native/hu20-trainer/Cargo.toml','--example','river_live']),
            ('native-tests',['cargo','test','--release','--locked','--manifest-path','native/hu20-trainer/Cargo.toml','--lib']),
            ('python-tests',[str(python),'-m','pytest','-q','tests/test_diagnose_river_harms.py','tests/test_summarize_river_exact.py']),
            ('calibrate',driver+['calibrate','--out',str(args.out/'calibrate')]+common),
            ('quote',driver+['quote','--capture',str(args.out/'calibrate'),'--out',str(args.out/'quote')]+common)]
    else:
        cal=args.calibration
        if not cal or (cal/'failure.json').exists() or json.loads((cal/'status.json').read_text())['status']!='complete':raise RuntimeError('qualified calibration required')
        if json.loads((cal/'source-manifest.json').read_text())!=manifest:raise RuntimeError('qualified source changed')
        if json.loads((cal/'binary-pin.json').read_text())!={'sha256':sha(binary)}:raise RuntimeError('qualified binary changed')
        quote=json.loads((cal/'quote/quote.json').read_text())
        if quote['upper_seconds']>3600:raise RuntimeError('quoted task exceeds one-hour scope; report before main')
        write(args.out/'calibration-pin.json',{'path':str(cal),'quote':quote})
        capture=args.out/'capture'
        stages=[('capture',driver+['capture','--out',str(capture)]+common)]
        stages +=[(name,driver+[name,'--capture',str(capture),'--out',str(args.out/name)]+common) for name in ('initial','repeat','verify')]
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
    if manifest!={p:sha(source/p) for p in manifest}:raise RuntimeError('source changed during qualification')
    write(args.out/'binary-pin.json',{'sha256':sha(binary)})
    write(args.out/'status.json',{'status':'complete','source':actual,'stages':len(stages)})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['calibration','main'])
    for k in ('root','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--source',required=True);p.add_argument('--calibration',type=Path);args=p.parse_args()
    if args.out.exists():p.error('fresh output required; no automatic retry')
    def interrupted(signum,frame):raise InterruptedError('owner/process signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:run(args)
    except BaseException as e:
        if args.out.exists():
            write(args.out/'failure.json',{'error':str(e),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
            write(args.out/'status.json',{'status':'failed','reason':str(e)})
        raise

if __name__=='__main__':main()
