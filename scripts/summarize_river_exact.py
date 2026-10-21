"""Read completed PR382 evidence only; never launches a solver or a hand."""
import argparse
import csv
import json
from pathlib import Path

from scripts.qualify_river_continuation import SHA,stable,write,sha
from scripts.qualify_river_exact import MENUS,PREFIX,PANEL_SHA,jobs
from scripts.river_search_round2_compare import describe


def compact(row):
    r=row['begin']['result'];a=row['audit']['result'];session=r['session'];c=row['continuation']['result']
    if a['profile_sha256']!=session['binding']['profile_sha256'] or a['solver_advances']!=0 or c['solver_advances']!=0:
        raise ValueError('profile identity/zero-advance proof differs')
    if not a['profile_unchanged']:raise ValueError('offline audit mutated profile')
    return {'case_index':row['case_index'],'menu':row['menu'],'backend':row['backend'],
        'installed':session['installed_search'],'actual_policy':a['actual_policy'],
        'sweeps':r['sweeps'],'target_bb':r['target_bb'],'capped_quality':r['quality'],
        'capped_exact_quality':a['capped_exact_oracle']['dense_quality'],
        'capped_oracle_error_bb':a['capped_exact_oracle']['max_error_bb'],
        'decision_seconds':row['begin']['roundtrip_seconds'],'offline_audit_seconds':row['audit']['roundtrip_seconds'],
        'profile_sha256':a['profile_sha256'],'checked_rows':c['checked_rows'],
        'retained_payload_bytes':session['binding']['retained_payload_bytes'],
        'timings':r.get('timings',{}),'solver_timing':r.get('solver_timing',{}),
        'chance':r.get('chance',{}),'solver_memory_bytes':r.get('solver_memory_bytes'),
        'continuation_seconds':c.get('seconds'),
        'hero_game_seat':a['hero_game_seat'],
        'laws':{law:{'actual':v['actual_deployed_policy'],'produced':v['candidate_profile'],
                     'blueprint_quality':v['blueprint_quality']} for law,v in a['laws'].items()}}


def arm(rows):
    times=[r['decision_seconds'] for r in rows];installed=sum(r['installed'] for r in rows)
    declared=sum(max(r['capped_quality']['best_response_gains_bb'])<=r['target_bb'] for r in rows)
    oracle=sum(max(r['capped_exact_quality']['best_response_gains_bb'])<=r['target_bb'] for r in rows)
    stats=describe(times)
    laws={}
    for law in ('projected','exact_modeled'):
        actual=[r['laws'][law]['actual'] for r in rows]
        laws[law]={'hero_worst_case_change_vs_blueprint_bb':describe([a['hero_worst_case_change_bb'] for a in actual]),
            'worse_than_blueprint':sum(a['hero_worst_case_change_bb'] < -1e-8 for a in actual),
            'opponent_deviation_gain_bb':describe([a['quality']['best_response_gains_bb'][1-r['hero_game_seat']] for a,r in zip(actual,rows)])}
    timing_keys=sorted(set.intersection(*(set(r['timings']) for r in rows)))
    per_row=[r['continuation_seconds']/r['checked_rows'] for r in rows if r['checked_rows'] and r['continuation_seconds'] is not None]
    return {'attempted':len(rows),'installed':installed,'fallbacks':len(rows)-installed,'declared_quality_met':declared,
        'exact_oracle_quality_met':oracle,'decision_seconds':stats,'latency_gate':stats['median']<=.5 and stats['p95']<=2.,
        'installed_coverage_gate':installed/len(rows)>=.9,'every_decision_declared_quality_gate':declared==len(rows),
        'offline_audit_seconds':describe([r['offline_audit_seconds'] for r in rows]),
        'retained_checked_rows':sum(r['checked_rows'] for r in rows),'retained_payload_bytes':describe([r['retained_payload_bytes'] for r in rows]),
        'decision_components_seconds':{key:describe([r['timings'][key] for r in rows]) for key in timing_keys},
        'batched_continuation_seconds_per_checked_row':describe(per_row) if per_row else None,
        'chance_scalar_rows':describe([r['chance']['scalar_rows'] for r in rows]) if all('scalar_rows' in r['chance'] for r in rows) else None,
        'max_capped_oracle_error_bb':max(r['capped_oracle_error_bb'] for r in rows),'classification_tolerance_bb':1e-8,'laws':laws}


def paired(left,right,law):
    if [r['case_index'] for r in left]!=[r['case_index'] for r in right]:raise ValueError('paired cases differ')
    gains=[];worst=[];harms=[]
    for a,b in zip(left,right):
        aa=a['laws'][law]['actual'];bb=b['laws'][law]['actual'];opp=1-a['hero_game_seat']
        if a['hero_game_seat']!=b['hero_game_seat']:raise ValueError('paired orientation differs')
        d=bb['hero_worst_case_bb']-aa['hero_worst_case_bb'];worst.append(d)
        g=aa['quality']['best_response_gains_bb'][opp]-bb['quality']['best_response_gains_bb'][opp];gains.append(g)
        if d < -1e-8:harms.append({'case_index':a['case_index'],'hero_worst_case_change_bb':d,'opponent_gain_reduction_bb':g})
    return {'cases':len(left),'hero_worst_case_change_bb':describe(worst),'opponent_gain_reduction_bb':describe(gains),
        'better':sum(x>1e-8 for x in worst),'worse':sum(x< -1e-8 for x in worst),'within_numeric_tolerance':sum(abs(x)<=1e-8 for x in worst),
        'classification_tolerance_bb':1e-8,'harms':sorted(harms,key=lambda r:r['hero_worst_case_change_bb'])}


def readout(root):
    if (root/'failure.json').exists() or json.loads((root/'status.json').read_text())['status']!='complete':
        raise ValueError('complete failure-free main required')
    costs=json.loads((root/'stage-costs.json').read_text())
    expected=[r+'-'+p for r in ('initial','repeat') for p in ('controls','projected','exact')]+['verify']
    if [r['phase'] for r in costs]!=expected or any(r['returncode']!=0 for r in costs):raise ValueError('stage proof incomplete')
    proof=json.loads((root/'verification/verified.json').read_text())
    if proof['status']!='passed':raise ValueError('verified reproduction required')
    pins=json.loads((root/'parent-pins.json').read_text());launch=json.loads((root/'launch.json').read_text())
    if pins['panel_sha256']!=PANEL_SHA or pins['model_sha256']!=SHA or launch['source']!=json.loads((root/'status.json').read_text())['source']:
        raise ValueError('source/input pins differ')
    calibration=Path(json.loads((root/'calibration-pin.json').read_text())['path'])
    cs=json.loads((calibration/'status.json').read_text())
    if cs['status']!='complete' or cs['source']!=launch['source'] or (calibration/'failure.json').exists():
        raise ValueError('calibration source/completion differs')
    if json.loads((calibration/'binary-pin.json').read_text())!=json.loads((root/'binary-pin.json').read_text()):
        raise ValueError('qualified binary/protocol changed')
    if json.loads((calibration/'source-manifest.json').read_text())!=json.loads((root/'source-manifest.json').read_text()):
        raise ValueError('qualified source manifest changed')
    raw={}
    for phase,n in [('controls',20),('projected',400),('exact',200)]:
        paths=[root/r/phase/'records.jsonl' for r in ('initial','repeat')]
        rows=[[json.loads(s) for s in p.read_text().splitlines()] for p in paths]
        if any(len(r)!=n for r in rows) or stable(rows[0])!=stable(rows[1]):raise ValueError('readout reproduction differs')
        if sha(paths[0])!=proof['counts'][phase]['initial_sha256'] or sha(paths[1])!=proof['counts'][phase]['repeat_sha256']:
            raise ValueError('verified raw record bytes changed')
        raw[phase]=rows[0]
    controls=raw['controls']
    if [r['case_index'] for r in controls]!=pins['controls']:raise ValueError('control selection changed')
    for phase in ('projected','exact'):
        if [(r['case_index'],r['menu'],r['backend']) for r in raw[phase]]!=jobs(phase,range(200)):
            raise ValueError('panel matrix changed')
    rows=[compact(r) for r in raw['projected']+raw['exact']]
    arms={name:[r for r in rows if r['menu']==menu and r['backend']==backend] for name,menu,backend in (
        ('reference_projected',MENUS[0],'projected-product-v1'),('expanded_projected',MENUS[1],'projected-product-v1'),
        ('expanded_exact',MENUS[1],PREFIX))}
    if any(len(r)!=200 for r in arms.values()):raise ValueError('arm counts differ')
    if any(not r['original_projected_identity'] for r in raw['projected']):raise ValueError('original deployment parity missing')
    # Native controls enforce the per-element absolute+relative leaf tolerance;
    # an aggregate absolute error alone cannot reapply that comparison.
    if any(r['status']!='ok' or r['result']['max_quality_error_bb']>1e-8 for r in controls):
        raise ValueError('oracle correctness failed')
    for r in rows:
        if r['installed'] != (max(r['capped_quality']['best_response_gains_bb'])<=r['target_bb']):
            raise ValueError('installed-search flag differs from declared quality')
        if r['capped_oracle_error_bb']>1e-8:raise ValueError('capped same-profile oracle differs')
        for law,v in r['laws'].items():
            for key in ('actual','produced'):
                q=v[key]['quality'];hero=r['hero_game_seat'];expected_wc=q['profile_values_bb'][hero]-q['best_response_gains_bb'][1-hero]
                if abs(expected_wc-v[key]['hero_worst_case_bb'])>1e-10:raise ValueError('worst-case accounting differs')
            if not r['installed'] and v['actual']['quality']!=v['blueprint_quality']:raise ValueError('actual fallback is not blueprint')
    resources=[json.loads(s) for s in (root/'resources.jsonl').read_text().splitlines()]
    startups=[]
    for repetition in ('initial','repeat'):
        for phase in ('controls','projected','exact'):
            path=root/repetition/phase/'startup.json'
            if path.exists():
                for worker in json.loads(path.read_text()):
                    if worker['status']!='ready' or worker['model_sha256']!=SHA:raise ValueError('startup model identity differs')
                    startups.append({'phase':repetition+'-'+phase,**worker})
    return {'format':'river-exact-qualification-readout-v1','status':'settled','source':launch['source'],
        'model_sha256':SHA,'panel_sha256':PANEL_SHA,'scope':'reused engineering panel; no fresh confirmation/whole-hand strength',
        'verification':proof,'parent_pins':pins,'arms':{k:arm(v) for k,v in arms.items()},
        'comparisons':{'menu_at_deployment_projected_law':paired(arms['reference_projected'],arms['expanded_projected'],'projected'),
            'menu_at_deployment_exact_law':paired(arms['reference_projected'],arms['expanded_projected'],'exact_modeled'),
            'exact_vs_projected_expanded_exact_law':paired(arms['expanded_projected'],arms['expanded_exact'],'exact_modeled')},
        'controls':{'count':20,'max_leaf_error_bb':max(r['result']['max_leaf_error_bb'] for r in controls),
            'max_quality_error_bb':max(r['result']['max_quality_error_bb'] for r in controls),
            'prefix_64sweep_seconds':describe([r['result']['timings']['prefix_fixed_solve_seconds'] for r in controls]),
            'dense_64sweep_seconds':describe([r['result']['timings']['dense_fixed_solve_seconds'] for r in controls]),
            'paired_dense_over_prefix_64sweep_ratio':describe([r['result']['timings']['dense_fixed_solve_seconds']/r['result']['timings']['prefix_fixed_solve_seconds'] for r in controls]),
            'per_case':controls,'scope':'fixed-work operator correctness controls, not matched-convergence belief gate passes'},
        'original_misses':[{ 'case_index':i,'arms':{k:{'installed':next(r for r in v if r['case_index']==i)['installed'],
              'checkpoints':next(r for r in raw['exact']+raw['projected'] if r['case_index']==i and r['menu']==v[0]['menu'] and r['backend']==v[0]['backend'])['begin']['result']['checkpoints']} for k,v in arms.items()}} for i in (137,195)],
        'costs':{'stages':costs,'wall_seconds':sum(r['wall_seconds'] for r in costs),
            'model_load_instances':len(startups),'startups':startups,
            'summed_worker_startup_seconds':sum(r['model_and_k50_load_seconds'] for r in startups),
            'summed_worker_policy_load_seconds':sum(r['policy_load_seconds'] for r in startups),
            'child_cpu_seconds':sum(r['user_cpu_seconds']+r['system_cpu_seconds'] for r in costs),
            'sampled_family_peak_rss_bytes':max(r['worker_family_rss_bytes'] for r in resources),
            'min_available_ram_bytes':min(r['available_ram_bytes'] for r in resources),
            'max_cpu_c':max(r['cpu_c'] for r in resources),'max_thermistor15_c':max(r['thermistor15_c'] for r in resources),
            'first_swap_bytes':resources[0]['swap_used_bytes'],'last_swap_bytes':resources[-1]['swap_used_bytes'],
            'last_nvme_free_bytes':resources[-1]['nvme_free_bytes'],'last_hdd_free_bytes':resources[-1]['hdd_free_bytes']},
        'per_case':rows}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    if args.out.exists():p.error('fresh output required')
    result=readout(args.root);args.out.mkdir(parents=True);write(args.out/'results.json',result)
    write(args.out/'summary.json',{k:v for k,v in result.items() if k!='per_case'})
    with (args.out/'cases.csv').open('w',newline='') as stream:
        w=csv.writer(stream,lineterminator='\n');w.writerow(['case','menu','backend','installed','sweeps','decision_seconds','offline_audit_seconds','law','hero_worst_case_bb','hero_worst_case_change_vs_bp_bb','opponent_gain_bb','produced_hero_worst_case_bb','produced_opponent_gain_bb','profile_sha256','hero_game_seat','target_bb','capped_player0_gain_bb','capped_player1_gain_bb','capped_exact_player0_gain_bb','capped_exact_player1_gain_bb','actual_player0_value_bb','actual_player1_value_bb','actual_player0_gain_bb','actual_player1_gain_bb','produced_player0_gain_bb','produced_player1_gain_bb'])
        for r in result['per_case']:
            for law,v in r['laws'].items():
                a=v['actual'];w.writerow([r['case_index'],r['menu'],r['backend'],r['installed'],r['sweeps'],r['decision_seconds'],r['offline_audit_seconds'],law,a['hero_worst_case_bb'],a['hero_worst_case_change_bb'],a['quality']['best_response_gains_bb'][1-r['hero_game_seat']],v['produced']['hero_worst_case_bb'],v['produced']['quality']['best_response_gains_bb'][1-r['hero_game_seat']],r['profile_sha256'],r['hero_game_seat'],r['target_bb'],*r['capped_quality']['best_response_gains_bb'],*r['capped_exact_quality']['best_response_gains_bb'],*a['quality']['profile_values_bb'],*a['quality']['best_response_gains_bb'],*v['produced']['quality']['best_response_gains_bb']])
    print(json.dumps({'status':result['status'],'arms':result['arms'],'costs':{k:v for k,v in result['costs'].items() if k!='stages'}},indent=2))

if __name__=='__main__':main()
