"""PR384 fixed original-profile diagnosis. No optimization, menu change or arena."""
import argparse
import csv
import json
import math
from pathlib import Path
from time import monotonic

from scripts.qualify_river_continuation import SHA,sha,write,solve_request,stable,ask
from scripts.qualify_river_exact import MENUS,PREFIX,PANEL_SHA
from scripts.river_search_panel import Worker

CASES=(0,53,69,75,79,113,137,195)
ARMS=(('reference_projected',MENUS[0],'projected-product-v1'),
      ('expanded_projected',MENUS[1],'projected-product-v1'),('expanded_exact',MENUS[1],PREFIX))
PARENT_SOURCE='e2a91181f77d9c5b0a4de545bccbe498391875fe'


def inputs(parent,panel):
    if (parent/'failure.json').exists() or json.loads((parent/'status.json').read_text())!={'status':'complete','stages':7,'source':PARENT_SOURCE}:
        raise ValueError('complete unchanged PR382 required')
    proof=json.loads((parent/'verification/verified.json').read_text())
    expected=json.loads(Path('docs/reports/river-exact-beliefs/verification.json').read_text())
    if proof!=expected or proof['status']!='passed':raise ValueError('PR382 verification pin differs')
    costs=json.loads((parent/'stage-costs.json').read_text())
    if len(costs)!=7 or any(c['returncode'] for c in costs):raise ValueError('parent stage failure')
    case_path=panel/'panel/cases.json'
    if sha(case_path)!=PANEL_SHA:raise ValueError('panel changed')
    cases=json.loads(case_path.read_text())['cases'];rows={}
    for phase in ('projected','exact'):
        path=parent/'initial'/phase/'records.jsonl'
        if sha(path)!=proof['counts'][phase]['initial_sha256']:raise ValueError('parent record checksum differs')
        for line in path.read_text().splitlines():
            r=json.loads(line);rows[(r['case_index'],r['menu'],r['backend'])]=r
    if len(rows)!=600:raise ValueError('parent matrix incomplete')
    return cases,rows


def original_identity(begin,reference):
    a=begin['result'];b=reference['begin']['result']
    for key in ('actions','probabilities','produced_root_strategy','algorithm','sweeps','requested_sweeps','target_bb','quality','nodes','checkpoints'):
        if stable(a[key])!=stable(b[key]):raise ValueError('original profile reconstruction differs: '+key)
    for key in ('installed_search','binding'):
        if a['session'][key]!=b['session'][key]:raise ValueError('original profile binding differs: '+key)


def quality_equal(a,b):
    for key in ('profile_values_bb','best_response_gains_bb'):
        if len(a[key])!=2 or len(b[key])!=2 or any(not math.isfinite(x) or abs(x-y)>1e-8 for x,y in zip(a[key],b[key])):
            raise ValueError('saved-profile aggregate audit differs')


def check_audit(result,reference):
    old=reference['audit']['result'];assert old['profile_unchanged']
    if result['profile_sha256']!=old['profile_sha256'] or not result['profile_unchanged'] or result['solver_advances']!=0:
        raise ValueError('diagnostic profile identity/advances differ')
    if result['installed_search']!=old['installed_search'] or result['actual_policy']!=old['actual_policy']:
        raise ValueError('actual deployed policy differs')
    for policy,field in [('actual','actual_deployed_policy'),('produced','candidate_profile')]:
        metrics=result[policy]['metrics'];prior=old['laws']['exact_modeled'][field]
        quality_equal(metrics['quality'],prior['quality'])
        if abs(metrics['hero_worst_case_bb']-prior['hero_worst_case_bb'])>1e-8:raise ValueError('absolute worst-case accounting differs')
        rows=result[policy]['responses']
        if any(not math.isfinite(r['leave_one_out_wc_improvement_bb']) or r['leave_one_out_wc_improvement_bb']< -1e-8 for r in rows):
            raise ValueError('restriction ordering failed')
    quality_equal(result['blueprint']['quality'],old['laws']['exact_modeled']['blueprint_quality'])


def capture(worker,cases,old,out,indices):
    snapshots=out/'snapshots';snapshots.mkdir()
    manifest=[]
    with (out/'capture.jsonl').open('x') as stream:
        for i in indices:
            for arm,menu,backend in ARMS:
                request=solve_request(cases[i],'deployment',menu)
                if backend==PREFIX:request['belief_backend']=PREFIX
                begin=ask(worker,{'mode':'retained-begin','hand_id':f'case-{i}','observation':request})
                original_identity(begin,old[(i,menu,backend)])
                context={'hand_id':f'case-{i}','handle':begin['result']['session']['handle']}
                exported=ask(worker,{'mode':'retained-export-profile',**context})['result']
                if exported['binding']!=begin['result']['session']['binding']:raise ValueError('export binding changed')
                path=snapshots/f'{i}-{arm}.json';write(path,exported)
                ask(worker,{'mode':'retained-release',**context})
                row={'case_index':i,'arm':arm,'menu':menu,'backend':backend,'path':str(path.resolve()),
                    'sha256':sha(path),'bytes':path.stat().st_size,'profile_sha256':exported['binding']['profile_sha256'],
                    'binding':exported['binding'],'installed_search':exported['installed_search'],
                    'reconstruction_seconds':begin['roundtrip_seconds']}
                manifest.append(row);stream.write(json.dumps(row)+'\n');stream.flush()
                write(out/'progress.json',{'phase':'capture','completed':len(manifest),'total':len(indices)*3})
    write(out/'snapshots.json',manifest)
    return manifest


def audit(worker,manifest,old,out):
    with (out/'records.jsonl').open('x') as stream:
        for n,item in enumerate(manifest,1):
            path=Path(item['path'])
            if sha(path)!=item['sha256']:raise ValueError('snapshot bytes changed')
            response=ask(worker,{'mode':'diagnose-saved-profile','snapshot_path':str(path),'snapshot_sha256':item['sha256']})
            check_audit(response['result'],old[(item['case_index'],item['menu'],item['backend'])])
            row={'case_index':item['case_index'],'arm':item['arm'],'snapshot_sha256':item['sha256'],**response}
            stream.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n');stream.flush()
            write(out/'progress.json',{'phase':'audit','completed':n,'total':len(manifest)})


def measure(args):
    cases,old=inputs(args.parent,args.panel);args.out.mkdir(parents=True)
    worker=Worker(args.binary,args.k50,args.model,SHA);write(args.out/'startup.json',worker.ready)
    try:
        if args.command=='repeat':
            manifest=json.loads((args.capture/'snapshots.json').read_text());validate_manifest(manifest)
        else:manifest=capture(worker,cases,old,args.out,(0,) if args.command=='calibrate' else CASES)
        if args.command in ('calibrate','repeat'):audit(worker,manifest,old,args.out)
    finally:worker.close()


def initial(args):
    _,old=inputs(args.parent,args.panel);args.out.mkdir(parents=True)
    manifest=json.loads((args.capture/'snapshots.json').read_text());validate_manifest(manifest)
    worker=Worker(args.binary,args.k50,args.model,SHA);write(args.out/'startup.json',worker.ready)
    try:audit(worker,manifest,old,args.out)
    finally:worker.close()


def validate_manifest(manifest):
    if [(r['case_index'],r['arm']) for r in manifest]!=[(i,a) for i in CASES for a,_,_ in ARMS]:
        raise ValueError('fixed snapshot matrix differs')


def verify(args):
    args.out.mkdir(parents=True)
    a=args.capture.parent/'initial/records.jsonl';b=args.capture.parent/'repeat/records.jsonl'
    rows=[[json.loads(s) for s in p.read_text().splitlines()] for p in (a,b)]
    manifest=json.loads((args.capture/'snapshots.json').read_text());validate_manifest(manifest)
    if any([(r['case_index'],r['arm']) for r in rs]!=[(r['case_index'],r['arm']) for r in manifest] for rs in rows):
        raise ValueError('diagnosis matrix differs')
    if stable(rows[0])!=stable(rows[1]):raise ValueError('saved-profile diagnostic reproduction differs')
    write(args.out/'verified.json',{'status':'passed','profiles':24,'initial_sha256':sha(a),'repeat_sha256':sha(b),
        'snapshot_manifest_sha256':sha(args.capture/'snapshots.json'),'scope':'strategic fields identical, clocks only excluded; repeat imports snapshots and advances zero sweeps'})


def quote(args):
    args.out.mkdir(parents=True);rows=[json.loads(s) for s in (args.capture/'records.jsonl').read_text().splitlines()]
    if len(rows)!=3 or [r['case_index'] for r in rows]!=[0]*3:raise ValueError('fixed calibration differs')
    _,old=inputs(args.parent,args.panel)
    by_arm={r['arm']:r for r in rows};startup=json.loads((args.capture/'startup.json').read_text())['model_and_k50_load_seconds']
    capture_cost=0.;audit_cost=0.
    for i in CASES:
        for arm,menu,backend in ARMS:
            prior=old[(i,menu,backend)];cal=by_arm[arm]
            capture_cost+=prior['begin']['roundtrip_seconds']
            scale=(prior['audit']['result']['full_menu_nodes']/cal['result']['full_menu_nodes'])**2
            audit_cost+=cal['roundtrip_seconds']*scale
    lower=3*startup+capture_cost+2*audit_cost
    upper=4*startup+1.5*capture_cost+4*audit_cost+120
    write(args.out/'quote.json',{'status':'quoted','lower_seconds':lower,'upper_seconds':upper,'startup_seconds':startup,
        'capture_prior_seconds':capture_cost,'one_audit_pass_estimate_seconds':audit_cost,'calibration_profile_count':3,
        'scope':'24 original-profile reconstructions, two saved-snapshot audit passes, three model starts; squared full-tree node scaling and 2x audit reserve; no unmeasured concurrency',
        'prior_profile_work_preserved':True,'no_main_started':True})


def summarize(args):
    root=args.capture.parent
    if (root/'failure.json').exists() or json.loads((root/'status.json').read_text())['status']!='complete':raise ValueError('complete failure-free run required')
    stages=json.loads((root/'stage-costs.json').read_text())
    if [s['phase'] for s in stages]!=['capture','initial','repeat','verify'] or any(s['returncode'] for s in stages):raise ValueError('successful fixed stages required')
    proof=json.loads((root/'verify/verified.json').read_text())
    if proof['status']!='passed' or sha(root/'initial/records.jsonl')!=proof['initial_sha256'] or sha(root/'repeat/records.jsonl')!=proof['repeat_sha256']:
        raise ValueError('verified audit bytes differ')
    if sha(args.capture/'snapshots.json')!=proof['snapshot_manifest_sha256']:raise ValueError('verified snapshot manifest changed')
    manifest=json.loads((args.capture/'snapshots.json').read_text());validate_manifest(manifest)
    for item in manifest:
        if sha(Path(item['path']))!=item['sha256']:raise ValueError('verified snapshot changed')
    rows=[json.loads(s) for s in (root/'initial/records.jsonl').read_text().splitlines()];args.out.mkdir(parents=True)
    summary=[]
    for row in rows:
        r=row['result'];policies={}
        for p in ('actual','produced'):
            d=r[p];responses=d['responses']
            policies[p]={**d['metrics'],'omitted_responses_joint_increment_bb':d['omitted_responses_joint_increment_bb'],
                'capped_response_only_opponent_gain_bb':d['capped_response_only_opponent_gain_bb'],
                'top_leave_one_out':sorted(responses,key=lambda x:x['leave_one_out_wc_improvement_bb'],reverse=True)[:5],
                'top_add_one':sorted((x for x in responses if x['omitted']),key=lambda x:x['add_one_increment_bb'],reverse=True)[:5],
                'top_blueprint_continuation':sorted(responses,key=lambda x:x['hero_blueprint_after_entry_wc_change_bb'],reverse=True)[:5]}
        summary.append({'case_index':row['case_index'],'arm':row['arm'],'installed_search':r['installed_search'],
            'profile_sha256':r['profile_sha256'],'pot_bb':r['pot_bb'],'blueprint':r['blueprint'],**policies})
    write(args.out/'results.json',{'status':'settled','scope':'eight deliberately selected diagnostic cases, not population benefit/strength; overlapping effects nonadditive',
        'cases':list(CASES),'verification':proof,'profiles':summary})
    with (args.out/'responses.csv').open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['case','arm','policy','path','action','label','omitted','leave_one_out_wc_improvement_bb','add_one_increment_bb','blueprint_continuation_wc_change_bb','changed_hero_rows'])
        for row in rows:
            for policy in ('actual','produced'):
                for v in row['result'][policy]['responses']:
                    w.writerow([row['case_index'],row['arm'],policy,json.dumps(v['path']),json.dumps(v['action']),v['label'],v['omitted'],v['leave_one_out_wc_improvement_bb'],v['add_one_increment_bb'],v['hero_blueprint_after_entry_wc_change_bb'],v['hero_blueprint_after_entry_changed_rows']])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['calibrate','capture','initial','repeat','verify','quote','summarize'])
    for k in ('out','parent','panel','capture','binary','k50','model'):p.add_argument('--'+k,type=Path,required=k=='out')
    args=p.parse_args()
    if args.out.exists():p.error('fresh output required; no automatic retry')
    try:
        if args.command in ('calibrate','capture','repeat'):measure(args)
        else:globals()[args.command](args)
    except BaseException as e:
        if args.out.exists():write(args.out/'failure.json',{'error':str(e)})
        raise

if __name__=='__main__':main()
