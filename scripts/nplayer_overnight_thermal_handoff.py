"""One owner-authorized checkpoint handoff; never retry failed science."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import struct
import sys
import time

from scripts import nplayer_overnight as campaign
from scripts.overnight_tensorboard import Scalars, string_field

OLD_PID = 358105
SEED = campaign.SEEDS[0]
BOUNDARY = 20_000_000_000
FROZEN = '4cd199a5fef18b24cac188617d767b3f49a422de'
AUTHORIZATION = 'yes please do it on the next completed checkpoint'


def read_events(path):
    # This is compact controller stdout, never a hand/resource trace.
    if path.stat().st_size > 2 * 1024**2:
        raise ValueError('unexpectedly large controller stdout')
    events = []
    for line in path.read_text().splitlines():
        event = campaign.guard.json_event(line)
        if event is not None:
            events.append(event)
    return events


def resume_plan(events):
    saves = [e for e in events if e.get('event') == 'checkpoint']
    if [e['target'] for e in saves] != list(campaign.TARGETS[:2]):
        raise ValueError('handoff requires exactly the completed 10B and 20B saves')
    trained = [e for e in events if e.get('event') == 'trained' and e['target'] == BOUNDARY]
    if len(trained) != 1 or not BOUNDARY <= trained[0]['nodes'] < campaign.TARGETS[-1]:
        raise ValueError('missing checkpoint training counters')
    points = [e['nodes'] for e in events if e.get('event') == 'probe']
    if (len(points) != 5 or not 2.9e9 <= points[0] < 3.1e9 or
            any(abs(a-b) > 1_000_000 for a,b in zip(points[1:],[5e9,10e9,15e9,20e9]))):
        raise ValueError('missing/duplicate pre-handoff monitoring points')
    return dict(checkpoint=saves[-1], trained=trained[0], targets=[campaign.TARGETS[-1]],
                probe_nodes=[25_000_000_000,30_000_000_000])


class ContinuedScalars(Scalars):
    """Append a unique event file while keeping the existing run and time counters."""
    def __init__(self, folder, trained, seed=SEED):
        folder = Path(folder)
        self.path = folder / f'events.out.tfevents.{int(time.time())}.{socket.gethostname()}.{os.getpid()}'
        self.file = self.path.open('xb')
        self.offsets = {f'{seed}/training/{key}':trained[key] for key in ('active_seconds','monitor_seconds')}
        self.record(b'\x09'+struct.pack('<d',time.time())+string_field(3,'brain.Event:2'))

    def add(self, tag, value, step):
        super().add(tag,value+self.offsets.get(tag,0),step)


class ContinuationSupervisor(campaign.Supervisor):
    def __init__(self, *args, origin=None, expected_probe=None, retained_roots=None, cache_parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.origin=origin
        self.expected_probe=expected_probe
        self.retained_roots=retained_roots
        self.cache_parent=cache_parent
        self.external_refresh=0

    def sample(self, process, phase, target):
        if self.origin is not None and time.monotonic()-self.external_refresh>=10:
            # Both attempts share the original allowances, including retained failures.
            roots=self.retained_roots if self.retained_roots is not None else [self.origin]
            self.initial_bytes=-sum(campaign.guard.tree_bytes(p) for p in roots)
            old_cache=self.cache_parent if self.cache_parent is not None else Path(campaign.load(self.origin/'config.json')['cache'])
            self.initial_cache_bytes=-(campaign.guard.tree_bytes(old_cache)-campaign.guard.tree_bytes(self.cache))
            self.external_refresh=time.monotonic()
        row=super().sample(process,phase,target)
        row.update(cpu_stop_c=self.cpu_limit,thermistor15_stop_c=self.thermistor_limit)
        row['swap_guard_enabled']=self.swap_limit_bytes is not None
        return row

    def event(self, line):
        event=campaign.guard.json_event_original(line)
        if (self.seed==SEED and self.expected_probe is not None and event is not None and
                event.get('event')=='probe' and event['nodes']==self.expected_probe['nodes']):
            for key in ('nodes','iteration','blocks','results'):
                if event[key]!=self.expected_probe[key]:
                    raise ValueError('resumed15B monitoring differs from retained trajectory')
            campaign.guard.write(self.root/'resume15b-verified.json',dict(
                status='passed',nodes=event['nodes'],iteration=event['iteration'],
                note='Repeated only to verify resume identity; duplicate TensorBoard point suppressed.'))
            return event
        return super().event(line)


def identity(pid):
    directory = Path('/proc') / str(pid)
    return dict(pid=pid, start_ticks=directory.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
                argv=directory.joinpath('cmdline').read_bytes().split(b'\0')[:-1])


def assert_identity(expected):
    if identity(expected['pid']) != expected:
        raise ValueError('process identity changed; refusing signal')


def await_exit(expected, seconds=15):
    until = time.monotonic()+seconds
    while time.monotonic()<until:
        try:
            actual=identity(expected['pid'])
        except FileNotFoundError:
            return
        if actual != expected:
            return  # Original process is gone; do not signal a reused PID.
        state=Path('/proc',str(expected['pid']),'stat').read_text().rsplit(')',1)[1].split()[0]
        if state=='Z':
            return
        time.sleep(.1)
    raise RuntimeError('original process did not exit; no replacement launched')


def stop_at_checkpoint(root, old, child, events):
    for expected in (child,old):
        assert_identity(expected)
    # pidfds keep all signals tied to these exact processes, even across PID reuse.
    child_fd,old_fd=os.pidfd_open(child['pid']),os.pidfd_open(old['pid'])
    try:
        signal.pidfd_send_signal(child_fd,signal.SIGSTOP)
        signal.pidfd_send_signal(old_fd,signal.SIGSTOP)
        if (root/'failure.json').exists():
            raise RuntimeError('original study failed; no retry authorized')
        plan=resume_plan(events)
        campaign.guard.write(root/'thermal-handoff-interruption.json',dict(
            status='owner-authorized-checkpoint-interruption',at=time.time(),
            authorization=AUTHORIZATION,checkpoint=plan['checkpoint'],trained=plan['trained'],
            old_supervisor_pid=old['pid'],old_child_pid=child['pid'],
            note='Not a successful stage exit. Unsaved work after this checkpoint is discarded; original logs remain.'))
    finally:
        # Never leave either process frozen if handoff validation fails.
        for descriptor in (child_fd,old_fd):
            try:
                signal.pidfd_send_signal(descriptor,signal.SIGTERM)
                signal.pidfd_send_signal(descriptor,signal.SIGCONT)
            except ProcessLookupError:
                pass
        os.close(child_fd);os.close(old_fd)
    await_exit(child);await_exit(old)
    return plan


def continue_campaign(root, plan, origin=None):
    c=campaign.load(root/'config.json');cache=Path(c['cache']);launch=campaign.load(root/'launch.json')
    deadline=launch['epoch']+campaign.MAX_SECONDS
    with Path('/tmp/cfr-nplayer-overnight.lock').open('a') as own,Path('/tmp/cfr-cygnus-exclusive.lock').open('a') as legacy:
        for lock in (own,legacy):
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'failure.json').exists() or time.time()>=deadline:
            raise RuntimeError('failed/expired study; no continuation')
        logs=ContinuedScalars(root/'tensorboard',plan['trained'])
        s=ContinuationSupervisor(root,cache,own.fileno(),deadline-time.time(),logs,
                                 origin=origin,expected_probe=plan.get('expected_probe'))
        s.thermistor_limit=100
        # Charge all existing owned bytes; no resource budget is reset by restart.
        s.initial_bytes=0;s.initial_cache_bytes=0
        # Swap remains telemetry; the owner removed it as a stop condition.
        boundary=plan['checkpoint']['target']
        admission=s.sample(None,'owner-checkpoint-handoff',boundary)
        if origin is not None and (admission['temperatures_c']['Package id 0']>=70 or
                                   admission['temperatures_c']['Thermistor 15']>=80):
            raise RuntimeError('resume thermal admission')
        campaign.guard.json_event_original=campaign.guard.json_event
        campaign.guard.json_event=s.event
        for name,digest in c['source_files'].items():
            if campaign.guard.sha(root/'source'/name)!=digest:
                raise ValueError('frozen source changed')
        native_info=campaign.load(root/'native-binary.json');native=Path(native_info['path'])
        if campaign.guard.sha(native)!=native_info['sha256']:
            raise ValueError('frozen trainer binary changed')
        cp=plan['checkpoint'];cp_path=Path(cp['path'])
        expected_root=origin if origin is not None else root
        if cp_path!=expected_root/f'training-{SEED}'/f'{boundary}.gz' or campaign.guard.sha(cp_path)!=cp['sha256']:
            raise ValueError('checkpoint identity mismatch')
        for key in ('policy','arena'):
            if campaign.guard.sha(c[key])!=c[key+'_sha256']:
                raise ValueError('frozen evaluation binary changed')
        for model in c['anchors'].values():
            for name,hashkey in [('checkpoint','checkpoint_sha256'),('path','sha256')]:
                if campaign.guard.sha(model[name])!=model[hashkey]:
                    raise ValueError('anchor changed')
        s.sample(None,'owner-checkpoint-verified',boundary)
        campaign.guard.write(root/'thermal-handoff-active.json',dict(
            status='active',at=time.time(),supervisor_pid=os.getpid(),cpu_stop_c=s.cpu_limit,
            thermistor15_stop_c=s.thermistor_limit,original_deadline=deadline,
            checkpoint=cp,source_commit=c['source_commit'],amendment_sha256=campaign.guard.sha(__file__),
            budgets='Existing owned storage charged in full; swap guard removed by owner, telemetry retained.',
            swap_guard_enabled=s.swap_limit_bytes is not None))
        campaign.guard.write(root/'status.json',dict(status='owner-checkpoint-handoff',at=time.time(),seed=SEED))
        if origin is None:
            campaign.preserve(root,cache,[f'training-{SEED}',f'measurements/training-{SEED}',
                                        'thermal-handoff-interruption.json','thermal-handoff-active.json'])
        else:
            campaign.preserve(root,cache,['owner-resume-authorization.json','thermal-handoff-active.json'])
        src=root/'source';env=dict(os.environ,RAYON_NUM_THREADS='16',CARGO_BUILD_JOBS='4',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',CARGO_TARGET_DIR=str(root/'target'))
        env['PATH']='/home/dberweger/.cargo/bin:'+env['PATH']
        def stage(name,command,keep_status=False):
            if not keep_status:
                campaign.guard.write(root/'status.json',dict(status=name,at=time.time(),seed=s.seed))
            result=s.execute(name,list(map(str,command)),src,env)
            campaign.preserve(root,cache,['measurements/'+name])
            return result
        models={f'{label}-{seed}':dict(c['anchors'][str(seed)],strategy='average',scope=3)
                for seed in campaign.SEEDS for label in ('final','anchor')}
        for seed in campaign.SEEDS:
            s.seed=seed
            resumed=seed==SEED
            label=f'training-{seed}'+('-thermal100' if resumed else '')
            model=dict(checkpoint=str(cp_path),checkpoint_sha256=cp['sha256']) if resumed else c['anchors'][str(seed)]
            config=dict(seed=seed,threads=16,tables=c['tables'],input=model['checkpoint'],input_sha256=model['checkpoint_sha256'],
                        out=str(root/label),targets=plan['targets'] if resumed else list(campaign.TARGETS),
                        probe_nodes=plan['probe_nodes'] if resumed else [0,5_000_000_000,10_000_000_000,15_000_000_000,20_000_000_000,25_000_000_000,30_000_000_000],
                        probe_blocks=128,probe_root=20261018348001+campaign.SEEDS.index(seed)*10,stop_file=str(root/'STOP'))
            path=root/(label+'-config.json');campaign.guard.write(path,config)
            result=stage(label,[native,path]);campaign.preserve(root,cache,[label,path.name])
            if resumed and plan.get('expected_probe') and not (root/'resume15b-verified.json').exists():
                raise ValueError('missing resumed15B identity verification')
            final=[e for e in result['events'] if e.get('event')=='checkpoint'][-1]
            if final['target']!=campaign.TARGETS[-1]:
                raise ValueError('missing final checkpoint')
            output=root/f'final-{seed}-average.gz'
            stage(f'export-{seed}',[c['policy'],'export',final['path'],final['sha256'],'average',output])
            stage(f'audit-{seed}',[c['python'],'-m','scripts.audit_nplayer_policy',final['path'],output])
            models[f'final-{seed}']=dict(path=str(output),sha256=campaign.guard.sha(output),strategy='average',scope=3,
                                       checkpoint=final['path'],checkpoint_sha256=final['sha256'])
            campaign.preserve(root,cache,[output.name])
        m=dict(arena=c['arena'],arena_sha256=c['arena_sha256'],tables=c['tables'],models=models,smoke=False,cases=campaign.cases())
        campaign.guard.write(root/'evaluation-manifest.json',m)
        stage('final-evaluation',[c['python'],'-m','scripts.nplayer_overnight','batch',root])
        campaign.guard.write(root/'status.json',dict(status='verified-readout-ready',at=time.time()))
        stage('readout',[c['python'],'-m','scripts.nplayer_overnight','read',root],keep_status=True)
        campaign.guard.write(root/'status.json',dict(status='complete',at=time.time()))
        logs.close()
        campaign.preserve(root,cache,['evaluation','tensorboard']+[p.name for p in root.glob('*.json')])


def handoff(root):
    root=Path(root)
    c=campaign.load(root/'config.json')
    if c['source_commit']!=FROZEN or campaign.load(root/'pretraining-freeze.json')['status']!='qualified':
        raise ValueError('unexpected campaign source/qualification')
    old=identity(OLD_PID)
    if old['argv'][-3:]!=[b'scripts.nplayer_overnight',b'run',os.fsencode(root)]:
        raise ValueError('unexpected original supervisor')
    state=campaign.load(root/'status.json')
    if state['status']!=f'training-{SEED}':
        raise ValueError('unexpected active seed/stage')
    children=Path('/proc',str(OLD_PID),'task',str(OLD_PID),'children').read_text().split()
    if len(children)!=1:
        raise ValueError('unexpected original child family')
    child=identity(int(children[0]))
    native=campaign.load(root/'native-binary.json')['path']
    if child['argv']!=[os.fsencode(native),os.fsencode(root/f'training-{SEED}-config.json')]:
        raise ValueError('unexpected original training child')
    stdout=root/'measurements'/f'training-{SEED}'/'stdout.log'
    initial=read_events(stdout)
    if any(e.get('event')=='checkpoint' and e['target']>=BOUNDARY for e in initial):
        raise ValueError('20B already completed before arming; do not rewind')
    campaign.guard.write(root/'thermal-handoff-armed.json',dict(status='armed',at=time.time(),
        helper_pid=os.getpid(),original_supervisor_pid=OLD_PID,seed=SEED,target=BOUNDARY,
        thermistor15_stop_c_before=95,thermistor15_stop_c_after=100,cpu_stop_c=90,
        authorization=AUTHORIZATION,original_deadline=campaign.load(root/'launch.json')['epoch']+campaign.MAX_SECONDS,
        amendment_sha256=campaign.guard.sha(__file__)))
    while time.time()<campaign.load(root/'launch.json')['epoch']+campaign.MAX_SECONDS:
        if (root/'failure.json').exists():
            raise RuntimeError('original campaign failed before checkpoint; no retry')
        assert_identity(old);assert_identity(child)
        if campaign.load(root/'status.json')['status']!=f'training-{SEED}':
            raise RuntimeError('original stage changed before authorized checkpoint')
        events=read_events(stdout)
        if any(e.get('event')=='checkpoint' and e['target']==BOUNDARY for e in events):
            plan=resume_plan(events)  # Validate before sending any signals.
            campaign.guard.write(root/'thermal-handoff-started.json',dict(at=time.time(),checkpoint=plan['checkpoint']))
            plan=stop_at_checkpoint(root,old,child,events)
            continue_campaign(root,plan)
            return
        time.sleep(.25)
    raise RuntimeError('original deadline reached before checkpoint; no extension')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path);args=parser.parse_args()
    owns_handoff=False
    try:
        with (args.root/'thermal-handoff.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if (args.root/'thermal-handoff-armed.json').exists():
                raise RuntimeError('handoff already armed; no duplicate/retry')
            owns_handoff=True
            handoff(args.root)
    except BaseException as error:
        if not owns_handoff:
            raise
        failure=dict(status='failed',error=repr(error),at=time.time())
        if hasattr(error,'resource_sample'):
            failure['resource_sample']=error.resource_sample
        campaign.guard.write(args.root/'thermal-handoff-failure.json',failure)
        # If the original run was interrupted, this is terminal, never a retry loop.
        if (args.root/'thermal-handoff-started.json').exists():
            campaign.guard.write(args.root/'failure.json',failure)
            try:
                cache=Path(campaign.load(args.root/'config.json')['cache'])
                campaign.preserve(args.root,cache,[p.name for p in args.root.iterdir() if p.name not in ('source','target')])
            except BaseException as preservation_error:
                campaign.guard.write(args.root/'preservation-failure.json',dict(error=repr(preservation_error)))
        raise
