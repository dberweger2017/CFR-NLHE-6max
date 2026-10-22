"""Publish closed PR402 metadata only; never train, play, select or alter models."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def publish(receipt_path, prior_path, out):
    receipt=json.loads(receipt_path.read_text())
    for name,body in receipt['files'].items():
        if hashlib.sha256(body.encode()).hexdigest()!=receipt['sha256'][name]:
            raise ValueError('changed compact receipt: '+name)
    def read(name):return json.loads(receipt['files'][name])
    result=read('completion-v1/results.json');prior=json.loads(prior_path.read_text())
    proof=receipt['verified_readback'];endpoint=result['endpoint'];audit=result['audit']
    if (result['status']!='complete-cost-only' or read('completion-v1/status.json')['status']!='complete-cost-only'
            or audit['status']!='passed' or audit['rows']!=endpoint['entries']
            or endpoint['counts']['nodes']!=1000008098 or endpoint['entries']!=250002537
            or result['training_repeated'] or not result['no_strength_readout']
            or result['initial_hands']!=3072 or result['reproduction_hands']!=3072
            or proof['status']!='passed' or len(proof['trace_readbacks'])!=4):
        raise ValueError('incomplete or changed final evidence')
    if any(name=='completion-v1/failure.json' for name in receipt['files']):raise ValueError('completion failure')
    if read('main-v1/failure.json')['error']!="ValueError('incomplete continuation or invalid capacity/timing')":
        raise ValueError('unexpected original failure')
    main=read('main-v1/stage-costs.json');post=read('completion-v1/stage-costs.json')
    if len(main)!=1 or main[0]['phase']!='continuation-1b' or len(post)!=8 or any(s['returncode'] for s in main+post):
        raise ValueError('stage completion barrier failed')
    for name,digest in [('checkpoint',endpoint['sha256']),('policy',audit['policy_sha256'])]:
        if proof[name]['sha256']!=digest or proof[name]['actual_sha256']!=digest:
            raise ValueError('closed artifact readback differs')
    for row,pin in zip(result['coverage'],proof['trace_readbacks']):
        replay=row['independent_replay'];summary=row['summary']
        if (row['bot']!=pin['bot'] or replay['status']!='passed' or replay['hands']!=768
                or pin['initial_sha256']!=pin['repeat_sha256']
                or pin['initial_sha256']!=summary['trace_sha256'] or replay['trace_sha256']!=pin['initial_sha256']):
            raise ValueError('trace/replay barrier differs')
    loads=play=0
    for row in result['coverage']:
        for suffix in ('initial','repeat'):
            summary=read('completion-v1/final-1b-'+row['bot']+'.json.'+suffix)
            if summary['hands']!=768 or summary['trace_sha256']!=row['summary']['trace_sha256']:
                raise ValueError('coverage counts/reproduction differ')
            loads+=summary['load_seconds'];play+=summary['play_seconds']
    by_phase={s['phase']:s for s in post}
    summed=sum(s['wall_seconds'] for s in main+post)
    elapsed=read('completion-v1/status.json')['epoch']-read('main-v1/launch.json')['epoch']
    costs={'stage_wall_sum_seconds':summed,'launch_to_complete_seconds':elapsed,
        'outside_measured_stages_seconds':elapsed-summed,
        'outside_stage_scope':'controller failure/correction/handoff, validation/hash and interstage overhead; not pure programming or load time',
        'stage_child_cpu_seconds':sum(s['user_cpu_seconds']+s['system_cpu_seconds'] for s in main+post),
        'active_training_seconds':endpoint['active_training_seconds'],'save_seconds':endpoint['save_seconds'],
        'training_process_seconds':endpoint['stage_wall_seconds'],
        'training_load_hash_startup_other_seconds':endpoint['stage_wall_seconds']-endpoint['elapsed_seconds'],
        'export_seconds':by_phase['final-1b-export']['wall_seconds'],
        'audit_seconds':by_phase['final-1b-audit']['wall_seconds'],
        'coverage_processes_seconds':sum(by_phase['final-1b-'+p]['wall_seconds'] for p in ('initial','repeat')),
        'coverage_load_seconds':loads,'coverage_play_seconds':play,
        'independent_replay_seconds':sum(s['wall_seconds'] for s in post if '-replay-' in s['phase']),
        'stages':main+post,'resources':receipt['resources'],
        'cpu_scope':'sum of disjoint stage-child CPU, includes their descendant CPU once; excludes controller Python, setup/tests, later publication/archive/readback',
        'resources_scope':'approximately2s sampled entire stage worker families, not exact high-water bounds; host swap attribution unknown'}
    # A prospective MODEL campaign, not an acceptance quote or authorization.
    rate=result['interval']['active_nodes_per_second']
    remaining=(10_000_000_000-endpoint['counts']['nodes'])/rate
    active=remaining+2*(sum(r['active_training_seconds'] for r in prior['rows'])+endpoint['active_training_seconds']+remaining)
    # This run loaded the smaller500M parent, not the capped1B model.
    # Explicitly scale that residual by checkpoint bytes; no mature load measured.
    load_scale=endpoint['checkpoint_bytes']/result['parent']['checkpoint_bytes']
    components={'active_training':active,'four_capped_resume_load_hash_other':4*costs['training_load_hash_startup_other_seconds']*load_scale,
        'six_checkpoint_saves':6*endpoint['save_seconds'],'six_average_exports':6*costs['export_seconds'],
        'six_full_row_audits':6*costs['audit_seconds'],'metadata_allowance':300}
    central=sum(components.values());reserve=3*active+2*(central-active)+300
    proposal={'status':'proposal-only-not-authorized','candidate_capacity':250000000,
        'capacity_verdict':'defensible bounded research candidate, incomplete coverage; not release-qualified',
        'lineages':{'existing_seed':2026102240001,'existing_parent_sha256':endpoint['sha256'],'additional_independent_fresh_seeds':2,'new_seeds':'freeze before launch'},
        'per_lineage_checkpoints':[3000000000,10000000000],
        'within_lineage_membership_must_match':True,'no_further_cost_pilot':True,
        'components_seconds':components,'model_campaign_central_seconds':central,'model_campaign_reserved_seconds':reserve,
        'assumptions':'Current pooled added-node rate4.355M/s held constant;2 fresh0->1B active costs fromPR400+402;4 resume load/hash residuals scaled by capped/parent checkpoint byte ratio (mature training load unmeasured);6saves,exports,audits at this endpoint cost. Conditional scenarios, not guarantees.',
        'resume_load_checkpoint_byte_scale':load_scale,
        'reserve_formula':'3xactive+2xeveryothercomponent+300s',
        'not_in_quote':['strength acceptance hands/reproduction/replay','200BB binary inference conversion/parity','optional staging/archive'],
        'model_storage_retained_bytes_rough':6*(endpoint['checkpoint_bytes']+proof['policy']['bytes']),
        'acceptance':{'gates':'same30 one-sided family95 Bonferroni gates as v0.6 at200BB:24absolute script/mixed profit>0,3own-checkpoint oriented contrasts>0,3cyclic continuation lower>-5BB/100',
            'counts_roots_effects_variances_pass_chances':'must be frozen and quoted before new confirming deals;100BB effects do not establish200BB power',
            'fixed_adverse_panels_retained':True,'not_a_launch_ready_acceptance_budget':True},
        'full_training_or_acceptance_started':False,'automatic_extension_retry_or_release':False}
    out.mkdir(parents=True,exist_ok=False)
    def write(name,value):(out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    (out/'results.json').write_text(receipt['files']['completion-v1/results.json'])
    write('costs.json',costs);write('verified-readback.json',proof);write('campaign-proposal.json',proposal)
    write('provenance.json',{'science_source':read('main-v1/launch.json')['source'],
        'completion_source':read('completion-v1/launch.json')['source'],'config':read('main-v1/config.json'),
        'original_controller_failure':read('main-v1/failure.json'),'original_outer_failure':read('failure.json'),
        'completion_status':read('completion-v1/status.json'),'file_sha256s':receipt['sha256'],
        'receipt_sha256':hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        'prior_result_sha256':hashlib.sha256(prior_path.read_bytes()).hexdigest(),
        'originals_retained':True,'cloud_acceptance':'pending; consult archival status separately'})
    with (out/'coverage.csv').open('w') as f:
        writer=csv.writer(f,lineterminator='\n');writer.writerow(['endpoint','bot','street','focal_decisions','missing','missing_fraction','independent_blocks','hand_instances','deal_root'])
        for label,rows in [('500M',prior['coverage']),('1B',result['coverage'])]:
            for row in rows:
                for i,street in enumerate(('preflop','flop','turn','river')):
                    n=row['summary']['decisions_by_identity_street'][0][i];miss=row['summary']['misses_by_identity_street'][0][i]
                    writer.writerow([label,row['bot'],street,n,miss,miss/n if n else None,row['blocks'],row['summary']['hands'],row['root']])
    with (out/'table-audit.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=['street',*audit['by_street'][0]],lineterminator='\n');writer.writeheader()
        for street,row in zip(('preflop','flop','turn','river'),audit['by_street']):writer.writerow({'street':street,**row})
    print(json.dumps({'stage_wall_seconds':summed,'elapsed_seconds':elapsed,'model_campaign_central_seconds':central,'model_campaign_reserved_seconds':reserve},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('receipt',type=Path)
    parser.add_argument('prior',type=Path);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    publish(args.receipt,args.prior,args.out)


if __name__=='__main__':main()
