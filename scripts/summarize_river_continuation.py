"""Compact readout of a completed, independently reproduced PR380 experiment.

Never reads an active study. Unsupported attempts and unqualified comparisons
remain in denominators. No new acceptance rule or statistical family is added.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from statistics import median

from scripts.qualify_river_continuation import MENUS, SHA, sha, stable, write
from scripts.river_search_round2_compare import describe, metric


def records(root,phase,repetition='initial'):
    return [json.loads(s) for s in (root/repetition/phase/'records.jsonl').read_text().splitlines()]


def converged(row):
    return row['status']=='ok' and row['result']['checkpoints'][-1]['target_met']


def readout(root):
    if (root/'failure.json').exists() or json.loads((root/'status.json').read_text())['status']!='complete':
        raise ValueError('study is not complete without failure')
    proof=json.loads((root/'verification/verified.json').read_text())
    if proof['status']!='passed':raise ValueError('deterministic verification did not pass')
    costs=json.loads((root/'stage-costs.json').read_text())
    if len(costs)!=16 or any(r['returncode']!=0 for r in costs):raise ValueError('stage completion proof differs')
    frozen=json.loads((root/'panel/freeze.json').read_text())
    cases=json.loads((root/'panel/cases.json').read_text())['cases']
    if frozen['model_sha256']!=SHA or sha(root/'panel/cases.json')!=frozen['cases_sha256'] or len(cases)!=200:
        raise ValueError('frozen observations differ')
    phases={p:records(root,p) for p in ['strict','deployment','retained','belief']}
    for phase,n in [('strict',400),('deployment',400),('retained',200),('belief',20)]:
        rows=phases[phase];again=records(root,phase,'repeat')
        if len(rows)!=n or len(again)!=n or stable(rows)!=stable(again):raise ValueError(f'{phase} repetition differs')
        identities=[(r['case_index'],r.get('menu')) for r in rows]
        expected=({(i,m) for i in range(200) for m in MENUS} if phase in ['strict','deployment'] else
                  {(i,MENUS[1]) for i in range(200)} if phase=='retained' else
                  {(i,None) for i in frozen['controls']['case_indices']})
        if len(set(identities))!=n or set(identities)!=expected:raise ValueError(f'{phase} identities incomplete or duplicated')
    strict={(r['case_index'],r['menu']):r for r in phases['strict']}
    deploy={(r['case_index'],r['menu']):r for r in phases['deployment']}
    pairs=[]
    for i,case in enumerate(cases):
        arms=[strict[i,m] for m in MENUS]
        qualified=all(converged(a) for a in arms)
        row={'case_index':i,'panel':case['panel'],'hand':case['hand'],'seat':case['request']['seat'],
             'pot_bb':sum(p[2] for p in case['request']['players'])/100,'qualified':qualified,
             'statuses':[a['status'] for a in arms],'reasons':[a.get('reason') for a in arms],
             'strict_converged':[converged(a) for a in arms]}
        if all(a['status']=='ok' for a in arms):
            a,b=[metric(x['result']) for x in arms]
            if arms[0]['result']['law']!=arms[1]['result']['law'] or a['blueprint_opponent_gain_bb']!=b['blueprint_opponent_gain_bb']:
                raise ValueError('paired beliefs or unchanged blueprint differ')
            row.update(baseline=a,candidate=b,opponent_gain_reduction_bb=a['opponent_gain_bb']-b['opponent_gain_bb'])
        pairs.append(row)
    qualified=[p for p in pairs if p['qualified']]
    reductions=[p['opponent_gain_reduction_bb'] for p in qualified]
    out={'format':'river-continuation-qualification-results-v1','status':'settled','model_sha256':SHA,
         'measured_source':frozen['source'],'cases_sha256':frozen['cases_sha256'],'cases':200,
         'primary':{'qualified_pairs':len(qualified),'inconclusive_pairs':200-len(qualified),
                    'paired_opponent_gain_reduction_bb':describe(reductions),
                    'improved':sum(x>1e-9 for x in reductions),'worsened':sum(x< -1e-9 for x in reductions),
                    'unchanged':sum(abs(x)<=1e-9 for x in reductions)},'arms':{},'per_case':pairs,
         'composition':frozen['composition'],'verification':proof}
    for menu,label in zip(MENUS,['baseline','candidate']):
        sr=[r for r in phases['strict'] if r['menu']==menu]
        dr=[r for r in phases['deployment'] if r['menu']==menu]
        ok=[r for r in sr if r['status']=='ok']
        dt=[r['roundtrip_seconds'] for r in dr]
        arm={'strict_ok':len(ok),'strict_quality_met':sum(converged(r) for r in sr),
             'strict_decision_seconds':describe([r['roundtrip_seconds']-r['result']['omitted_raise_evaluation']['seconds'] for r in ok]),
             'offline_full_menu_audit_seconds':describe([r['result']['omitted_raise_evaluation']['seconds'] for r in ok]),
             'nodes':describe([r['result']['nodes'] for r in ok]),
             'solver_f64_bytes':describe([r['result']['solver_memory_bytes'] for r in ok]),
             'deployment_ok':sum(r['status']=='ok' for r in dr),'deployment_quality_met':sum(converged(r) for r in dr),
             'deployment_decision_seconds_all_attempts':describe(dt),
             'latency_gate':median(dt)<=.5 and describe(dt)['p95']<=2,
             'every_decision_declared_quality_gate':all(converged(r) for r in dr),
             'qualified_opponent_gain_bb':describe([p[label]['opponent_gain_bb'] for p in qualified]),
             'blueprint_regressions_qualified':sum(p[label]['opponent_gain_bb']>p[label]['blueprint_opponent_gain_bb']+1e-9 for p in qualified)}
        out['arms'][menu]=arm
    details=[]
    for row in phases['retained']:
        i=row['case_index'];begin=row['begin'];audit=row['audit']['result'];b=begin['result'];session=b['session']
        if session['model_sha256']!=SHA or session['hand_id']!=f"{cases[i]['panel']}/{cases[i]['hand']}":raise ValueError('retained identity differs')
        if audit['solver_advances']!=0 or row['release']['result']!={'released':True}:raise ValueError('continuation solved or failed to release')
        installed=session['installed_search']
        if installed:
            reference=deploy[i,MENUS[1]]['result']
            for key in ['probabilities','actions','quality','sweeps']:
                if b[key]!=reference[key]:raise ValueError(f'retained begin differs from stateless deployed solve: {key}')
            if not audit['installed_search'] or audit['checked_rows']<1:raise ValueError('installed continuation not audited')
            if audit['profile_sha256']!=session['binding']['profile_sha256']:raise ValueError('retained profile identity differs')
        details.append({'case_index':i,'installed':installed,'reason':session['fallback_reason'],
                        'begin_roundtrip_seconds':begin['roundtrip_seconds'],'checked_rows':audit['checked_rows'],
                        'audit_seconds':audit.get('seconds',0),'retained_payload_bytes':session['binding']['retained_payload_bytes'],
                        'profile_sha256':session['binding']['profile_sha256']})
    installed=[r for r in details if r['installed']]
    out['retained']={'installed':len(installed),'fallbacks':200-len(installed),'share':len(installed)/200,
                     'installed_coverage_90pct_gate':len(installed)>=180,
                     'checked_rows':sum(r['checked_rows'] for r in details),'solver_advances':0,
                     'begin_seconds':describe([r['begin_roundtrip_seconds'] for r in details]),
                     'payload_bytes':describe([r['retained_payload_bytes'] for r in installed]),
                     'audit_seconds_per_checked_row':describe([r['audit_seconds']/r['checked_rows'] for r in installed]),
                     'timing_scope':'audit includes synthetic public observation construction, replay/row checking and bit equality; timer excludes model load and new solves',
                     'per_case':details}
    controls=[]
    for row in phases['belief']:
        i=row['case_index'];entry={'case_index':i,'panel':cases[i]['panel'],'hand':cases[i]['hand'],'status':row['status']}
        if row['status']=='ok':
            r=row['result'];d=r['decomposition']
            if not r['matched_accuracy'] or r['target_bb']!=.01 or r['reference']['tolerance_bb']!=.01:raise ValueError('belief accuracies differ')
            for s in range(2):
                if abs(r['excess_gain_bb'][s]-(d['same_profile_law_shift_bb'][s]+d['solver_residual_bb'][s]-d['reference_residual_bb'][s]))>1e-12:
                    raise ValueError('belief residual identity differs')
            entry.update(qualified=r['qualified'],passes=r['passes'],pot_bb=r['pot_bb'],
                         S=d['solver_residual_bb'],D=d['same_profile_law_shift_bb'],R=d['reference_residual_bb'],E=r['excess_gain_bb'],
                         projected_sweeps=r['deployed']['sweeps'],reference_sweeps=r['reference']['sweeps'],
                         roundtrip_seconds=row['roundtrip_seconds'],projection_tv=r['law']['projection_total_variation'])
        else:entry.update(qualified=False,passes=False,reason=row.get('reason'))
        controls.append(entry)
    cq=[r for r in controls if r['qualified']]
    out['belief']={'controls':20,'qualified':len(cq),'passes':sum(r['passes'] for r in cq),
                   'verdict':'inconclusive' if len(cq)!=20 else 'pass' if all(r['passes'] for r in cq) else 'fail',
                   'excess_threshold_bb':.05,'selection':frozen['controls'],'per_case':controls,
                   'interpretation':'E = D + S - R compares two approximate solutions under the exact modeled law; E is not pure causal projection error'}
    resources=[json.loads(s) for s in (root/'resources.jsonl').read_text().splitlines()]
    out['costs']={'stages':costs,'wall_seconds_sum':sum(c['wall_seconds'] for c in costs),
                  'user_cpu_seconds':sum(c['user_cpu_seconds'] for c in costs),'system_cpu_seconds':sum(c['system_cpu_seconds'] for c in costs),
                  'sampled_family_peak_rss_bytes':max(r['worker_family_rss_bytes'] for r in resources),
                  'max_cpu_c':max(r['cpu_c'] for r in resources),'max_thermistor15_c':max(r['thermistor15_c'] for r in resources),
                  'min_available_ram_bytes':min(r['available_ram_bytes'] for r in resources),
                  'first_swap_bytes':resources[0]['swap_used_bytes'],'last_swap_bytes':resources[-1]['swap_used_bytes'],
                  'last_nvme_free_bytes':resources[-1]['nvme_free_bytes'],'last_hdd_free_bytes':resources[-1]['hdd_free_bytes']}
    classified=[]
    for i in range(2):classified += [json.loads(s) for s in (root/f'panel/classification-{i}.jsonl').read_text().splitlines()]
    support=sum(r['result']['supported'] for r in classified)
    out['allocation_support']={'supported':support,'eligible':len(classified),'share':support/len(classified),
                               'coverage_90pct_gate':support/len(classified)>=.9}
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if args.out.exists():p.error('fresh output required')
    result=readout(args.root)
    args.out.mkdir(parents=True)
    write(args.out/'results.json',result)
    rows=result['per_case']
    with (args.out/'cases.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['case','panel','hand','seat','pot_bb','qualified','baseline_opponent_gain_bb',
            'candidate_opponent_gain_bb','blueprint_opponent_gain_bb','paired_reduction_bb'])
        for row in rows:
            writer.writerow([row[k] for k in ['case_index','panel','hand','seat','pot_bb','qualified']]+
                [row.get('baseline',{}).get('opponent_gain_bb'),row.get('candidate',{}).get('opponent_gain_bb'),
                 row.get('baseline',{}).get('blueprint_opponent_gain_bb'),row.get('opponent_gain_reduction_bb')])
    print(json.dumps({k:result[k] for k in ['status','primary','allocation_support']},indent=2))


if __name__=='__main__':main()
