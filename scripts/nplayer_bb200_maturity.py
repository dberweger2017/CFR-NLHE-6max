"""Issue401: one approved PR400 checkpoint continuation to1B, then stop."""
import argparse
import fcntl
import math
import os
from pathlib import Path
import subprocess
import time

from scripts import nplayer_bb200_feasibility as pilot

SOURCE=Path(__file__).resolve().parents[1]
TARGET=1_000_000_000
PARENT_NODES=500_027_427
PARENT_SHA='704e35dd04d8290fc49c9d4505f6371bf0e8a50200e185c8881807ce727af625'
PRIOR_CONFIG_SHA='36c4e69cd780dcdcac61279ca3eceea2603230b7f4fe9182857efc88b2e57b28'
ROOTS=[2026102240201+i for i in range(4)]


def validate_parent(parent):
    if (parent['counts']['nodes']!=PARENT_NODES or parent['sha256']!=PARENT_SHA
            or parent['identity']['players']!=3 or parent['identity']['stacks']!=[20000]*3
            or parent['entries']!=159384070 or parent['frozen_at'] is not None
            or parent['stop_reason']!='nodes' or parent['counts']['discarded_keys']
            or parent['counts']['discarded_visits']):
        raise ValueError('not the verified unfrozen PR400 parent')


def check_prior(prior):
    main=prior/'main-v1';config=pilot.read(main/'config.json');pilot.validate_config(config)
    if pilot.sha(main/'config.json')!=PRIOR_CONFIG_SHA:
        raise ValueError('PR400 frozen config changed')
    if any((prior/name).exists() for name in ('preparation/failure.json','build-v1/failure.json','main-v1/failure.json')):
        raise ValueError('failed prior work cannot authorize continuation')
    if (pilot.read(prior/'preparation/status.json')['status']!='complete'
            or pilot.read(main/'status.json')['status']!='complete-cost-only'
            or pilot.read(main/'qualification.json')['status']!='passed'):
        raise ValueError('complete qualified prior run required')
    for stage in pilot.read(main/'stage-costs.json'):
        if stage['returncode']!=0 and not (stage['phase']=='reject-cross-depth' and stage['returncode']==2
                and stage.get('expected_rejection')=='resume configuration mismatch'):
            raise ValueError('prior stage failed')
    build=pilot.read(prior/'build-v1/build-receipt.json')
    native={k:v for k,v in pilot.source_pins().items() if k.startswith('native/')}
    if (native!=build['native_files'] or not build['native_library_tests_passed']
            or not build['arena_example_tests_passed']):
        raise ValueError('qualified native sources/tests differ')
    result=pilot.read(main/'results.json');parent=result['rows'][-1];validate_parent(parent)
    proof=pilot.read(prior/'publication-v1/verified-readback.json')
    if (proof['status']!='passed' or result['final_audit']['status']!='passed'
            or result['final_audit']['checkpoint_sha256']!=PARENT_SHA
            or result['final_audit']['rows']!=parent['entries']):
        raise ValueError('prior complete export/readback proof differs')
    checkpoint=main/'pilot-500000000.gz'
    if parent['checkpoint']!=str(checkpoint) or pilot.sha(checkpoint)!=PARENT_SHA:
        raise ValueError('parent checkpoint bytes/path differ')
    for name,digest in config['binary_sha256s'].items():
        if pilot.sha(config['binaries'][name])!=digest:raise ValueError('qualified native binary differs')
    for name,digest in config['table_sha256s'].items():
        if pilot.sha(Path(config['tables'])/name)!=digest:raise ValueError('pinned K50 differs')
    if pilot.sha(config['python'])!=config['python_sha256']:raise ValueError('managed Python differs')
    return config,parent


def prepare(root, prior):
    if subprocess.check_output(['git','status','--porcelain'],cwd=SOURCE,text=True).strip():
        raise ValueError('committed source required')
    config,parent=check_prior(prior)
    config={**config,'format':'nplayer-bb200-maturity-v1','targets':[TARGET],
        'source':subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),
        'source_files':pilot.source_pins(),'prior_root':str(prior),'parent':parent,
        'prior_config_sha256':PRIOR_CONFIG_SHA,'prior_readback_sha256':pilot.sha(prior/'publication-v1/verified-readback.json'),
        'coverage_roots':ROOTS,'coverage_blocks':128,'no_further_cost_pilot_or_extension':True,
        'same_qualified_native_binaries':True}
    root.mkdir(parents=True,exist_ok=False);pilot.write(root/'config.json',config)


def validate_config(config):
    expected={'format':'nplayer-bb200-maturity-v1','targets':[TARGET],'seed':pilot.SEED,
        'qualification_seed':pilot.QUAL_SEED,'max_entries':pilot.CAP,'stack_bb':200,'threads':16,
        'roots_per_seat':8,'last_average_street':3,'freeze_at_cap':True,'fast_gzip':True,
        'pruning':False,'planning_allowance_seconds':5400,'automatic_resource_stops':'thermal-only-90-100',
        'full_training_admitted':False,'coverage_roots':ROOTS,'coverage_blocks':128,
        'no_further_cost_pilot_or_extension':True,'same_qualified_native_binaries':True,
        'prior_config_sha256':PRIOR_CONFIG_SHA}
    if any(config.get(k)!=v for k,v in expected.items()):raise ValueError('fixed1B scope differs')
    validate_parent(config['parent'])


def continuation_metrics(row,parent):
    added=row['counts']['nodes']-parent['counts']['nodes']
    active=row['active_training_seconds']
    if (added<=0 or active<=0 or not math.isfinite(active) or row['counts']['nodes']<TARGET
            or not parent['entries']<=row['entries']<=pilot.CAP
            or row['frozen_at'] is not None and row['entries']!=pilot.CAP):
        raise ValueError('incomplete continuation or invalid capacity/timing')
    return {'added_nodes':added,'added_entries':row['entries']-parent['entries'],
        'active_training_seconds':active,'active_nodes_per_second':added/active,
        'marginal_retained_keys_per_node':(row['entries']-parent['entries'])/added,
        'frozen_at':row['frozen_at'],'retained_capacity_fraction':row['entries']/pilot.CAP,
        'growth_after_freeze_is_censored':row['frozen_at'] is not None}


def run(root, accepted_seconds):
    config=pilot.read(root/'config.json');validate_config(config)
    if accepted_seconds!=5400:raise ValueError('owner-approved90minute allocation required')
    if any((root/name).exists() for name in ('launch.json','status.json','failure.json','measurements')):
        raise ValueError('attempt already exists; no retry')
    locks=[]
    try:
        for name in ('/tmp/cfr-cygnus-exclusive.lock','/tmp/cfr-nplayer-bb200-maturity.lock'):
            lock=open(name,'a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(lock)
        if (config['source']!=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip()
                or subprocess.check_output(['git','status','--porcelain'],cwd=SOURCE,text=True).strip()
                or config['source_files']!=pilot.source_pins()):raise ValueError('frozen controller source differs')
        prior=Path(config['prior_root']);old,parent=check_prior(prior)
        if (parent!=config['parent'] or old['binaries']!=config['binaries']
                or old['binary_sha256s']!=config['binary_sha256s']
                or old['python']!=config['python'] or old['tables']!=config['tables']
                or pilot.sha(prior/'publication-v1/verified-readback.json')!=config['prior_readback_sha256']):
            raise ValueError('qualified handoff changed')
        pilot.write(root/'launch.json',{'pid':os.getpid(),'epoch':time.time(),'source':config['source'],
            'config_sha256':pilot.sha(root/'config.json'),'parent_checkpoint_sha256':PARENT_SHA,
            'targets':[TARGET],'accepted_planning_seconds':5400,'corrected_reserved_seconds':4179.263974015036,
            'native_binaries_reused':config['binary_sha256s'],'no_other_resource_stops':True})
        env={**os.environ,'PYTHONPATH':str(SOURCE),'RAYON_NUM_THREADS':'16','OMP_NUM_THREADS':'1',
            'OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NPLAYER_STOP_FILE':str(root/'STOP')}
        supervisor=pilot.Supervisor(root,env)
        row=pilot.train_endpoint(root,config,supervisor.stage,'continuation-1b',TARGET,
            parent=parent,seed=pilot.SEED,cap=pilot.CAP)
        metrics=continuation_metrics(row,parent)
        policy,digest,audit=pilot.export_model(root,config,supervisor.stage,'final-1b',row)
        coverage=pilot.measure_coverage(root,config,supervisor.stage,'final-1b',policy,digest,128,ROOTS[0])
        result={'status':'complete-cost-only','parent':parent,'endpoint':row,'interval':metrics,
            'audit':audit,'coverage':coverage,'initial_hands':3072,'reproduction_hands':3072,
            'stopped_at_fixed_endpoint':True,'no_strength_readout':True,'no_followup_started':True,
            'full_training_admitted':False,'no_further_cost_pilot_authorized':True}
        pilot.write(root/'results.json',result)
        pilot.write(root/'status.json',{'status':'complete-cost-only','source':config['source'],
            'epoch':time.time(),'stages':len(supervisor.costs)})
    except BaseException as error:
        pilot.write(root/'failure.json',{'error':repr(error),'epoch':time.time(),
            'resource_sample':getattr(error,'resource_sample',None),'originals_retained':True,'no_automatic_retry':True})
        raise
    finally:
        for lock in locks:lock.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--root',type=Path,required=True);a.add_argument('--prior',type=Path,required=True)
    a=sub.add_parser('run');a.add_argument('--root',type=Path,required=True)
    a.add_argument('--accepted-planning-seconds',type=int,required=True)
    args=p.parse_args()
    if args.command=='prepare':prepare(args.root.absolute(),args.prior.absolute())
    else:run(args.root.absolute(),args.accepted_planning_seconds)


if __name__=='__main__':main()
