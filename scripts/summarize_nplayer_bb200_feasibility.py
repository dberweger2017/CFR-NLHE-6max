"""Publish PR400 compact receipts and a prospective allocation; never run poker."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt',type=Path);parser.add_argument('supplement',type=Path)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    receipt=json.loads(args.receipt.read_text());proof=json.loads(args.supplement.read_text())
    for name,body in receipt['files'].items():
        if hashlib.sha256(body.encode()).hexdigest()!=receipt['sha256'][name]:
            raise ValueError('changed compact receipt: '+name)
    def read(name):return json.loads(receipt['files'][name])
    result=read('main-v1/results.json');config=read('main-v1/config.json')
    assert result['status']=='complete-cost-only' and proof['status']=='passed'
    assert not any(name.endswith('failure.json') for name in receipt['files'])
    assert read('preparation/status.json')['status']=='complete'
    assert read('main-v1/status.json')['status']=='complete-cost-only'
    assert config['source']=='735e3d3b5f32de5913f50686cb3a861c18734037'
    assert config['targets']==[100000000,200000000,500000000] and config['stack_bb']==200
    assert read('main-v1/qualification.json')['status']=='passed'
    assert read('main-v1/qualification.json')['cross_depth_refused']
    for name in ('preparation/stage-costs.json','build-v1/stage-costs.json','main-v1/stage-costs.json'):
        for stage in read(name):
            assert stage['returncode']==0 or (stage['phase']=='reject-cross-depth' and stage['returncode']==2
                and stage.get('expected_rejection')=='resume configuration mismatch')
    assert len(proof['endpoint_readbacks'])==3 and proof['expected_cross_depth_rejection']['forbidden_output_absent']
    for target,row,pin in zip(config['targets'],result['rows'],proof['endpoint_readbacks']):
        assert row['counts']['nodes']>=target and row['stop_reason']=='nodes'
        assert row['sha256']==pin['sha256'] and row['checkpoint_bytes']==pin['bytes']
        assert row['identity']['stacks']==[20000]*3 and row['frozen_at'] is None
        assert row['counts']['discarded_keys']==row['counts']['discarded_visits']==0
    audit=result['final_audit'];assert audit['status']=='passed' and audit['rows']==result['rows'][-1]['entries']
    assert audit['policy_sha256']==proof['policy']['sha256'] and audit['zero_keys_sha256']==proof['zero_mass']['sha256']
    assert result['initial_descriptive_hands']==result['reproduction_descriptive_hands']==3072
    assert result['no_learning_or_strength_gate'] and not result['full_training_admitted']
    for group,blocks in (('fixture',2),('pilot-final',128)):
        rows=proof['coverage'][group];assert len(rows)==4
        for row in rows:
            assert row['initial_sha256']==row['repeat_sha256']
            assert all(s['hands']==blocks*6 and s['trace_sha256']==row['initial_sha256']
                for s in row['summaries'].values())
    for row in result['coverage']:
        assert row['independent_replay']['status']=='passed' and row['independent_replay']['hands']==768
        assert row['independent_replay']['trace_sha256']==row['summary']['trace_sha256']
    args.out.mkdir(parents=True,exist_ok=False)
    def write(name,value):(args.out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    (args.out/'results.json').write_text(receipt['files']['main-v1/results.json'])
    stages=read('main-v1/stage-costs.json');by_phase={s['phase']:s for s in stages}
    coverage=proof['coverage']['pilot-final']
    loads=sum(row['summaries'][p]['load_seconds'] for row in coverage for p in ('initial','repeat'))
    play=sum(row['summaries'][p]['play_seconds'] for row in coverage for p in ('initial','repeat'))
    prepare=read('preparation/stage-costs.json')
    costs={'whole_elapsed_seconds':read('preparation/status.json')['epoch']-read('preparation/launch.json')['epoch'],
        'whole_child_cpu_seconds':sum(s['user_cpu_seconds']+s['system_cpu_seconds'] for s in prepare),
        'main_stages':stages,'build_stages':read('build-v1/stage-costs.json'),'outer_preparation_stages':prepare,
        'resources':receipt['resources'],'active_training_seconds':sum(r['active_training_seconds'] for r in result['rows']),
        'checkpoint_save_seconds':sum(r['save_seconds'] for r in result['rows']),
        'training_process_wall_seconds':sum(r['stage_wall_seconds'] for r in result['rows']),
        'export_wall_seconds':by_phase['pilot-final-export']['wall_seconds'],
        'audit_wall_seconds':by_phase['pilot-final-audit']['wall_seconds'],
        'coverage_native_wall_seconds':sum(by_phase['pilot-final-'+p]['wall_seconds'] for p in ('initial','repeat')),
        'coverage_native_load_seconds':loads,'coverage_native_play_seconds':play,
        'cpu_accounting':'Whole outer child CPU includes nested build/worker CPU; do not add inner CPU again. Excludes later publication/readback.',
        'qualification_counts':{'initial_hands':48,'reproduced_hands':48},
        'final_coverage_counts':{'initial_hands':3072,'reproduced_hands':3072}}
    write('costs.json',costs);write('verified-readback.json',proof)
    write('provenance.json',{'source':config['source'],'config':config,'authorization':read('owner-authorization.json'),
        'supervisor':read('supervisor-launch.json'),'dependencies':read('dependencies.json'),
        'file_sha256s':receipt['sha256'],'receipt_sha256':hashlib.sha256(args.receipt.read_bytes()).hexdigest(),
        'supplement_sha256':hashlib.sha256(args.supplement.read_bytes()).hexdigest(),
        'originals_retained':True,'archive_acceptance':'pending-no-copy-or-upload-claimed'})
    with (args.out/'endpoints.csv').open('w') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['actual_nodes','iterations','entries','active_training_seconds',
            'interval_nodes_per_second','save_seconds','process_wall_seconds','sampled_peak_rss_bytes','checkpoint_bytes','checkpoint_sha256'])
        for target,row,interval in zip(config['targets'],result['rows'],result['intervals']):
            w.writerow([row['counts']['nodes'],row['iteration'],row['entries'],row['active_training_seconds'],interval['active_nodes_per_second'],
                row['save_seconds'],row['stage_wall_seconds'],by_phase['pilot-'+str(target)]['sampled_peak_rss_bytes'],row['checkpoint_bytes'],row['sha256']])
    with (args.out/'coverage.csv').open('w') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['bot','street','focal_decisions','missing','found_share','blocks','independent_hands'])
        for row in result['coverage']:
            for i,street in enumerate(('preflop','flop','turn','river')):
                decisions=row['summary']['decisions_by_identity_street'][0][i]
                missing=row['summary']['misses_by_identity_street'][0][i]
                w.writerow([row['bot'],street,decisions,missing,1-missing/decisions if decisions else None,row['blocks'],768])
    # Proposed one fixed follow-up, not part of the completed pilot and not authorized.
    last=result['rows'][-1];scale=250000000/last['entries'];rate=min(x['active_nodes_per_second'] for x in result['intervals'])
    components={'active_training':(1000000000-last['counts']['nodes'])/rate,
        'startup_load_hash_other':result['intervals'][-1]['startup_load_hash_other_seconds']*last['checkpoint_bytes']/result['rows'][-2]['checkpoint_bytes'],
        'save':last['save_seconds']*scale,'export':costs['export_wall_seconds']*scale,
        'audit':costs['audit_wall_seconds']*scale,'coverage_both_native_processes':costs['coverage_native_wall_seconds']*scale,
        'independent_replay':sum(s['wall_seconds'] for s in stages if s['phase'].startswith('pilot-final-replay-')),
        'metadata_and_verification_allowance':120}
    proposal={'status':'proposal-only-not-authorized','question':'Qualify capped mature200BB costs before a three-lineage training allocation',
        'seed':config['seed'],'parent_checkpoint_sha256':last['sha256'],'targets':[1000000000],
        'entry_cap':250000000,'same_recipe':True,'new_proposed_coverage_roots':[2026102240201+i for i in range(4)],
        'coverage_blocks_per_script':128,'initial_hands':3072,'reproduction_hands':3072,
        'components_seconds':components,'central_seconds':sum(components.values()),
        'reserved_seconds':2*sum(v for k,v in components.items() if k not in ('active_training','metadata_and_verification_allowance'))+3*components['active_training']+300,
        'proposed_planning_allocation_seconds':5400,'not_a_time_stop':True,
        'assumptions':'Current minimum interval rate; linear I/O/load scaling to250M entries;2x non-training/3x active reserves plus300s. Not mature measurements or a guarantee.',
        'decision':'Stop at1B even if unfrozen; no automatic extension, full training or strength readout; then quote the model campaign.',
        'model_campaign_not_admitted':True}
    write('next-allocation.json',proposal)
    print(json.dumps({'wall_seconds':costs['whole_elapsed_seconds'],'cpu_seconds':costs['whole_child_cpu_seconds'],
        'next_proposal_central_seconds':proposal['central_seconds'],'next_proposal_reserved_seconds':proposal['reserved_seconds']},indent=2))


if __name__=='__main__':main()
