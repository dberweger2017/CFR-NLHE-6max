"""Issue399: fixed three-player200BB qualification and cost-only feasibility.

`prepare` records immutable inputs; `run` requires a separate explicit quote
acceptance. Neither command starts full training or a strength comparison.
"""
import argparse
import fcntl
from functools import partial
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

SOURCE = Path(__file__).resolve().parents[1]
SEED = 2026102240001
QUAL_SEED = 2026102240091
TARGETS = (100_000_000, 200_000_000, 500_000_000)
CAP = 250_000_000
BOTS = ('random', 'check-call', 'tight-aggressive', 'pot-pressure')
EXAMPLES = ('nplayer_train', 'nplayer_policy', 'nplayer_arena')
ALLOWANCE = 5400  # Planning allowance, never an elapsed-time kill condition.


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def read(path):
    return json.loads(path.read_text())


def source_pins():
    names = subprocess.check_output(['git', 'ls-files', 'native', 'scripts'], cwd=SOURCE, text=True).splitlines()
    return {name: sha(SOURCE/name) for name in names if (SOURCE/name).is_file()}


def prepare(root, tables, binary_dir, python, build_receipt):
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=SOURCE, text=True).strip():
        raise ValueError('commit the source before preparation')
    build=read(build_receipt)
    current=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip()
    binaries = {name: str((binary_dir/name).resolve()) for name in EXAMPLES}
    if (build.get('status')!='passed' or build.get('source')!=current
            or build.get('native_files')!={k:v for k,v in source_pins().items() if k.startswith('native/')}
            or any(build.get('binary_sha256s',{}).get(name)!=sha(path) for name,path in binaries.items())
            or not build.get('native_library_tests_passed') or not build.get('arena_example_tests_passed')):
        raise ValueError('successful source-bound build/native-test receipt required')
    config = {'format': 'nplayer-bb200-feasibility-v1', 'source': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip(), 'source_files': source_pins(),
        'seed': SEED, 'qualification_seed': QUAL_SEED, 'targets': list(TARGETS), 'max_entries': CAP,
        'stack_bb': 200, 'threads': 16, 'roots_per_seat': 8, 'last_average_street': 3,
        'freeze_at_cap': True, 'fast_gzip': True, 'pruning': False,
        'tables': str(tables.resolve()), 'table_sha256s': {name: sha(tables/name) for name in
            ('flop-k50.bin', 'turn-k50.bin', 'river-k50.bin')},
        'binaries': binaries, 'binary_sha256s': {name: sha(path) for name, path in binaries.items()},
        'build_receipt':str(build_receipt.absolute()),'build_receipt_sha256':sha(build_receipt),
        'python': str(python.absolute()), 'python_sha256': sha(python),
        'planning_allowance_seconds': ALLOWANCE, 'automatic_resource_stops': 'thermal-only-90-100',
        'full_training_admitted': False}
    root.mkdir(parents=True, exist_ok=False)
    write(root/'config.json', config)
    return config


def validate_config(config):
    expected = {'format': 'nplayer-bb200-feasibility-v1', 'seed': SEED, 'qualification_seed': QUAL_SEED,
        'targets': list(TARGETS), 'max_entries': CAP, 'stack_bb': 200, 'threads': 16,
        'roots_per_seat': 8, 'last_average_street': 3, 'freeze_at_cap': True,
        'fast_gzip': True, 'pruning': False, 'planning_allowance_seconds': ALLOWANCE,
        'automatic_resource_stops': 'thermal-only-90-100', 'full_training_admitted': False}
    if any(config.get(k) != value for k, value in expected.items()):
        raise ValueError('frozen200BB scope changed')


def train_command(config, checkpoint, target, *, seed=SEED, threads=16, cap=CAP, parent=None, stack=200):
    command = [config['binaries']['nplayer_train'], '--players', '3', '--stack-bb', str(stack),
        '--small-blind', '50', '--big-blind', '100', '--fast', '--threads', str(threads),
        '--roots-per-seat', '8', '--seed', str(seed), '--nodes', str(target),
        '--last-average-street', '3', '--max-entries', str(cap), '--freeze-at-cap', '--fast-gzip',
        # Required legacy CLI option; finite but practically nonbinding. No time stop is added.
        '--max-seconds', '1e100', '--card-buckets', config['tables'], '--out', str(checkpoint),
        '--telemetry', str(checkpoint)+'.progress.jsonl']
    if parent:
        command += ['--resume', str(parent['checkpoint']), '--resume-sha256', parent['sha256']]
    return command


def validate_checkpoint(summary, checkpoint, target, seed, cap):
    with gzip.open(checkpoint, 'rt') as stream:
        header = json.loads(next(stream))
    identity = header['game']
    if (identity.get('players') != 3 or identity.get('stacks') != [20000]*3
            or identity.get('small_blind') != 50 or identity.get('big_blind') != 100
            or identity.get('menu') != 'min-pot-conditional-jam-v1'
            or identity.get('schema') != 'nplayer-button-live-actor-history-equity-k50-v1'
            or identity.get('utility_unit') != 'big-blind' or identity != summary['identity']):
        raise ValueError('not the frozen200BB game identity')
    if (header['format'] != 'nplayer-cfr-v1' or header['seed'] != seed or header['max_entries'] != cap
            or header['last_average_street'] != 3 or not header['freeze_at_cap']
            or header.get('sampling') != 'path-v1' or header.get('roots_per_seat') != 8
            or header.get('average_rule') != 'opponent-sampled' or 'pruning' in header
            or header['counts'] != summary['counts'] or header['entries'] != summary['entries']
            or header['frozen_at'] != summary['frozen_at'] or summary['stop_reason'] != 'nodes'
            or summary['counts']['nodes'] < target or sha(checkpoint) != summary['sha256']):
        raise ValueError('checkpoint recipe/count/hash/node endpoint differs')
    if header['frozen_at'] is None and any(header['counts'][k] for k in ('discarded_keys','discarded_visits')):
        raise ValueError('updates discarded before membership freeze')
    return header


def quote_from_rows(rows):
    """Local growth scenarios, not a mature-table timing or learning forecast."""
    intervals=[]
    for previous, current in zip([None]+rows, rows):
        added = current['counts']['nodes']-(previous['counts']['nodes'] if previous else 0)
        entries = current['entries']-(previous['entries'] if previous else 0)
        active = current['active_training_seconds']
        if added <= 0 or active <= 0 or not math.isfinite(active):
            raise ValueError('nonpositive interval work or timing')
        intervals.append({'added_nodes': added, 'added_keys': entries, 'keys_per_node': entries/added,
            'active_nodes_per_second': added/active, 'save_seconds': current['save_seconds'],
            'startup_load_hash_other_seconds': current['stage_wall_seconds']-current['elapsed_seconds']})
    slope=intervals[-1]['keys_per_node']; last=rows[-1]
    unconstrained = not any(r.get('frozen_at') is not None for r in rows[-2:])
    return {'intervals': intervals, 'uncapped_local_linear_entries': {str(target): last['entries']+
        slope*max(0,target-last['counts']['nodes']) if unconstrained else None
        for target in (3_000_000_000,10_000_000_000)},
        'last_growth_interval_unconstrained':unconstrained,
        'scope': 'local uncapped linear scenarios only; not bounds, saturation, mature runtime or strength',
        'mature_table_calibration_required': True, 'full_training_admitted': False}


class Supervisor:
    def __init__(self, root, env):
        self.root=root; self.env=env; self.costs=[]

    def stage(self, name, command, *, expected_error=None):
        # Late imports keep planning/tests independent of the pinned poker engine.
        from scripts.run_river_continuation_qualification import thermal, resources, stop
        folder=self.root/'measurements'/name; folder.mkdir(parents=True,exist_ok=False)
        write(self.root/'status.json', {'status':'running','phase':name,'completed_stages':len(self.costs)})
        initial=thermal()
        if (self.root/'STOP').exists():raise RuntimeError('owner STOP')
        if initial['cpu_c']>=90 or initial['thermistor15_c']>=100:
            error=RuntimeError('thermal admission stop');error.resource_sample=initial;raise error
        before=resource.getrusage(resource.RUSAGE_CHILDREN); tick=time.monotonic(); peak=0
        with (folder/'stdout.log').open('x') as stdout, (folder/'stderr.log').open('x') as stderr:
            child=subprocess.Popen(list(map(str,command)),cwd=SOURCE,env=self.env,stdout=stdout,
                stderr=stderr,start_new_session=True)
            try:
                with (self.root/'resources.jsonl').open('a') as log:
                    while child.poll() is None:
                        sample={'phase':name,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                            **thermal(),**resources(child.pid)}
                        peak=max(peak,sample['worker_family_rss_bytes'])
                        log.write(json.dumps(sample)+'\n');log.flush()
                        if (self.root/'STOP').exists():raise RuntimeError('owner STOP')
                        if sample['cpu_c']>=90 or sample['thermistor15_c']>=100:
                            error=RuntimeError('thermal stop');error.resource_sample=sample;raise error
                        time.sleep(2)
                code=child.wait()
            except BaseException:
                stop(child.pid);child.wait();raise
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        row={'phase':name,'command':list(map(str,command)),'returncode':code,
            'wall_seconds':time.monotonic()-tick,'user_cpu_seconds':after.ru_utime-before.ru_utime,
            'system_cpu_seconds':after.ru_stime-before.ru_stime,'sampled_peak_rss_bytes':peak}
        if expected_error is not None:
            row['expected_rejection']=expected_error
            self.costs.append(row);write(self.root/'stage-costs.json',self.costs)
            if code==0 or expected_error not in (folder/'stderr.log').read_text():
                raise ValueError('expected cross-depth rejection did not occur')
            write(folder/'expected-rejection.json',{'status':'passed','expected_error':expected_error})
            return row
        self.costs.append(row);write(self.root/'stage-costs.json',self.costs)
        if code:raise RuntimeError(f'{name} failed with {code}; no automatic retry')
        return row


def train_endpoint(root, config, stage, name,target,*,parent=None,seed=QUAL_SEED,threads=16,cap=10000):
    checkpoint=root/(name+'.gz')
    cost=stage(name,train_command(config,checkpoint,target,parent=parent,seed=seed,threads=threads,cap=cap))
    summary=read(root/'measurements'/name/'stdout.log')
    validate_checkpoint(summary,checkpoint,target,seed,cap)
    if parent:
        if summary['counts']['nodes']<=parent['counts']['nodes']:
            raise ValueError('resume made no progress')
        if parent['frozen_at'] is not None and any(summary[k]!=parent[k] for k in ('entries','frozen_at')):
            raise ValueError('frozen membership count/marker changed')
    active=summary['elapsed_seconds']-summary['save_seconds']
    row={**summary,'checkpoint':str(checkpoint),'checkpoint_bytes':checkpoint.stat().st_size,
        'stage_wall_seconds':cost['wall_seconds'],'active_training_seconds':active}
    write(root/(name+'-summary.json'),row)
    return row

def export_model(root, config, stage, name,model):
    policy=root/(name+'-average.gz')
    stage(name+'-export',[config['binaries']['nplayer_policy'],'export',model['checkpoint'],model['sha256'],
        'average',policy,'--fast-gzip'])
    stage(name+'-audit',[config['python'],'-m','scripts.audit_nplayer_policy_parallel',model['checkpoint'],policy,
        '--workers','8','--lookup-out',root/(name+'-mass')])
    audit=read(root/'measurements'/(name+'-audit')/'stdout.log')
    if audit['status']!='passed' or audit['rows']!=model['entries']:
        raise ValueError('full-row export audit failed')
    return policy,sha(policy),audit

def measure_coverage(root, config, stage, name,policy,digest,blocks,base_root):
    specs=[]
    for bot_index,bot in enumerate(BOTS):
        specs.append({'name':bot,'blocks':blocks,'root':base_root+bot_index,
            'singleton':f'policy={policy}@{digest}','pair':'bot='+bot,
            'trace':str(root/(name+'-'+bot+'.jsonl')),'summary':str(root/(name+'-'+bot+'.json'))})
    for suffix in ('initial','repeat'):
        manifest={'tables':config['tables'],'threads':4,'stack_bb':200,'cases':[
            {**c,'trace':c['trace']+'.'+suffix,'summary':c['summary']+'.'+suffix} for c in specs]}
        write(root/(name+'-'+suffix+'.json'),manifest)
        stage(name+'-'+suffix,[config['binaries']['nplayer_arena'],'batch',root/(name+'-'+suffix+'.json')])
    summaries=[]
    for case in specs:
        initial=Path(case['trace']+'.initial'); repeat=Path(case['trace']+'.repeat')
        if sha(initial)!=sha(repeat):raise ValueError('coverage trace reproduction differs')
        stage(name+'-replay-'+case['name'],[config['python'],'-m','scripts.check_nplayer_policy_replay',initial])
        proof=read(root/'measurements'/(name+'-replay-'+case['name'])/'stdout.log')
        if proof['status']!='passed' or proof['hands']!=blocks*6:raise ValueError('incomplete replay')
        summary=read(Path(case['summary']+'.initial'))
        if summary['hands']!=blocks*6:raise ValueError('incomplete coverage')
        summaries.append({'bot':case['name'],'root':case['root'],'blocks':blocks,'summary':summary,
            'independent_replay':proof,'no_strength_readout':True})
    write(root/(name+'-coverage.json'),summaries)
    return summaries


def execute(root, config, stage):
    trained=partial(train_endpoint,root,config,stage)
    exported=partial(export_model,root,config,stage)
    first=trained('fixture-one',100000,threads=1)
    many=trained('fixture-sixteen',100000)
    resumed=trained('fixture-resume',200000,parent=first)
    fresh=trained('fixture-fresh',200000)
    if first['sha256']!=many['sha256'] or resumed['sha256']!=fresh['sha256']:
        raise ValueError('thread/resume checkpoint identity differs')
    if first['frozen_at'] is None or first['entries']!=resumed['entries']:
        raise ValueError('fixture did not exercise frozen membership')
    stage('reject-cross-depth',train_command(config,root/'forbidden-100bb.gz',300000,
        parent=fresh,seed=QUAL_SEED,cap=10000,stack=100),expected_error='resume configuration mismatch')
    if (root/'forbidden-100bb.gz').exists():raise ValueError('cross-depth resume wrote output')
    left,left_sha,left_audit=exported('fixture-resume',resumed)
    right,right_sha,right_audit=exported('fixture-fresh',fresh)
    if left_sha!=right_sha or left_audit['keyset_sha256']!=right_audit['keyset_sha256']:
        raise ValueError('resume export/key-set identity differs')

    coverage=partial(measure_coverage,root,config,stage)

    coverage('fixture',right,right_sha,2,2026102240901)
    write(root/'qualification.json',{'status':'passed','checkpoint_sha256':fresh['sha256'],
        'policy_sha256':right_sha,'keyset_sha256':right_audit['keyset_sha256'],'cross_depth_refused':True})
    rows=[];previous=None
    for target in TARGETS:
        previous=trained(f'pilot-{target}',target,parent=previous,seed=SEED,cap=CAP)
        rows.append(previous)
    policy,digest,audit=exported('pilot-final',rows[-1])
    covered=coverage('pilot-final',policy,digest,128,2026102240101)
    result={'status':'complete-cost-only','rows':rows,'qualification':read(root/'qualification.json'),
        'final_audit':audit,'coverage':covered,**quote_from_rows(rows),
        'initial_descriptive_hands':4*128*6,'reproduction_descriptive_hands':4*128*6,
        'no_learning_or_strength_gate':True,'no_followup_started':True}
    write(root/'results.json',result)


def run(root, accepted_seconds):
    config=read(root/'config.json');validate_config(config)
    if accepted_seconds!=ALLOWANCE:raise ValueError('explicit acceptance of the published90min pilot quote required')
    if any((root/name).exists() for name in ('launch.json','status.json','failure.json','measurements')):
        raise ValueError('attempt already exists; no restart or retry')
    locks=[]
    try:
        for name in ('/tmp/cfr-cygnus-exclusive.lock','/tmp/cfr-nplayer-bb200-feasibility.lock'):
            lock=open(name,'a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(lock)
        if config['source']!=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip():
            raise ValueError('frozen source differs')
        if subprocess.check_output(['git','status','--porcelain'],cwd=SOURCE,text=True).strip():
            raise ValueError('source checkout modified')
        if config['source_files']!=source_pins():raise ValueError('source bytes differ')
        if sha(config['build_receipt'])!=config['build_receipt_sha256']:raise ValueError('build receipt differs')
        for name,digest in config['binary_sha256s'].items():
            if sha(config['binaries'][name])!=digest:raise ValueError('binary differs')
        for name,digest in config['table_sha256s'].items():
            if sha(Path(config['tables'])/name)!=digest:raise ValueError('K50 input differs')
        if sha(config['python'])!=config['python_sha256']:raise ValueError('Python executable differs')
        write(root/'launch.json',{'pid':os.getpid(),'source':config['source'],'config_sha256':sha(root/'config.json'),
            'epoch':time.time(),'accepted_planning_seconds':accepted_seconds,'no_time_or_memory_or_disk_or_swap_stop':True})
        env={**os.environ,'PYTHONPATH':str(SOURCE),'RAYON_NUM_THREADS':'16','OMP_NUM_THREADS':'1',
            'OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NPLAYER_STOP_FILE':str(root/'STOP')}
        supervisor=Supervisor(root,env)
        supervisor.stage('environment',[config['python'],'-c',
            'import sys; assert sys.version_info[:2]==(3,11); from scripts.check_nplayer_parity import engine_identity; print(engine_identity())'])
        execute(root,config,supervisor.stage)
        write(root/'status.json',{'status':'complete-cost-only','source':config['source'],'stages':len(supervisor.costs)})
    except BaseException as error:
        write(root/'failure.json',{'error':repr(error),'resource_sample':getattr(error,'resource_sample',None),
            'originals_retained':True,'no_automatic_retry':True})
        raise
    finally:
        for lock in locks:lock.close()


def build(root):
    """Owned build/test preparation; does not launch training or copy external inputs."""
    if subprocess.check_output(['git','status','--porcelain'],cwd=SOURCE,text=True).strip():
        raise ValueError('commit source before building')
    root.mkdir(parents=True,exist_ok=False)
    lock=open('/tmp/cfr-cygnus-exclusive.lock','a+')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        env={**os.environ,'CARGO_TARGET_DIR':str(root/'target'),'CARGO_BUILD_JOBS':'4','RAYON_NUM_THREADS':'4'}
        supervisor=Supervisor(root,env)
        common=['cargo','--locked','--manifest-path',str(SOURCE/'native/hu20-trainer/Cargo.toml')]
        # Cargo's verb precedes its options.
        command=['cargo','build',*common[1:],'--release']
        for name in EXAMPLES:command+=['--example',name]
        supervisor.stage('build',command)
        supervisor.stage('native-tests',['cargo','test',*common[1:],'--release','--lib'])
        supervisor.stage('arena-example-tests',['cargo','test',*common[1:],'--release','--example','nplayer_arena'])
        write(root/'build-receipt.json',{'status':'passed','source':subprocess.check_output(
            ['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),
            'native_files':{k:v for k,v in source_pins().items() if k.startswith('native/')},
            'native_library_tests_passed':True,'arena_example_tests_passed':True,
            'binary_sha256s':{name:sha(root/'target/release/examples'/name) for name in EXAMPLES},
            'toolchain':subprocess.check_output(['rustc','-vV'],text=True).splitlines(),
            'costs':supervisor.costs})
        write(root/'status.json',{'status':'build-tests-passed'})
    except BaseException as error:
        write(root/'failure.json',{'error':repr(error),'originals_retained':True,'no_automatic_retry':True})
        raise
    finally:lock.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('build');p.add_argument('--root',type=Path,required=True)
    p=sub.add_parser('prepare');p.add_argument('--root',type=Path,required=True)
    p.add_argument('--tables',type=Path,required=True);p.add_argument('--binary-dir',type=Path,required=True)
    p.add_argument('--python',type=Path,required=True)
    p.add_argument('--build-receipt',type=Path,required=True)
    p=sub.add_parser('run');p.add_argument('--root',type=Path,required=True)
    p.add_argument('--accepted-planning-seconds',type=int,required=True)
    args=parser.parse_args()
    if args.command=='build':build(args.root.absolute())
    elif args.command=='prepare':prepare(args.root.absolute(),args.tables,args.binary_dir,args.python,args.build_receipt)
    else:run(args.root.absolute(),args.accepted_planning_seconds)


if __name__=='__main__':main()
