"""Offline PR396 publication and bounded follow-up arithmetic; no poker execution."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist


def read(path):return json.loads(path.read_text())


def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('receipt',type=Path)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    receipt=read(a.receipt)
    for name,body in receipt['files'].items():
        if hashlib.sha256(body.encode()).hexdigest()!=receipt['sha256'][name]:raise ValueError('receipt changed: '+name)
    remote=lambda name:json.loads(receipt['files']['main-v1/'+name])
    status=remote('status.json');stages=remote('stage-costs.json');result=remote('readout/results.json');proof=remote('screen/verified.json')
    if (status['status']!='complete' or 'main-v1/failure.json' in receipt['files'] or
            len(stages)!=5 or any(s['returncode'] for s in stages) or result['status']!='settled'):
        raise ValueError('complete successful settled run required')
    if (proof['status']!='passed' or proof['blocks_per_lineup']!=1024 or proof['initial_hands']!=24576 or
            proof['reproduction_hands']!=24576 or not proof['no_exclusions'] or
            not proof['all_value_profile_work_reproduced'] or proof['solver_advances'] or proof['profile_reconstructions']):
        raise ValueError('frozen screening proof differs')
    if sum(r['independent_replay']['hands'] for r in proof['records'])!=24576:
        raise ValueError('independent replay coverage differs')
    if set(proof['expectation_roots'])!={'trained','call-pressure'}:raise ValueError('lineups differ')
    (a.out/'results.json').write_text(receipt['files']['main-v1/readout/results.json'])
    cost={'stages':stages,'resources':receipt['resources'],
        'total_supervised_wall_seconds':sum(s['wall_seconds'] for s in stages),
        'total_child_cpu_seconds':sum(s['user_cpu_seconds']+s['system_cpu_seconds'] for s in stages),
        'screen_and_readout_wall_seconds':sum(s['wall_seconds'] for s in stages if s['phase'] in ('screen','readout')),
        'screen_and_readout_child_cpu_seconds':sum(s['user_cpu_seconds']+s['system_cpu_seconds'] for s in stages if s['phase'] in ('screen','readout')),
        'screen_components':result['costs'],'main_admission':remote('main-admission.json')}
    write(a.out/'costs.json',cost)
    with (a.out/'lineups.csv').open('w') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['lineup','blocks','expected_mean_bb100','pointwise95_low','pointwise95_high','family95_low','family95_high','sampled_mean_bb100','expected_sd','sampled_sd','variance_ratio','root_attempts','installed','quality_fallbacks','off_tree_hands','largest_centered_variation_share'])
        for row in result['lineups']:
            s=row['integrated'];c=row['counts']
            w.writerow([row['lineup'],1024,s['mean_bb100'],*s['pointwise95_bb100'],*s['family95_bb100'],row['sampled']['mean_bb100'],s['sd_bb100'],row['sampled']['sd_bb100'],row['variance_ratio'],c.get('mode/root',0),c.get('root_installed',0),c.get('root_quality_fallback',0),c.get('off_tree_hands',0),s['centered_square_concentration']['1']])
    with (a.out/'tails.csv').open('w') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['lineup','block','contrast_bb100','centered_square_share','uncentered_square_share','largest_root_id','largest_root_contrast_bb'])
        for row in result['lineups']:
            for tail in row['tails']:
                e=tail['examples'][0] if tail['examples'] else {}
                w.writerow([row['lineup'],tail['block'],tail['contrast_bb100'],tail['centered_square_share'],tail['uncentered_square_share'],e.get('root_id'),e.get('expected_on_minus_off_bb')])
    reports=Path(__file__).resolve().parents[1]/'docs/reports'
    prior=read(reports/'river-arena-expectation/strength-proposal.json')
    historical={x['lineup']:x for x in prior['lineups']}
    blocks={'trained':2048,'call-pressure':4096};normal=NormalDist();critical=normal.inv_cdf(1-.05/3);design=[]
    costs=result['costs']['batches'];play=0
    for row in result['lineups']:
        name=row['lineup'];n=blocks[name];boundary=0 if name=='trained' else -5
        perblock=max(sum(c['case_play_seconds'][name+'-'+arm] for arm in ('on','off')) for c in costs.values())/1024
        play+=3*2*n*perblock
        current=row['integrated']['sd_bb100'];planning=max(current*1.140139376526409,historical[name]['normal_model_sd_upper_bb100'])
        def power(sd,effect):return normal.cdf((effect-boundary)*math.sqrt(n)/sd-critical)
        effects=(0,2,5,10) if name=='trained' else (-10,-5,0,5)
        design.append({'lineup':name,'blocks_per_lineage':n,'family':'primary3' if name=='trained' else 'check_call_pressure_safeguards3',
            'gate_lower_bound_must_exceed_bb100':boundary,'one_sided_alpha':.05/3,
            'fresh_block_sd_bb100':current,'conservative_planning_sd_bb100':planning,
            'family_one_sided_error_allowance_bb100':{'fresh_sd':critical*current/math.sqrt(n),'conservative_sd':critical*planning/math.sqrt(n)},
            'conditional_power_by_true_effect':{str(e):{'fresh_sd':power(current,e),'conservative_sd':power(planning,e)} for e in effects},
            'measured_play_seconds_per_block_per_pass':perblock})
    loads=3*sum(c['startup']['model_and_k50_load_seconds'] for c in costs.values())
    hands=sum(blocks.values())*3*24;verification=result['costs']['verification_seconds']*hands/49152
    central=loads+play+verification+1800;reserve=2*loads+3*play+max(600,2*verification)+1800
    proposal={'status':'proposal-only-not-authorized','planning_budget_seconds':43200,
        'lineages':[2026101935003,202610200601,202610200602],
        'primary_peer_schedule':'003 versus601/601;601 versus602/602;602 versus003/003; two resident policies, sequential focal lineages',
        'fresh_roots_by_focal_then_lineup':[2026102239701,2026102239702,2026102239703,2026102239704,2026102239705,2026102239706],
        'design':design,'total_initial_plus_reproduction_hand_instances':hands,
        'central_seconds':central,'reserved_seconds':reserve,
        'components':{'six_process_model_k50_load_seconds':loads,'both_passes_all_lineage_play_seconds':play,'scaled_replay_proof_seconds':verification,'qualification_readout_archive_allowance_seconds':1800},
        'assumptions':'Use slower observed fresh pass by lineup; other two focal lineages unmeasured.3x play/2x model load+verification,>=600s proof reserve. No model conversion/download. No guarantee against unseen cost/variance tails.',
        'guarantee_limit':'Two separate nominal95% one-sided Bonferroni families(3primary,3single-lineup safeguards); no80% joint-power promise, no broad-scripted or release acceptance claim. Reproduction adds no samples.',
        'outcome_rule':'Require all3 primary lower bounds>0 and all3 safeguard lower bounds>-5 for this limited declared verdict; otherwise failed/inconclusive, no automatic extension. Report every lineage and adverse result.',
        'no_automatic_launch':True,'source_player_menu_work_fallback_frozen':True}
    if not 8*3600<=reserve<=proposal['planning_budget_seconds']:raise ValueError('proposal reserve outside requested8–12h scope')
    write(a.out/'followup-proposal.json',proposal)
    print(json.dumps({'total_wall_minutes':cost['total_supervised_wall_seconds']/60,'main_minutes':cost['screen_and_readout_wall_seconds']/60,
                      'followup_hours':[central/3600,reserve/3600],'hand_instances':hands}))


if __name__=='__main__':main()
