"""Qualify PR335 and measure bb128 scaling without reading poker outcomes."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import time

from scripts import run_nplayer_storage_benchmark as guard

SEED = 2026101833500
THREADS = [1, 2, 4, 8, 16]


def legacy_holder():
    path = Path('/tmp/cfr-cygnus-exclusive.lock')
    s = path.stat()
    key = f'{os.major(s.st_dev):02x}:{os.minor(s.st_dev):02x}:{s.st_ino}'
    for line in Path('/proc/locks').read_text().splitlines():
        fields = line.split()
        if key in fields:
            pid = int(fields[4])
            command = (Path('/proc') / str(pid) / 'cmdline').read_bytes().replace(b'\0', b' ').decode()
            return dict(pid=pid, command=command)
    return None


class Qualification(guard.Supervisor):
    def sample(self, process, phase, target):
        row = super().sample(process, phase, target)
        if time.monotonic() - self.started >= 90 * 60:
            raise RuntimeError('qualification ninety-minute fail-safe')
        return row


def report(result):
    return next(e for e in reversed(result['events']) if 'stop_reason' in e)


def run(root):
    config = json.loads((root/'config.json').read_text())
    guard.BUDGET = 10_000_000_000
    with Path('/tmp/cfr-pr335-compute.lock').open('a') as own, \
            Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as legacy:
        fcntl.flock(own, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            fcntl.flock(legacy, fcntl.LOCK_EX | fcntl.LOCK_NB)
            background = None
        except BlockingIOError:
            background = legacy_holder()
            expected = '/home/dberweger/hu200-capacity-20261015/planning/archive_terminal_closeout_20261018.py run'
            if background is None or expected not in background['command']:
                raise RuntimeError('unknown legacy lock holder; cannot admit')
        supervisor = Qualification(root, own.fileno(), cpus=range(16))
        first = supervisor.sample(None, 'admission', 0)
        if first['temperatures_c']['Package id 0'] >= 70 or first['temperatures_c']['Thermistor 15'] >= 80:
            raise RuntimeError('temperature admission refused')
        guard.write(root/'admission.json', dict(pid=os.getpid(), initial_sample=first,
            source_commit=config['source_commit'], legacy_holder=background,
            owner_override='Owner authorizes PR335 compute/all16 threads while PR301 archives; do not disturb archive',
            own_lock='/tmp/cfr-pr335-compute.lock'))
        env = dict(os.environ, RAYON_NUM_THREADS='16', CARGO_BUILD_JOBS='4',
            OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
            NPLAYER_K50_TABLES=config['tables'], CARGO_TARGET_DIR=str(root/'target'))
        env['PATH']='/home/dberweger/.cargo/bin:'+env['PATH']
        env['CARGO_ENCODED_RUSTFLAGS']='\x1f'.join([
            '--remap-path-prefix='+str(root)+'=qualification',
            '--remap-path-prefix=/home/dberweger/.cargo=cargo-home'])
        receipts=[]
        for arm in ['baseline', 'candidate']:
            src=root/'sources'/arm
            supervisor.cpus=set(range(8))
            manifest=str(src/'native/hu20-trainer/Cargo.toml')
            supervisor.execute('build-'+arm, ['cargo','build','--release','--locked','--offline',
                '--manifest-path',manifest,'--example','nplayer_train','--example','nplayer_policy',
                '--example','nplayer_arena'], src, env)
            if arm=='candidate':
                supervisor.execute('native-tests', ['cargo','test','--release','--locked','--offline',
                    '--manifest-path',manifest,'--lib','--','--test-threads=1'],src,env)
            dest=root/'binaries'/arm;dest.mkdir(parents=True,exist_ok=False)
            for name in ['nplayer_train','nplayer_policy','nplayer_arena']:
                shutil.copy2(root/'target/release/examples'/name,dest/name)
            receipts.append(dict(arm=arm,binaries={p.name:guard.sha(p) for p in dest.iterdir()}))
        guard.write(root/'binary-receipts.json',receipts)
        (root/'outputs').mkdir()
        def train(label,arm,nodes,threads,fast=False,resume=None):
            supervisor.cpus=set(range(threads))
            current=dict(env,RAYON_NUM_THREADS=str(threads))
            out=root/'outputs'/(label+'.gz')
            command=[str(root/'binaries'/arm/'nplayer_train'),'--players','3','--stack-bb','20',
                '--seed',str(SEED),'--nodes',str(nodes),'--last-average-street','3',
                '--max-entries','150000000','--max-seconds','600','--card-buckets',config['tables'],
                '--out',str(out)]
            if arm=='candidate':command+=['--threads',str(threads)]
            if fast:command+=['--fast','--roots-per-seat','8']
            if resume:command+=['--resume',str(resume),'--resume-sha256',guard.sha(resume)]
            result=supervisor.execute(label,command,root,current)
            r=report(result)
            if r['stop_reason']!='nodes' or r['counts']['nodes']<nodes:
                raise ValueError(label+' did not reach its node endpoint')
            return out,r,result
        _,a,_=train('production-baseline','baseline',10_000_000,1)
        _,b,_=train('production-candidate','candidate',10_000_000,1)
        if a['sha256']!=b['sha256']:raise ValueError('production checkpoint identity mismatch')
        small=[]
        for t in THREADS:
            out,r,_=train('identity-fast-'+str(t),'candidate',3_000_000,t,True)
            small.append(r['sha256'])
        if len(set(small))!=1:raise ValueError('fast thread identity mismatch')
        prefix,_,_=train('resume-prefix','candidate',1_500_000,4,True)
        _,resumed,_=train('resume-identity','candidate',3_000_000,3,True,prefix)
        if resumed['sha256']!=small[0]:raise ValueError('cross-thread exact resume mismatch')
        pilot,_,_=train('pilot-100m','candidate',100_000_000,16,True)
        rows=[]
        for i,t in enumerate(THREADS+THREADS[::-1]):
            _,r,result=train(f'scaling-{i:02d}-{t}t','candidate',120_000_000,t,True,pilot)
            seconds=r['elapsed_seconds']-r['save_seconds']
            rows.append(dict(threads=t,repeat=i//5+1,training_seconds=seconds,
                actual_nodes=r['counts']['nodes'],entries=r['entries'],iteration=r['iteration'],
                sha256=r['sha256'],wall_seconds=result['wall_seconds'],cpu_seconds=result['cpu_seconds'],
                sampled_peak_rss_bytes=max(result['sampled_peak_rss_by_phase'].values()),
                save_seconds=r['save_seconds']))
            if len({x['sha256'] for x in rows})!=1:raise ValueError('scaling checkpoint identity mismatch')
            guard.write(root/'scaling-progress.json',rows)
        medians={t:sum(x['training_seconds'] for x in rows if x['threads']==t)/2 for t in THREADS}
        best=min(medians.values());chosen=min(t for t in THREADS if medians[t]<=best*1.03)
        guard.write(root/'qualification-passed.json',dict(status='passed',rows=rows,
            production_sha256=a['sha256'],fast_identity_sha256=small[0],
            median_training_seconds=medians,selected_threads=chosen,legacy_archive_at_admission=background))
        guard.write(root/'status.json',dict(status='qualification-passed',selected_threads=chosen))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path)
    root=parser.parse_args().root.resolve()
    try:run(root)
    except BaseException as error:
        guard.write(root/'failure.json',dict(error=repr(error),at=time.time()));raise


if __name__=='__main__':main()
