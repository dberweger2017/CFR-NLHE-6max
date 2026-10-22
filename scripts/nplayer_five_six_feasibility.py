"""One combined five/six-player M4 feasibility allocation; no strength readout."""
import argparse
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from scripts import nplayer_four_player_feasibility as core

REFERENCE=core.SOURCE/'docs/reports/nplayer-four-player-feasibility/results.json'
REFERENCE_SHA='7e0f51220a34b547719e06d7af72727c9c02e195f070dc0a4f95881d98cefa61'
SPECS={p:dict(players=p,seed=2026102300001+p*1000,qual_seed=2026102300091+p*1000,
    cost_seed=2026102300092+p*1000,trace_seed=2026102300081+p*1000,
    main_trace_seed=2026102300011+p*1000,qualification_hands=30,main_hands=60) for p in (5,6)}


def quote_for(players):
    def component(row,costs,already_spent,available):
        if core.sha(REFERENCE)!=REFERENCE_SHA:raise ValueError('PR406 cost reference changed')
        prior=core.load(REFERENCE);factor=players/4
        ref={c['phase'].removeprefix('endpoint50000000-'):c['wall_seconds'] for c in prior['costs'] if c['phase'].startswith('endpoint50000000-')}
        fresh={c['phase'].removeprefix('cost-'):c['wall_seconds'] for c in costs if c['phase'].startswith('cost-')}
        cp=row['checkpoint'];entries=cp['entries'];nodes=cp['counts']['nodes']
        if entries<=0 or nodes<=0 or cp['active_seconds']<=0:raise ValueError('invalid qualification costs')
        rate=nodes/cp['active_seconds']
        old=prior['rows'][-1]['checkpoint'];old_added=old['counts']['nodes']-prior['rows'][0]['checkpoint']['counts']['nodes']
        train=max(50000000/rate,50000000*old['active_seconds']/old_added*factor)
        # Scale row-processing work, but model/K50 startup only once per process.
        tools=sum(max(ref[k]*factor,fresh[k]*(core.CAP/entries if k in ('export','audit') else 2))
            for k in ('export','audit','play-0','play-1','replay'))
        residual=max((ref['train']-old['active_seconds'])*factor,
            (cp['stage_wall_seconds']-cp['active_seconds'])*core.CAP/entries)
        central=train+2*(tools+residual)
        peak=max(c['sampled_peak_rss_bytes'] for c in costs)+max(0,core.CAP-entries)*200
        return dict(status='quoted',players=players,central_seconds=central,reserved_seconds=2*central,
            qualification_seconds=already_spent,forecast_peak_rss_bytes=peak,available_ram_bytes=available,
            memory_admission=peak+2**30<=available,time_admission=2*central<=3600,
            main_admitted=peak+2**30<=available and 2*central<=3600,no_main_started=True,
            reference_sha256=REFERENCE_SHA,assumptions='Two capped endpoints; max(PR406 20M-row work times players/4, new cost-only row work); fixed startup separated; 2x work reserve; 200B/additional key plus 1GiB headroom. Not a mature forecast.')
    return component


def combined_quote(components,elapsed):
    central=elapsed+sum(q['central_seconds'] for q in components)+300
    reserved=elapsed+sum(q['reserved_seconds'] for q in components)+600
    return dict(status='quoted',central_seconds=central,reserved_seconds=reserved,accepted_planning_seconds=3600,
        qualification_seconds=elapsed,components=components,main_admitted=reserved<=3600 and all(q['memory_admission'] for q in components),
        no_main_started=True,reference_sha256=REFERENCE_SHA,sequential_sizes=True)


def qualify(root,tables):
    tick=time.monotonic();components=[]
    for p,spec in SPECS.items():
        child=root/f'players{p}'
        core.qualify(child,tables,Path(sys.executable).absolute(),spec=spec,quote_fn=quote_for(p))
        components.append(core.load(child/'quote.json'))
    q=combined_quote(components,time.monotonic()-tick);core.write(root/'quote.json',q)
    core.write(root/'qualification.json',dict(status='passed',source=core.source_identity(),quote_sha256=core.sha(root/'quote.json'),
        children={str(p):dict(path=str(root/f'players{p}'),qualification_sha256=core.sha(root/f'players{p}'/'qualification.json')) for p in SPECS}))
    core.write(root/'status.json',dict(status='qualified',main_admitted=q['main_admitted'],no_main_started=True))


def validate_qualification(qualification):
    q=core.load(qualification/'qualification.json');budget=core.load(qualification/'quote.json')
    if (qualification/'failure.json').exists() or q['status']!='passed' or q['source']!=core.source_identity() or q['quote_sha256']!=core.sha(qualification/'quote.json') or not budget['main_admitted']:
        raise ValueError('combined source/qualification/quote not admitted')
    for p,spec in SPECS.items():
        child=qualification/f'players{p}'
        if q['children'][str(p)]['path']!=str(child) or q['children'][str(p)]['qualification_sha256']!=core.sha(child/'qualification.json'):
            raise ValueError('child qualification receipt changed')
        if (child/'failure.json').exists():raise ValueError('failed child qualification')
        core.validate(core.load(child/'config.json'),spec)
    return q,budget


def run(root,qualification):
    q,budget=validate_qualification(qualification)
    import psutil
    available=psutil.virtual_memory().available
    if any(c['forecast_peak_rss_bytes']+2**30>available for c in budget['components']):raise ValueError('current memory admission declined')
    core.write(root/'launch.json',dict(pid=os.getpid(),epoch=time.time(),source=q['source']['commit'],
        quote_sha256=core.sha(qualification/'quote.json'),accepted_seconds=3600,qualification=str(qualification)))
    rows={}
    os.environ['NPLAYER_STOP_FILE']=str(root/'STOP')
    for p,spec in SPECS.items():
        if (root/'STOP').exists():raise RuntimeError('ownerSTOP')
        core.write(root/'status.json',dict(status='running',players=p,child=str(root/f'players{p}')))
        core.run(root/f'players{p}',qualification/f'players{p}',3600,spec=spec)
        rows[str(p)]=core.load(root/f'players{p}'/'results.json')
    core.write(root/'results.json',dict(status='complete-cost-only',source=q['source']['commit'],players=rows,
        no_strength_readout=True,archive='owner-managed pending; originals retained'))
    core.write(root/'status.json',dict(status='complete',result_sha256=core.sha(root/'results.json')))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('qualify','run'))
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--tables',type=Path)
    parser.add_argument('--qualification',type=Path);parser.add_argument('--accepted-seconds',type=int)
    a=parser.parse_args();root=a.root.absolute()
    if sys.platform!='darwin' or subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True).strip()!='Apple M4':raise ValueError('M4 only')
    if 'AC Power' not in subprocess.check_output(['pmset','-g','batt'],text=True):raise ValueError('AC required')
    if a.mode=='run' and a.accepted_seconds!=3600:raise ValueError('fixed combined one-hour planning allocation required')
    def stop(sig,frame):raise InterruptedError(f'owner signal{sig}')
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,stop)
    with (Path.home()/'Local/.hu20-m4-research.lock').open('a+') as normal,Path('/tmp/cfr-five-six-feasibility.lock').open('a+') as own:
        for lock in (normal,own):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if root.exists():raise FileExistsError('attempt exists; preserve/no retry')
        root.mkdir(parents=True,exist_ok=False)
        os.environ['NPLAYER_STOP_FILE']=str(root/'STOP')
        try:
            if a.mode=='qualify':qualify(root,a.tables.absolute())
            else:run(root,a.qualification.absolute())
        except BaseException as e:
            core.write(root/'failure.json',dict(error=repr(e),epoch=time.time(),originals_retained=True,no_automatic_retry=True));raise


if __name__=='__main__':main()
