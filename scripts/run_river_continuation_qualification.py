"""PR380 owner-authorized fixed stages, exclusive locks and scoped heat stops.

No wall-time, disk, RSS or swap stop. A fresh output root is mandatory; failures
are preserved and never automatically resumed. This supervisor owns every child
process group, including native workers started by its Python stage drivers.
"""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

from scripts.qualify_river_continuation import SHA, TRACE_SEEDS, write

MODEL=Path('/home/dberweger/nplayer-v06-acceptance-20261020/main-v1/inputs/2026101935003/candidate.bin')
K50=Path('/home/dberweger/cygnus-qualification-20261014/tables')
DEVELOPMENT=Path('/home/dberweger/river-search-round1-20261021/stage1/panel-2026102101/panel.jsonl')


def thermal():
    data=json.loads(subprocess.check_output(['sensors','-j'],timeout=10))
    cpus=[];thermistors=[]
    for chip,values in data.items():
        for label,fields in values.items():
            if not isinstance(fields,dict):continue
            inputs=[float(v) for k,v in fields.items() if k.endswith('_input')]
            if chip.startswith('coretemp-') and (label.startswith('Core ') or label.startswith('Package id ')):cpus+=inputs
            if label=='Thermistor 15':thermistors+=inputs
    if not cpus or len(thermistors)!=1 or any(not math.isfinite(v) for v in cpus+thermistors):
        raise RuntimeError('thermal sensor missing or nonfinite')
    return {'cpu_c':max(cpus),'thermistor15_c':thermistors[0]}


def resources(pgid):
    rss=0;cpu=0
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            fields=(p/'stat').read_text().split(') ',1)[1].split()
            if int(fields[2])!=pgid:continue
            rss+=int(fields[21])*os.sysconf('SC_PAGE_SIZE')
            cpu+=(int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK')
        except (OSError,ValueError,IndexError):continue
    mem={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines()}
    return {'worker_family_rss_bytes':rss,'live_family_cpu_seconds':cpu,'available_ram_bytes':mem['MemAvailable'],
            'swap_used_bytes':mem['SwapTotal']-mem['SwapFree'],
            'nvme_free_bytes':os.statvfs('/home/dberweger').f_bavail*os.statvfs('/home/dberweger').f_frsize,
            'hdd_free_bytes':os.statvfs('/mnt/data2tb').f_bavail*os.statvfs('/mnt/data2tb').f_frsize}


def stop(group):
    try:os.killpg(group,signal.SIGTERM)
    except ProcessLookupError:return
    end=time.monotonic()+5
    while time.monotonic()<end:
        try:os.killpg(group,0)
        except ProcessLookupError:return
        time.sleep(.1)
    try:os.killpg(group,signal.SIGKILL)
    except ProcessLookupError:pass


def run(args):
    args.out.mkdir(parents=True,exist_ok=False)
    root=args.root.resolve();source=root/'source';python=root/'venv/bin/python'
    target=root/'target';binary=target/'release/examples/river_live';play=target/'release/examples/nplayer_policy'
    locks=[]
    for path in ['/tmp/cfr-cygnus-exclusive.lock','/tmp/cfr-pr380-river.lock']:
        f=open(path,'a+')
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError(f'compute lock occupied: {path}')
        locks.append(f)
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    if actual!=args.source:raise RuntimeError('source commit differs')
    if subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True).strip():raise RuntimeError('source checkout modified')
    env={**os.environ,'PYTHONPATH':str(source),'CARGO_TARGET_DIR':str(target),'RAYON_NUM_THREADS':'1','CARGO_BUILD_JOBS':'8'}
    manifest={p:hashlib.sha256((source/p).read_bytes()).hexdigest() for p in
              subprocess.check_output(['git','ls-files'],cwd=source,text=True).splitlines() if (source/p).is_file()}
    write(args.out/'source-manifest.json',manifest)
    write(args.out/'launch.json',{'pid':os.getpid(),'source':actual,'mode':args.mode,'launched_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
          'model':str(MODEL),'model_sha256':SHA,'k50':str(K50),'cpu_stop_c':90,'thermistor15_stop_c':100,
          'no_other_resource_stops':True,'source_files':len(manifest)})
    common=['--binary',str(binary),'--k50',str(K50),'--model',str(MODEL)]
    driver=[str(python),'-m','scripts.qualify_river_continuation']
    stages=[]
    if args.mode=='calibration':
        stages += [('build',['cargo','build','--release','--locked','--manifest-path','native/hu20-trainer/Cargo.toml','--example','river_live','--example','nplayer_policy'],1),
                   ('native-tests',['cargo','test','--release','--locked','--manifest-path','native/hu20-trainer/Cargo.toml','--lib'],1),
                   ('python-tests',[str(python),'-m','pytest','-q','tests/test_live_river.py','tests/test_retained_river.py','tests/test_qualify_river_continuation.py'],1),
                   ('calibration',driver+['calibrate','--inputs',str(DEVELOPMENT),'--out',str(args.out/'calibration')]+common,16)]
    else:
        if not args.calibration or not (args.calibration/'status.json').exists() or json.loads((args.calibration/'status.json').read_text())['status']!='complete':
            raise RuntimeError('completed development calibration required')
        write(args.out/'calibration-pin.json',{'path':str(args.calibration),'quote':json.loads((args.calibration/'calibration/quote.json').read_text())})
        inputs=args.out/'traces';inputs.mkdir()
        for i,seed in enumerate(TRACE_SEEDS):
            for suffix in ['', '-repeat']:
                trace=inputs/f'trace-{i}{suffix}.jsonl'
                stages.append((f'trace-{i}{suffix}',[str(play),'play',str(K50),'5000',str(seed),str(trace)]+[str(MODEL),SHA]*3,1))
            stages.append((f'replay-{i}',[str(python),'-m','scripts.check_nplayer_policy_replay',str(inputs/f'trace-{i}.jsonl')],1))
        stages.append(('freeze',driver+['freeze','--inputs',str(inputs),'--out',str(args.out/'panel'),'--source',actual]+common,1))
        for repetition in ['initial','repeat']:
            for phase in ['strict','deployment','retained','belief']:
                stages.append((f'{repetition}-{phase}',driver+['measure','--inputs',str(args.out/'panel'),'--out',str(args.out/repetition/phase),'--phase',phase]+common,16 if phase=='belief' else 1))
        stages.append(('verify',driver+['verify','--inputs',str(args.out),'--out',str(args.out/'verification')],1))
    costs=[]
    for name,command,threads in stages:
        before=resource.getrusage(resource.RUSAGE_CHILDREN);tick=time.monotonic()
        write(args.out/'status.json',{'status':'running','phase':name,'completed_stages':len(costs),'total_stages':len(stages)})
        with (args.out/f'{name}.stdout').open('x') as stdout,(args.out/f'{name}.stderr').open('x') as stderr:
            child=subprocess.Popen(command,cwd=source,env={**env,'RAYON_NUM_THREADS':str(threads)},stdout=stdout,stderr=stderr,start_new_session=True)
            try:
                with (args.out/'resources.jsonl').open('a') as log:
                    while child.poll() is None:
                        if (args.out/'STOP').exists() or (root/'STOP').exists():
                            raise RuntimeError('owner STOP requested')
                        sample={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'phase':name,**thermal(),**resources(child.pid)}
                        log.write(json.dumps(sample,separators=(',',':'))+'\n');log.flush()
                        if sample['cpu_c']>=90 or sample['thermistor15_c']>=100:
                            write(args.out/'thermal-crossing.json',sample)
                            raise RuntimeError('thermal stop: '+json.dumps(sample))
                        time.sleep(2)
            finally:
                stop(child.pid);child.wait()
            if child.returncode:raise RuntimeError(f'{name} failed with return code {child.returncode}')
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        costs.append({'phase':name,'command':command,'returncode':child.returncode,'wall_seconds':time.monotonic()-tick,
                      'user_cpu_seconds':after.ru_utime-before.ru_utime,'system_cpu_seconds':after.ru_stime-before.ru_stime})
        write(args.out/'stage-costs.json',costs)
        if name.startswith('replay-'):
            proof=json.loads((args.out/f'{name}.stdout').read_text());write(inputs/f'{name}.json',proof)
    write(args.out/'status.json',{'status':'complete','stages':len(costs),'source':actual})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['calibration','main'])
    for name in ['root','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--source',required=True);p.add_argument('--calibration',type=Path)
    args=p.parse_args()
    if args.out.exists():p.error('output root already exists; refusing to overwrite or retry')
    def interrupted(signum,frame):raise InterruptedError(f'owner/process signal {signum}')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:run(args)
    except BaseException as error:
        if args.out.exists():
            write(args.out/'failure.json',{'error':str(error),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
            write(args.out/'status.json',{'status':'failed','reason':str(error)})
        raise


if __name__=='__main__':main()
