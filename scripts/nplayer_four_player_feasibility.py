"""Bounded N-player100BB M4 pilot tools; default is frozen four-player scope."""
import argparse
import fcntl
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

SOURCE=Path(__file__).resolve().parents[1]
SEED=2026102240601
QUAL_SEED=2026102240591
COST_SEED=2026102240592
TARGETS=(25000000,50000000)
CAP=20000000
NAMES=('nplayer_train','nplayer_policy','nplayer_parity')
TABLES={'flop-k50.bin':'084e243ded9fe93ad03cd59601f22f16c3210592f51e1e3646a60983b572c111',
 'turn-k50.bin':'c0bc6a8aa0535553118109d18a32d3b4dc6880e937c263cdc87472b1ae9f168f',
 'river-k50.bin':'70c1cb5ecf4cd292e4c89dc2200f7c8381100be3b0288ceeb0a12a3e83977629'}


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def load(p):return json.loads(Path(p).read_text())


def write(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')


def source_identity():
    if subprocess.check_output(['git','status','--porcelain'],cwd=SOURCE,text=True).strip():raise ValueError('clean committed source required')
    names=subprocess.check_output(['git','ls-files','native','scripts','src','tests/test_nplayer_four_player_feasibility.py','tests/test_nplayer_five_six_feasibility.py','docs/nplayer-four-player-feasibility.md','docs/nplayer-five-six-feasibility.md'],cwd=SOURCE,text=True).splitlines()
    return dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),files={n:sha(SOURCE/n) for n in names})


def sample(root,thermal,pid=None):
    import psutil
    state=subprocess.check_output([str(thermal)],text=True,timeout=10).strip()
    if state not in ('nominal','fair','serious','critical'):raise ValueError('missing/unknown thermal state')
    processes=[]
    if pid:
        try:
            parent=psutil.Process(pid)
            for p in [parent,*parent.children(recursive=True)]:
                try:processes.append(dict(pid=p.pid,rss=p.memory_info().rss,cpu=sum(p.cpu_times()[:2])))
                except (psutil.NoSuchProcess,psutil.ZombieProcess):pass
        except (psutil.NoSuchProcess,psutil.ZombieProcess):pass
    return dict(epoch=time.time(),thermal_state=state,available_ram_bytes=psutil.virtual_memory().available,
        swap_used_bytes=psutil.swap_memory().used,disk_free_bytes=__import__('shutil').disk_usage(root).free,
        pressure=int(subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True)),
        worker_family_rss_bytes=sum(x['rss'] for x in processes),live_cpu_seconds=sum(x['cpu'] for x in processes))


class Supervisor:
    def __init__(self,root,env,thermal):
        self.root=root;self.env=env;self.thermal=thermal;self.costs=[];self.child=None
        self.config_sha=sha(root/'config.json') if (root/'config.json').exists() else None
        self.stop_files=(root/'STOP',Path(env.get('NPLAYER_STOP_FILE',str(root/'STOP'))))
    def stage(self,name,args):
        if self.config_sha is not None and sha(self.root/'config.json')!=self.config_sha:raise ValueError('frozen config changed')
        folder=self.root/'measurements'/name;folder.mkdir(parents=True,exist_ok=False)
        write(self.root/'status.json',dict(status='running',phase=name,completed_stages=len(self.costs)))
        before=resource.getrusage(resource.RUSAGE_CHILDREN);tick=time.monotonic();peak=0
        initial=sample(self.root,self.thermal)
        if initial['thermal_state'] in ('serious','critical') or any(p.exists() for p in self.stop_files):raise RuntimeError('thermal/ownerSTOP admission')
        with (folder/'stdout.log').open('x') as out,(folder/'stderr.log').open('x') as err:
            child=subprocess.Popen(list(map(str,args)),cwd=SOURCE,env=self.env,stdout=out,stderr=err,start_new_session=True);self.child=child
            try:
                with (self.root/'resources.jsonl').open('a') as log:
                    while child.poll() is None:
                        x=dict(sample(self.root,self.thermal,child.pid),phase=name);peak=max(peak,x['worker_family_rss_bytes'])
                        log.write(json.dumps(x)+'\n');log.flush()
                        if x['thermal_state'] in ('serious','critical') or any(p.exists() for p in self.stop_files):raise RuntimeError('thermal/ownerSTOP')
                        time.sleep(1)
                code=child.wait()
            except BaseException:
                if child.poll() is None:
                    os.killpg(child.pid,signal.SIGTERM)
                    try:child.wait(timeout=5)
                    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                raise
            finally:self.child=None
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        row=dict(phase=name,command=list(map(str,args)),returncode=code,wall_seconds=time.monotonic()-tick,
            cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,sampled_peak_rss_bytes=peak)
        self.costs.append(row);write(folder/'receipt.json',row);write(self.root/'stage-costs.json',self.costs)
        if code:raise RuntimeError(f'{name} failed:{code}; preserve/no automatic retry')
        return row


def train_command(c,out,target,seed,cap,parent=None,threads=10):
    args=[c['binaries']['nplayer_train'],'--players',str(c.get('players',4)),'--stack-bb','100','--small-blind','50','--big-blind','100',
        '--fast','--threads',str(threads),'--roots-per-seat','8','--seed',str(seed),'--nodes',str(target),
        '--max-entries',str(cap),'--freeze-at-cap','--last-average-street','3','--fast-gzip','--max-seconds','1e100',
        '--card-buckets',c['tables'],'--out',str(out),'--telemetry',str(out)+'.progress.jsonl']
    if parent:args+=['--resume',parent['checkpoint'],'--resume-sha256',parent['sha256']]
    return args


def checkpoint(summary,path,target,seed,cap,players=4):
    with gzip.open(path,'rt') as f:h=json.loads(next(f))
    identity=h['game']
    if (identity['players']!=players or identity['stacks']!=[10000]*players or identity['big_blind']!=100 or identity['small_blind']!=50
            or identity['menu']!='min-pot-conditional-jam-v1' or identity['schema']!='nplayer-button-live-actor-history-equity-k50-v1'
            or identity!=summary['identity'] or h['seed']!=seed or h['max_entries']!=cap or not h['freeze_at_cap']
            or h['roots_per_seat']!=8 or h['last_average_street']!=3 or h['average_rule']!='opponent-sampled'
            or h['sampling']!='path-v1' or 'pruning' in h or h['counts']!=summary['counts'] or h['entries']!=summary['entries']
            or h['frozen_at']!=summary['frozen_at'] or summary['counts']['nodes']<target or summary['stop_reason']!='nodes'
            or sha(path)!=summary['sha256']):raise ValueError('checkpoint player/recipe/count/hash differs')
    if h['frozen_at'] is None and any(h['counts'][x] for x in ('discarded_keys','discarded_visits')):raise ValueError('discard before freeze')
    return h


def train(root,c,sup,name,target,seed,cap,parent=None,threads=10):
    out=root/(name+'.gz');cost=sup.stage(name,train_command(c,out,target,seed,cap,parent,threads))
    x=load(root/'measurements'/name/'stdout.log');checkpoint(x,out,target,seed,cap,c.get('players',4))
    if parent and parent['frozen_at'] is not None and any(x[k]!=parent[k] for k in ('entries','frozen_at')):raise ValueError('frozen count/marker changed')
    return dict(x,stage_wall_seconds=cost['wall_seconds'],active_seconds=x['elapsed_seconds']-x['save_seconds'])


def export_play(root,c,sup,name,cp,hands,trace_seed):
    players=c.get('players',4)
    if hands % players:raise ValueError('hands must cover complete button rotations')
    policy=root/(name+'-average.gz');sup.stage(name+'-export',[c['binaries']['nplayer_policy'],'export',cp['checkpoint'],cp['sha256'],'average',policy,'--fast-gzip'])
    sup.stage(name+'-audit',[c['python'],'-m','scripts.audit_nplayer_policy_parallel',cp['checkpoint'],policy,'--workers','4','--lookup-out',root/(name+'-mass')])
    audit=load(root/'measurements'/(name+'-audit')/'stdout.log')
    if audit['status']!='passed' or audit['rows']!=cp['entries'] or audit['checkpoint_sha256']!=cp['sha256'] or audit['policy_sha256']!=sha(policy):raise ValueError('export audit binding differs')
    for i in (0,1):
        trace=root/f'{name}-play-{i}.jsonl'
        sup.stage(f'{name}-play-{i}',[c['binaries']['nplayer_policy'],'play',c['tables'],hands,trace_seed,trace,*[str(x) for _ in range(players) for x in (policy,audit['policy_sha256'])]])
    a,b=(root/f'{name}-play-{i}.jsonl' for i in (0,1))
    if sha(a)!=sha(b):raise ValueError('trace reproduction differs')
    buttons=[0]*players
    with a.open() as f:
        header=json.loads(next(f))
        if header['identity']['stacks']!=[10000]*players or header['distinct_policy_instances']!=players or header['loaded_weight_tables']!=1 or header['hands']!=hands:raise ValueError('trace player identity differs')
        for line in f:
            x=json.loads(line)
            if x['button']!=x['hand']%players:raise ValueError('button rotation differs')
            buttons[x['button']]+=1
    if buttons!=[hands//players]*players:raise ValueError('all button positions not represented')
    sup.stage(name+'-replay',[c['python'],'-m','scripts.check_nplayer_policy_replay',a])
    replay=load(root/'measurements'/(name+'-replay')/'stdout.log')
    if replay['status']!='passed' or replay['hands']!=hands or replay['trace_sha256']!=sha(a):raise ValueError('independent replay incomplete')
    return dict(checkpoint=cp,policy=str(policy),policy_sha256=audit['policy_sha256'],audit=audit,
        self_play_coverage=load(root/'measurements'/(name+'-play-0')/'stdout.log'),trace_sha256=sha(a),replay=replay,button_counts=buttons,no_strength_readout=True)


def quote(row,costs,already_spent,available):
    cp=row['checkpoint'];n=cp['counts']['nodes'];entries=cp['entries']
    if n<=0 or entries<=0 or cp['active_seconds']<=0:raise ValueError('invalid cost qualification')
    train_seconds=cp['active_seconds']*50000000/n
    tools=sum(x['wall_seconds'] for x in costs if x['phase'].startswith('cost-') and x['phase']!='cost-train')
    tool_seconds=2*(tools+cp['save_seconds'])*max(1,CAP/entries)
    resume_load=next(x['wall_seconds'] for x in costs if x['phase']=='cost-export')*max(1,CAP/entries)
    fixed=2*max(0,cp['stage_wall_seconds']-cp['elapsed_seconds'])+resume_load
    central=already_spent+train_seconds+tool_seconds+fixed+300
    reserved=already_spent+2*(train_seconds+tool_seconds+fixed)+600
    peak=max(x['sampled_peak_rss_bytes'] for x in costs)
    memory=peak+max(0,CAP-entries)*200
    return dict(status='quoted',central_seconds=central,reserved_seconds=reserved,accepted_planning_seconds=3600,
        forecast_peak_rss_bytes=memory,available_ram_bytes=available,memory_admission=memory+2**30<=available,
        time_admission=reserved<=3600,main_admitted=memory+2**30<=available and reserved<=3600,
        assumptions='Fixed50Mtotal; two endpoint tool/save passes scaled to20Mcap,2xreserve,600sreport. Peak+200bytes/additionalkey,1GiBavailable headroom. Scenarios not bounds; no mature/strength inference.',no_main_started=True)


def validate(c,spec=None):
    expected=spec or dict(players=4,seed=SEED,qual_seed=QUAL_SEED,cost_seed=COST_SEED,trace_seed=2026102240581,main_trace_seed=2026102240611,qualification_hands=24,main_hands=64)
    if c.get('scope',expected)!=expected or c.get('players',4)!=expected['players']:raise ValueError('frozen player scope differs')
    if c['source']!=source_identity() or c['seed']!=expected['seed'] or c['targets']!=list(TARGETS) or c['cap']!=CAP or c['threads']!=10:raise ValueError('frozen scope/source differs')
    for name,digest in TABLES.items():
        if sha(Path(c['tables'])/name)!=digest:raise ValueError('K50 changed')
    for name,path in c['binaries'].items():
        if sha(path)!=c['binary_sha256s'][name]:raise ValueError('native binary changed')
    if sha(c['thermal'])!=c['thermal_sha256'] or sha(c['python'])!=c['python_sha256']:raise ValueError('thermal helper/Python changed')


def qualify(root,tables,python,*,spec=None,quote_fn=None):
    if root.exists():raise FileExistsError('qualification exists; preserve/no retry')
    import psutil
    spec=spec or dict(players=4,seed=SEED,qual_seed=QUAL_SEED,cost_seed=COST_SEED,trace_seed=2026102240581,main_trace_seed=2026102240611,qualification_hands=24,main_hands=64)
    source=source_identity();root.mkdir(parents=True,exist_ok=False)
    env={**os.environ,'PYTHONPATH':str(SOURCE),'CARGO_TARGET_DIR':str(root/'target'),'CARGO_BUILD_JOBS':'4','RUST_TEST_THREADS':'4',
        'RAYON_NUM_THREADS':'10','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    thermal=root/'thermal-state';subprocess.run(['swiftc',str(SOURCE/'scripts/support/m4_thermal_state.swift'),'-o',str(thermal)],check=True)
    sup=Supervisor(root,env,thermal);tick=time.monotonic()
    sup.stage('build',[str(Path.home()/'.cargo/bin/cargo'),'build','--release','--locked','--offline','--manifest-path',SOURCE/'native/hu20-trainer/Cargo.toml',*[x for n in NAMES for x in ('--example',n)]])
    sup.stage('native-tests',[str(Path.home()/'.cargo/bin/cargo'),'test','--release','--locked','--offline','--manifest-path',SOURCE/'native/hu20-trainer/Cargo.toml','--lib'])
    from scripts.check_nplayer_parity import engine_identity
    engine=engine_identity();binaries={n:str(root/'target/release/examples'/n) for n in NAMES}
    c=dict(source=source,scope=spec,players=spec['players'],seed=spec['seed'],targets=list(TARGETS),cap=CAP,threads=10,tables=str(tables),python=str(python),python_sha256=sha(python),engine=engine,
        binaries=binaries,binary_sha256s={n:sha(p) for n,p in binaries.items()},thermal=str(thermal),thermal_sha256=sha(thermal))
    write(root/'config.json',c);sup.config_sha=sha(root/'config.json');validate(c,spec)
    sup.stage('engine-parity',[python,'-m','scripts.check_nplayer_parity','--binary',binaries['nplayer_parity'],'--players',str(spec['players']),'--hands','128','--seed',str(spec['trace_seed']),'--out',root/'engine-parity'])
    a=train(root,c,sup,'fixture100k',100000,spec['qual_seed'],10000)
    one=train(root,c,sup,'fixture100k-one-thread',100000,spec['qual_seed'],10000,threads=1)
    b=train(root,c,sup,'fixture200k-resumed',200000,spec['qual_seed'],10000,parent=a)
    fresh=train(root,c,sup,'fixture200k-fresh',200000,spec['qual_seed'],10000)
    if a['frozen_at'] is None or b['frozen_at'] is None:raise ValueError('fixture did not freeze')
    if a['sha256']!=one['sha256'] or b['sha256']!=fresh['sha256']:raise ValueError('thread/resume checkpoint bytes differ')
    x=export_play(root,c,sup,'fixture-a',a,spec['qualification_hands'],spec['trace_seed']+1);y=export_play(root,c,sup,'fixture-b',b,spec['qualification_hands'],spec['trace_seed']+2)
    if x['audit']['keyset_sha256']!=y['audit']['keyset_sha256']:raise ValueError('fixture frozen membership differs')
    cp=train(root,c,sup,'cost-train',1000000,spec['cost_seed'],CAP);row=export_play(root,c,sup,'cost',cp,spec['qualification_hands'],spec['trace_seed']+3)
    write(root/'cost-qualification.json',row)
    value=(quote_fn or quote)(row,sup.costs,time.monotonic()-tick,psutil.virtual_memory().available);write(root/'quote.json',value)
    write(root/'qualification.json',dict(status='passed',source=source,config_sha256=sha(root/'config.json'),checkpoint_byte_parity=True,
        trace_reproduction_and_replay=True,initial_hands=3*spec['qualification_hands'],reproduction_hands=3*spec['qualification_hands'],engine_parity_hands=128,quote_sha256=sha(root/'quote.json')))
    write(root/'status.json',dict(status='qualified',main_admitted=value['main_admitted'],no_main_started=True))


def run(root,qualification,accepted,*,spec=None):
    if root.exists():raise FileExistsError('main attempt exists; preserve/no retry')
    if accepted!=3600:raise ValueError('fixed one-hour planning allocation required')
    c=load(qualification/'config.json');validate(c,spec);q=load(qualification/'qualification.json');budget=load(qualification/'quote.json')
    if (qualification/'failure.json').exists() or q['status']!='passed' or q['source']!=c['source'] or q['config_sha256']!=sha(qualification/'config.json') or q['quote_sha256']!=sha(qualification/'quote.json') or not budget['main_admitted']:raise ValueError('qualification/quote not admitted')
    root.mkdir(parents=True,exist_ok=False);write(root/'config.json',c);write(root/'launch.json',dict(pid=os.getpid(),epoch=time.time(),source=c['source']['commit'],qualification=str(qualification),quote_sha256=sha(qualification/'quote.json'),accepted_seconds=accepted))
    env={**os.environ,'PYTHONPATH':str(SOURCE),'RAYON_NUM_THREADS':'10','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'};sup=Supervisor(root,env,Path(c['thermal']))
    rows=[];parent=None
    for i,target in enumerate(TARGETS):
        validate(c,spec);cp=train(root,c,sup,f'endpoint{target}-train',target,c['seed'],CAP,parent)
        row=export_play(root,c,sup,f'endpoint{target}',cp,c['scope']['main_hands'],c['scope']['main_trace_seed']+i);rows.append(row);parent=cp
        write(root/'endpoints.json',rows)
    if rows[0]['checkpoint']['frozen_at'] is not None and rows[0]['audit']['keyset_sha256']!=rows[1]['audit']['keyset_sha256']:raise ValueError('frozen membership changed')
    if any(x['returncode'] for x in sup.costs):raise ValueError('failed stage')
    write(root/'results.json',dict(status='complete-cost-only',rows=rows,source=c['source']['commit'],costs=sup.costs,no_strength_readout=True,
        cap_censors_growth=any(x['checkpoint']['frozen_at'] is not None for x in rows),archive='owner-managed pending; originals retained'))
    write(root/'status.json',dict(status='complete',result_sha256=sha(root/'results.json')))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('qualify','run'));p.add_argument('--root',type=Path,required=True)
    p.add_argument('--tables',type=Path);p.add_argument('--qualification',type=Path);p.add_argument('--accepted-seconds',type=int);a=p.parse_args();root=a.root.absolute()
    if sys.platform!='darwin' or subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True).strip()!='Apple M4':raise ValueError('M4 only')
    def interrupted(sig,frame):raise InterruptedError(f'owner signal{sig}')
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,interrupted)
    with (Path.home()/'Local/.hu20-m4-research.lock').open('a+') as normal,Path('/tmp/cfr-four-player-feasibility.lock').open('a+') as own:
        for lock in (normal,own):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if root.exists():raise FileExistsError('attempt exists; no restart or metadata overwrite')
        try:
            if a.mode=='qualify':qualify(root,a.tables.absolute(),Path(sys.executable).absolute())
            else:run(root,a.qualification.absolute(),a.accepted_seconds)
        except BaseException as e:
            if root.exists():write(root/'failure.json',dict(error=repr(e),epoch=time.time(),originals_retained=True,no_automatic_retry=True))
            raise


if __name__=='__main__':main()
