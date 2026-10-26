"""PR436: one fixed small policy and a guarded M4-only river request panel."""
import argparse
import fcntl
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import tomllib

from scripts.nplayer_four_player_feasibility import SOURCE, Supervisor, TABLES, sample, sha, write
from scripts.qualify_river_second_to_act_m4 import verify_panel, test_receipt as native_test_receipt
from scripts.river_model_panel_protocol import BASELINE, MAIN, PANEL_SHA, PREFLIGHT, SEED, first_actor, quote, reentry_matches, signature, verify_batch_pair


def read(path):
    return json.loads(Path(path).read_text())


def frozen_source(path):
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=path, text=True).strip():
        raise ValueError('dirty source snapshot')
    files = subprocess.check_output(['git', 'ls-files'], cwd=path, text=True).splitlines()
    return dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=path, text=True).strip(),
                files={n:sha(path/n) for n in files if (path/n).is_file()})


def validate_inputs(c):
    for name, digest in TABLES.items():
        if sha(Path(c['tables'])/name) != digest:
            raise ValueError('K50 input changed')
    if sha(c['python']) != c['python_sha256'] or sha(c['thermal']) != c['thermal_sha256']:
        raise ValueError('runtime/thermal changed')
    for name, digest in c.get('binary_sha256', {}).items():
        if sha(c['binaries'][name]) != digest:
            raise ValueError('binary changed')


def validate_fixture(header, summary):
    g = header['game']
    if (header['format'] != 'nplayer-cfr-v1' or header['players'] != 3
            or g['stacks'] != [10000]*3 or g['small_blind'] != 50 or g['big_blind'] != 100
            or g['schema'] != 'nplayer-button-live-actor-history-equity-k50-v1'
            or header['seed'] != SEED or header['max_entries'] != 1000000
            or not header['freeze_at_cap'] or header['roots_per_seat'] != 8
            or header['last_average_street'] != 3 or header['sampling'] != 'path-v1'
            or header['average_rule'] != 'opponent-sampled' or 'pruning' in header
            or header.get('traverser_admission', False) or header.get('opponent_pot_raise')
            or summary['stop_reason'] != 'nodes' or summary['counts']['nodes'] < 25000000
            or header['entries'] != summary['entries'] or header['counts'] != summary['counts']
            or g != summary['identity']):
        raise ValueError('fixture recipe/identity/endpoint changed')


def baseline_manifest(baseline, worker):
    profile=tomllib.loads((baseline/'native/hu20-trainer/Cargo.toml').read_text())['profile']['release']
    if profile != {'opt-level':3,'lto':'thin','codegen-units':1}:
        raise ValueError('baseline release profile changed')
    return ('[package]\nname="river-m4-baseline-worker"\nversion="0.0.0"\nedition="2021"\n'
            '[dependencies]\nhu20-trainer={path='+json.dumps(str(baseline/'native/hu20-trainer'))+'}\n'
            'serde_json={version="1",features=["float_roundtrip"]}\n'
            '[[bin]]\nname="river_m4_baseline"\npath='+json.dumps(str(worker))+'\n'
            '[profile.release]\nopt-level=3\nlto="thin"\ncodegen-units=1\n')


def baseline_lock(original):
    text=original.read_text()
    if any(p['name']=='river-m4-baseline-worker' for p in tomllib.loads(text)['package']):
        raise ValueError('unexpected wrapper in historical lockfile')
    # Add only the owned root package, retaining every historical dependency pin.
    # --locked host builds validate this without resolving unused target crates.
    return text+'\n[[package]]\nname = "river-m4-baseline-worker"\nversion = "0.0.0"\ndependencies = [\n "hu20-trainer",\n "serde_json",\n]\n'


class Worker:
    def __init__(self, command, folder):
        self.folder = folder
        self.stderr = (folder/'worker.stderr.log').open('x')
        self.wire = (folder/'wire.jsonl').open('x')
        self.tick = time.monotonic()
        self.p = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=self.stderr, text=True, bufsize=1)
        try:
            self.ready = self.receive()
        except BaseException:
            self.close(failed=True)
            raise
        self.startup = time.monotonic()-self.tick
        if self.ready.get('status') != 'ready':
            self.close(failed=True)
            raise ValueError('worker failed startup')

    def receive(self):
        line = self.p.stdout.readline(16*1024*1024+1)
        if not line or len(line) > 16*1024*1024:
            raise ValueError('worker EOF/oversized response; retain stderr/wire')
        x = json.loads(line, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON '+x)))
        self.wire.write(json.dumps(dict(direction='response',value=x),allow_nan=False)+'\n');self.wire.flush()
        return x

    def request(self, value):
        self.wire.write(json.dumps(dict(direction='request',value=value),allow_nan=False)+'\n');self.wire.flush()
        tick = time.monotonic()
        self.p.stdin.write(json.dumps(value,allow_nan=False)+'\n');self.p.stdin.flush()
        x = self.receive()
        return x,time.monotonic()-tick

    def close(self, failed=False):
        tick = time.monotonic()
        if self.p.poll() is None:
            try:self.p.stdin.close()
            except BrokenPipeError:pass
            if failed:
                self.p.terminate()
            try:
                self.p.wait(timeout=5 if failed else None)
            except subprocess.TimeoutExpired:
                self.p.kill();self.p.wait()
        self.wire.close();self.stderr.close();self.p.stdout.close()
        if not failed and self.p.returncode:
            raise ValueError('worker nonzero exit')
        return time.monotonic()-tick


def batch(root, phase, version, repeat):
    c = read(root/'config.json');validate_inputs(c)
    if sha(root/'fixture-average.gz') != c['policy_sha256'] or sha(root/'mass/receipt.json') != c['mass_sha256']:
        raise ValueError('audited policy/mass receipt changed')
    rows = [json.loads(line) for line in (root/'panel.jsonl').read_text().splitlines()]
    if sha(root/'panel.jsonl') != PANEL_SHA:
        raise ValueError('panel changed')
    ids = (PREFLIGHT if phase == 'preflight' else MAIN)[version]
    folder = root/f'{phase}-{version}-{repeat}';folder.mkdir(exist_ok=False)
    worker = Worker([c['binaries'][version],c['tables'],str(root/'fixture-average.gz'),c['policy_sha256'],
                     str(root/'mass'),c['mass_sha256']],folder)
    result = dict(phase=phase,version=version,repeat=repeat,ready=worker.ready,
                  startup_wall_seconds=worker.startup,roots=[])
    if (worker.ready['model_sha256'] != c['policy_sha256'] or worker.ready['mass_receipt_sha256'] != c['mass_sha256']
            or worker.ready['rows'] != c['fixture_entries']):
        worker.close(failed=True);raise ValueError('ready model/mass/count binding differs')
    try:
        for i in ids:
            observation = rows[i]['request'];context=dict(hand_id=f'm4-river-panel/{i}')
            begin,t = worker.request(dict(mode='retained-begin',observation=observation,**context))
            entry = dict(id=i,entry=rows[i]['entry'],begin=begin,begin_seconds=t,
                         reentry=None,release=None,reentry_seconds=0.,release_seconds=0.)
            # Preserve the exact first divergent response before any validation can fail.
            result['roots'].append(entry);write(folder/'partial.json',result)
            if begin['status'] == 'ok':
                r = begin['result'];s = r['session'];context['handle'] = s['handle']
                for cov in r.get('coverage', []):
                    if cov.get('mass_unknown') != 0:
                        raise ValueError('missing original-mass diagnostics')
                if r.get('lookup_tag') == 3:
                    raise ValueError('fallback original mass unknown')
                again,at = worker.request(dict(mode='retained-continue',observation=observation,**context))
                entry.update(reentry=again,reentry_seconds=at);write(folder/'partial.json',result)
                reentry_matches(begin,again)
                release,rt = worker.request(dict(mode='retained-release',**context))
                entry.update(release=release,release_seconds=rt)
                if release.get('status') != 'ok' or release.get('result') != dict(released=True):
                    raise ValueError('retained release failed')
            elif begin['status'] != 'unsupported' or begin.get('reason') not in (
                    'public action sequence has zero modeled likelihood',
                    'three-seat compatible chance mass below supported conditioning floor',
                    'unreachable node or excessive strategy cells'):
                raise ValueError('unexpected unsupported request: '+str(begin))
            write(folder/'partial.json',result)
            write(root/'request-progress.json',dict(phase=phase,version=version,repeat=repeat,
                                                    completed=len(result['roots']),total=len(ids)))
        result['shutdown_seconds'] = worker.close()
    except BaseException:
        worker.close(failed=True)
        raise
    write(folder/'results.json',result)


def verify_phase(root, phase):
    inventory = PREFLIGHT if phase == 'preflight' else MAIN
    proof = dict(phase=phase,reproduction={},first_actor_profiles=0,first_actor_classifications=0)
    for version in ('current','baseline'):
        a,b = [read(root/f'{phase}-{version}-{i}/results.json') for i in (0,1)]
        proof['reproduction'][version] = verify_batch_pair(a,b,inventory[version])
    current = {r['id']:r for r in read(root/f'{phase}-current-0/results.json')['roots']}
    baseline = read(root/f'{phase}-baseline-0/results.json')['roots']
    for row in baseline:
        if row['id'] not in current:
            continue  # Nonshared preflight controls are covered by the complete main panel.
        a,b = current[row['id']]['begin'],row['begin']
        if first_actor(a) != first_actor(b):
            write(root/'first-divergence.json',dict(phase=phase,id=row['id'],current=a,baseline=b))
            raise ValueError('first-to-act version parity mismatch')
        has_profile = a.get('result',{}).get('session',{}).get('binding',{}).get('profile_sha256') is not None
        proof['first_actor_profiles' if has_profile else 'first_actor_classifications'] += 1
    write(root/f'{phase}-verified.json',proof)
    return proof


def summary(root, c, sup, tick, proof):
    current = read(root/'main-current-0/results.json')['roots']
    def quantiles(values):
        if not values:return dict(n=0)
        v=sorted(values)
        def q(p):
            pos=(len(v)-1)*p;i=int(pos);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(pos-i)
        return dict(n=len(v),p50=q(.5),p90=q(.9),p95=q(.95),max=v[-1])
    groups={k:[] for k in ('installed','fallback','unsupported')};compact=[]
    for row in current:
        r=row['begin'].get('result',{});s=r.get('session',{})
        kind='unsupported' if row['begin']['status']!='ok' else 'installed' if s['installed_search'] else 'fallback'
        groups[kind].append(row['begin_seconds'])
        compact.append(dict(id=row['id'],entry=row['entry'],classification=kind,
                            reason=s.get('fallback_reason',row['begin'].get('reason')),
                            begin_seconds=row['begin_seconds'],reentry_seconds=row['reentry_seconds'],
                            actions=r.get('actions'),probabilities=r.get('probabilities'),
                            produced_root_strategy=r.get('produced_root_strategy'),coverage=r.get('coverage'),
                            lookup_tag=r.get('lookup_tag'),quality=r.get('quality'),target_bb=r.get('target_bb'),
                            sweeps=r.get('sweeps'),nodes=r.get('nodes'),timings=r.get('timings'),
                            solver_memory_bytes=r.get('solver_memory_bytes'),binding=s.get('binding')))
    result=dict(status='complete',scope='small-history-policy engineering; no strength/adoption claim',
                source=c['source']['commit'],baseline_source=BASELINE,config_sha256=sha(root/'config.json'),
                policy_sha256=c['policy_sha256'],mass_sha256=c['mass_sha256'],panel_sha256=PANEL_SHA,
                native_tests=native_test_receipt(root/'measurements/native-tests/stdout.log'),
                stage_costs=sup.costs,controller_wall_seconds=time.monotonic()-tick,
                primary_root_count=48,declared_root_requests=144,
                first_actor_proof=proof,latency_seconds={k:quantiles(v) for k,v in groups.items()},
                installed_second_to_act=sum(r['classification']=='installed' and r['entry']!=0 for r in compact),
                roots=compact,quote=read(root/'quote.json'),no_new_arena_hands=True,no_bb128_work=True)
    write(root/'results.json',result)
    write(root/'status.json',dict(status='complete',result_sha256=sha(root/'results.json')))


def run(root, baseline, tables, thermal, preparation):
    if root.exists():raise FileExistsError('attempt exists; preserve/no retry')
    if platform.system()!='Darwin' or 'Apple M4' not in subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True):
        raise ValueError('M4 only')
    if 'AC Power' not in subprocess.check_output(['pmset','-g','batt'],text=True):raise ValueError('AC required')
    if shutil.disk_usage(root.parent).free<20*2**30:raise ValueError('20GiB actual free required')
    root.mkdir();tick=time.monotonic()
    try:
        with (Path.home()/'Local/.hu20-m4-research.lock').open('a+') as normal,(root/'.study.lock').open('a+') as owned:
            for f in (normal,owned):fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            admission=sample(root,thermal);write(root/'admission.json',admission)
            if admission['available_ram_bytes']<5*2**30:raise ValueError('4GiB family plus1GiB headroom unavailable')
            c=dict(source=frozen_source(SOURCE),baseline=frozen_source(baseline),baseline_path=str(baseline),
                   tables=str(tables),python=sys.executable,python_sha256=sha(sys.executable),
                   thermal=str(thermal),thermal_sha256=sha(thermal),admission=admission,
                   preparation=str(preparation),preparation_sha256=sha(preparation),
                   normal_inode=os.fstat(normal.fileno()).st_ino,study_inode=os.fstat(owned.fileno()).st_ino,
                   seed=SEED,target_nodes=25000000,max_entries=1000000)
            if c['baseline']['commit']!=BASELINE:raise ValueError('wrong baseline snapshot')
            write(root/'config.json',c);validate_inputs(c)
            env={**os.environ,'PYTHONPATH':str(SOURCE),'CARGO_TARGET_DIR':str(root/'target'),
                 'CARGO_BUILD_JOBS':'2','RUST_TEST_THREADS':'2','RAYON_NUM_THREADS':'1',
                 'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NPLAYER_STOP_FILE':str(root/'STOP')}
            sup=Supervisor(root,env,thermal)
            def bind():
                write(root/'config.json',c);sup.config_sha=sha(root/'config.json')
            sup.stage('thermal-build',['swiftc',SOURCE/'scripts/support/m4_thermal_state.swift','-o',root/'thermal-state'])
            c['thermal']=str(root/'thermal-state');c['thermal_sha256']=sha(c['thermal']);sup.thermal=Path(c['thermal']);bind()
            cargo=str(Path.home()/'.cargo/bin/cargo');manifest=SOURCE/'native/hu20-trainer/Cargo.toml'
            flags=['--release','--locked','--offline','--manifest-path',manifest]
            sup.stage('native-tests',[cargo,'test',*flags,'--lib','--','--test-threads=2'])
            sup.stage('example-tests',[cargo,'test',*flags,'--example','nplayer_river_panel','--example','river_live','--','--test-threads=2'])
            sup.stage('python-tests',[sys.executable,'-m','unittest','tests.test_river_model_panel_m4',
                      'tests.test_river_second_to_act_m4','tests.test_river_arena_expectation','tests.test_river_whole_hand_pilot'])
            names=('nplayer_train','nplayer_policy','river_live','nplayer_river_panel')
            sup.stage('build',[cargo,'build',*flags,*[a for name in names for a in ('--example',name)]])
            wrapper=root/'baseline-worker';wrapper.mkdir()
            text=baseline_manifest(baseline,SOURCE/'native/hu20-trainer/examples/river_live.rs')
            (wrapper/'Cargo.toml').write_text(text)
            (wrapper/'Cargo.lock').write_text(baseline_lock(baseline/'native/hu20-trainer/Cargo.lock'))
            sup.stage('baseline-lock',[cargo,'metadata','--offline','--locked','--no-deps','--format-version','1','--manifest-path',wrapper/'Cargo.toml'])
            def packages(path):
                x=tomllib.loads(path.read_text())['package']
                return {(a['name'],a['version'],a.get('source'),a.get('checksum')) for a in x if a['name']!='river-m4-baseline-worker'}
            if packages(wrapper/'Cargo.lock')!=packages(baseline/'native/hu20-trainer/Cargo.lock'):
                raise ValueError('baseline dependency versions/checksums changed')
            c['baseline_adapter']={n:sha(wrapper/n) for n in ('Cargo.toml','Cargo.lock')};bind()
            sup.stage('baseline-build',[cargo,'build','--release','--locked','--offline','--manifest-path',wrapper/'Cargo.toml'])
            c['binaries']={n:str(root/'target/release/examples'/n) for n in names}
            c['binaries'].update(current=c['binaries']['river_live'],baseline=str(root/'target/release/river_m4_baseline'))
            c['binary_sha256']={k:sha(p) for k,p in c['binaries'].items()};bind()
            sup.stage('panel-generate',[c['binaries']['nplayer_river_panel'],root/'panel.jsonl'])
            verify_panel(root/'panel.jsonl')
            if sha(root/'panel.jsonl')!=PANEL_SHA:raise ValueError('fixed panel digest differs')
            cp=root/'fixture.gz'
            sup.stage('fixture-train',[c['binaries']['nplayer_train'],'--players','3','--stack-bb','100',
                      '--small-blind','50','--big-blind','100','--key-schema','history','--fast','--threads','2',
                      '--roots-per-seat','8','--seed',SEED,'--nodes','25000000','--last-average-street','3',
                      '--max-entries','1000000','--freeze-at-cap','--fast-gzip','--max-seconds','1e100',
                      '--card-buckets',tables,'--out',cp,'--telemetry',root/'training-progress.jsonl'])
            trained=read(root/'measurements/fixture-train/stdout.log')
            with gzip.open(cp,'rt') as f:header=json.loads(next(f))
            validate_fixture(header,trained)
            if sha(cp)!=trained['sha256']:raise ValueError('checkpoint SHA differs')
            sup.stage('fixture-export',[c['binaries']['nplayer_policy'],'export',cp,trained['sha256'],'average',root/'fixture-average.gz','--fast-gzip'])
            sup.stage('fixture-audit',[sys.executable,'-m','scripts.audit_nplayer_policy_parallel',cp,
                      root/'fixture-average.gz','--workers','1','--lookup-out',root/'mass'])
            audit=read(root/'mass/receipt.json')
            if audit['status']!='passed' or audit['rows']!=trained['entries'] or audit['policy_sha256']!=sha(root/'fixture-average.gz'):
                raise ValueError('full-row audit binding differs')
            c.update(policy_sha256=audit['policy_sha256'],mass_sha256=sha(root/'mass/receipt.json'),
                     fixture_entries=trained['entries'],checkpoint_sha256=trained['sha256'])
            # Fixed solver limits plus actual rows; generous allocator/K50/scratch reserve.
            forecast=max(4*2**30,2*2**30+trained['entries']*512+4096*1081*64+2000000*64)
            now=sample(root,Path(c['thermal']))
            if forecast>6*2**30 or now['available_ram_bytes']<forecast+2**30:
                raise ValueError('model/solver forecast plus headroom unavailable')
            c['forecast_family_bytes']=forecast;bind()
            for phase in ('preflight','main'):
                for version in ('current','baseline'):
                    for repeat in (0,1):
                        validate_inputs(c)
                        sup.stage(f'{phase}-{version}-{repeat}',[sys.executable,'-m','scripts.river_model_panel_m4',
                                  'batch',root,'--phase',phase,'--version',version,'--repeat',repeat])
                proof=verify_phase(root,phase)
                if phase=='preflight':
                    batches=[read(root/f'preflight-{v}-{i}/results.json') for v in ('current','baseline') for i in (0,1)]
                    available=sample(root,Path(c['thermal']))['available_ram_bytes']
                    if sha(preparation)!=c['preparation_sha256']:raise ValueError('preparation receipt changed')
                    prep=read(preparation)['wall_seconds']
                    value=quote(batches,time.monotonic()-tick+prep,available,forecast)
                    value['disk_admitted']=shutil.disk_usage(root).free>=12*2**30
                    value['main_admitted'] &= value['disk_admitted']
                    write(root/'quote.json',value)
                    if not value['main_admitted']:
                        write(root/'status.json',dict(status='preflight-complete-budget-or-resource-not-admitted',no_main_started=True))
                        return
            validate_inputs(c)
            for path,key in ((SOURCE,'source'),(baseline,'baseline')):
                if frozen_source(path)!=c[key]:raise ValueError('source snapshot changed')
            if sha(cp)!=c['checkpoint_sha256'] or sha(root/'fixture-average.gz')!=c['policy_sha256']:
                raise ValueError('fixture bytes changed')
            summary(root,c,sup,tick,proof)
    except BaseException as e:
        write(root/'failure.json',dict(error=repr(e),epoch=time.time(),automatic_retry=False,preserve=True))
        write(root/'status.json',dict(status='failed'))
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('run');a.add_argument('root',type=Path);a.add_argument('--baseline',type=Path,required=True)
    a.add_argument('--tables',type=Path,required=True);a.add_argument('--thermal',type=Path,required=True)
    a.add_argument('--preparation',type=Path,required=True)
    b=sub.add_parser('batch');b.add_argument('root',type=Path);b.add_argument('--phase',choices=('preflight','main'),required=True)
    b.add_argument('--version',choices=('current','baseline'),required=True);b.add_argument('--repeat',type=int,choices=(0,1),required=True)
    x=p.parse_args()
    if x.command=='run':run(x.root.resolve(),x.baseline.resolve(),x.tables.resolve(),x.thermal.resolve(),x.preparation.resolve())
    else:batch(x.root.resolve(),x.phase,x.version,x.repeat)


if __name__=='__main__':main()
