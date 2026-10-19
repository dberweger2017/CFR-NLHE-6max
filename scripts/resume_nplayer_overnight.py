"""Explicit owner recovery of PR346 from its retained10B checkpoint, once."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys
import time

# Standalone deployment is separate from the frozen campaign source directory.
sys.path.insert(0,str(Path(__file__).parent))
from nplayer_overnight_thermal_handoff import FROZEN, SEED, campaign, continue_campaign, read_events


def recovery_plan(events):
    saves=[e for e in events if e.get('event')=='checkpoint']
    if len(saves)!=1 or saves[0]['target']!=10_000_000_000:
        raise ValueError('recovery requires the sole completed10B checkpoint')
    trained=[e for e in events if e.get('event')=='trained' and e['target']==10_000_000_000]
    expected=[e for e in events if e.get('event')=='probe' and 15_000_000_000<=e['nodes']<15_001_000_000]
    if len(trained)!=1 or len(expected)!=1:
        raise ValueError('missing10B counters or retained15B identity probe')
    return dict(checkpoint=saves[0],trained=trained[0],targets=[20_000_000_000,30_000_000_000],
                probe_nodes=[15_000_000_000,20_000_000_000,25_000_000_000,30_000_000_000],expected_probe=expected[0])


def remaining_quote(config, plan, failed_progress, original_quote, now, deadline):
    nodes=(30_000_000_000-plan['trained']['nodes']+
           sum(30_000_000_000-config['anchor_nodes'][str(seed)] for seed in campaign.SEEDS[1:]))
    rate=min(original_quote['nodes_per_second'],failed_progress['nodes_per_second'])
    # Eight remaining saves retain the original three-times qualification allowance.
    save_allowance=original_quote['save_allowance_seconds']*8/9
    forecast=1.25*(nodes/rate+save_allowance+original_quote['monitoring_seconds'])+3600
    result=dict(remaining_nodes=nodes,nodes_per_second=rate,save_allowance_seconds=save_allowance,
                projected_remaining_seconds=forecast,remaining_seconds=deadline-now,original_deadline=deadline)
    if forecast>deadline-now:
        raise RuntimeError('original-deadline recovery cost admission refused: '+json.dumps(result))
    return result


def resume(origin, root):
    # This third lock prevents duplicate recovery launchers before normal admission.
    with (origin/'owner-resume100.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if root.exists():
            raise ValueError('recovery root already exists; no duplicate/retry')
        c=campaign.load(origin/'config.json')
        if c['source_commit']!=FROZEN or campaign.load(origin/'pretraining-freeze.json')['status']!='qualified':
            raise ValueError('unexpected original source/qualification')
        failure=campaign.load(origin/'failure.json')
        if failure.get('resource_sample',{}).get('temperatures_c',{}).get('Thermistor 15')!=95.0:
            raise ValueError('unexpected original failure')
        events=read_events(origin/f'measurements/training-{SEED}/stdout.log')
        plan=recovery_plan(events)
        deadline=campaign.load(origin/'launch.json')['epoch']+campaign.MAX_SECONDS
        quote=remaining_quote(c,plan,campaign.load(origin/f'measurements/training-{SEED}/progress.json'),
                              campaign.load(origin/'cost-quote.json'),time.time(),deadline)
        root.mkdir()
        cache=Path(c['cache'])/root.name;cache.mkdir(exist_ok=False)
        c=dict(c,cache=str(cache))
        campaign.guard.write(root/'config.json',c)
        for name in ('launch.json','native-binary.json','pretraining-freeze.json'):
            campaign.guard.write(root/name,campaign.load(origin/name))
        for name in ('source','target','tensorboard'):
            (root/name).symlink_to(origin/name,target_is_directory=True)
        campaign.guard.write(root/'owner-resume-authorization.json',dict(
            authorization='Okay let’s continue from10B with the new thermal limit',at=time.time(),
            original_root=str(origin),original_failure=failure,checkpoint=plan['checkpoint'],
            supervisor_pid=os.getpid(),cpu_stop_c=90,thermistor15_stop_c=100,original_deadline=deadline,
            source_commit=FROZEN,entry_sha256=campaign.guard.sha(__file__),
            continuation_sha256=campaign.guard.sha(Path(__file__).with_name('nplayer_overnight_thermal_handoff.py')),
            note='One explicit recovery; original failure remains untouched. No further automatic retry.'))
        campaign.guard.write(root/'recovery-cost-quote.json',quote)
        continue_campaign(root,plan,origin=origin)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('origin',type=Path);p.add_argument('root',type=Path);a=p.parse_args()
    try:
        resume(a.origin,a.root)
    except BaseException as error:
        # Do not mutate a pre-existing root belonging to another launcher.
        if a.root.exists() and (a.root/'owner-resume-authorization.json').exists():
            own=campaign.load(a.root/'owner-resume-authorization.json')['supervisor_pid']==os.getpid()
            if own:
                failure=dict(error=repr(error),at=time.time())
                if hasattr(error,'resource_sample'):failure['resource_sample']=error.resource_sample
                campaign.guard.write(a.root/'failure.json',failure)
                try:
                    cache=Path(campaign.load(a.root/'config.json')['cache'])
                    campaign.preserve(a.root,cache,[p.name for p in a.root.iterdir() if p.name not in ('source','target','tensorboard')])
                except BaseException as preserve_error:
                    campaign.guard.write(a.root/'preservation-failure.json',dict(error=repr(preserve_error)))
        raise
