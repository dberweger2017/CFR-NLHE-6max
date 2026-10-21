"""PR382 fixed development qualification. No arena or adaptive selection."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from time import monotonic

from scripts.qualify_river_continuation import SHA, MENUS, sha, write, stable, solve_request, control_selection
from scripts.river_search_panel import Worker
from scripts.river_search_stage2 import Pool

PANEL_SHA='f5b6b2706a0b6ee8912a52961b6b8e2795158bd982bea18fa43227f74924b919'
CALIBRATION_CASES=(0,79,137,195)
PREFIX='exact-folded-prefix-v1'


def inputs(root):
    if json.loads((root/'status.json').read_text())['status']!='complete' or (root/'failure.json').exists():
        raise ValueError('PR380 must be complete without failure')
    if json.loads((root/'verification/verified.json').read_text())['status']!='passed':
        raise ValueError('PR380 reproduction is not verified')
    costs=json.loads((root/'stage-costs.json').read_text())
    if len(costs)!=16 or any(r['returncode']!=0 for r in costs):raise ValueError('PR380 stage proof differs')
    frozen=json.loads((root/'panel/freeze.json').read_text())
    if sha(root/'panel/cases.json')!=PANEL_SHA or frozen['cases_sha256']!=PANEL_SHA or frozen['model_sha256']!=SHA:
        raise ValueError('frozen panel or model changed')
    cases=json.loads((root/'panel/cases.json').read_text())['cases']
    controls=frozen['controls']['case_indices']
    if len(cases)!=200 or len(controls)!=20 or frozen['controls']!=control_selection(cases):raise ValueError('frozen counts/selection differ')
    proof=json.loads((root/'verification/verified.json').read_text())
    if sha(root/'initial/deployment/records.jsonl')!=proof['counts']['deployment']['initial_sha256']:
        raise ValueError('original deployment record checksum changed')
    previous=[json.loads(s) for s in (root/'initial/deployment/records.jsonl').read_text().splitlines()]
    if len(previous)!=400:raise ValueError('original deployment records incomplete')
    old={(r['case_index'],r['menu']):r for r in previous}
    if len(old)!=400 or any(r['status']!='ok' for r in old.values()):raise ValueError('original deployment identities differ')
    return cases,controls,old


def ask(worker,request):
    tick=monotonic();response=worker.ask(request);response['roundtrip_seconds']=monotonic()-tick
    if response['status']!='ok':raise RuntimeError('valid development request refused: '+str(response))
    return response


def original_identity(begin,old):
    """Original unconverged output remains separate from actual BP fallback."""
    result=begin['result'];reference=old['result']
    produced=result['produced_root_strategy']
    for key in ('probabilities','actions'):
        if produced[key]!=reference[key]:raise RuntimeError('original projected root strategy changed')
    for key in ('sweeps','requested_sweeps','target_bb','quality','search_menu','nodes'):
        if result[key]!=reference[key]:raise RuntimeError('original projected '+key+' changed')
    if stable(result['checkpoints'])!=stable(reference['checkpoints']):raise RuntimeError('original projected checkpoints changed')
    return True


def panel_one(worker,case,menu,backend,old=None):
    request=solve_request(case,'deployment',menu)
    if backend==PREFIX:request['belief_backend']=PREFIX
    begin=ask(worker,{'mode':'retained-begin','hand_id':f"{case['panel']}/{case['hand']}",'observation':request})
    if old is not None:original_identity(begin,old)
    session=begin['result']['session'];context={'hand_id':session['hand_id'],'handle':session['handle']}
    continuation=ask(worker,{'mode':'retained-audit',**context})
    audit=ask(worker,{'mode':'retained-full-menu-audit',**context})
    release=ask(worker,{'mode':'retained-release',**context})
    if audit['result']['profile_sha256']!=session['binding']['profile_sha256'] or audit['result']['solver_advances']!=0:
        raise RuntimeError('offline audit profile identity/advance mismatch')
    if continuation['result']['solver_advances']!=0:raise RuntimeError('continuation started a solve')
    return {'menu':menu,'backend':backend,'original_projected_identity':old is not None,
            'begin':begin,'continuation':continuation,'audit':audit,'release':release}


def controls_one(worker,case):
    return ask(worker,{**case['request'],'mode':'exact-qualification','search_menu':MENUS[1]})


def jobs(phase,indices):
    if phase=='projected':
        return [(i,m,'projected-product-v1') for i in indices for m in (MENUS if i%2==0 else MENUS[::-1])]
    if phase=='exact':return [(i,MENUS[1],PREFIX) for i in indices]
    raise ValueError('invalid panel phase')


def measure(args):
    cases,controls,old=inputs(args.inputs)
    args.out.mkdir(parents=True,exist_ok=False)
    calibration=args.command=='calibrate'
    indices=CALIBRATION_CASES if calibration else range(200)
    if args.phase=='controls':
        worker=Worker(args.binary,args.k50,args.model,SHA)
        write(args.out/'startup.json',[worker.ready])
        try:
            with (args.out/'records.jsonl').open('x') as stream:
                selected=CALIBRATION_CASES if calibration else controls
                for count,i in enumerate(selected,1):
                    row={'case_index':i,'phase':'controls',**controls_one(worker,cases[i])}
                    stream.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n');stream.flush()
                    write(args.out/'progress.json',{'phase':args.phase,'completed':count,'total':len(selected)})
        finally:worker.close()
    else:
        pool=Pool(1 if calibration else 5,args)
        write(args.out/'startup.json',[w.ready for w in list(pool.workers.queue)])
        def run(job):
            i,menu,backend=job;worker=pool.workers.get()
            try:
                row=panel_one(worker,cases[i],menu,backend,old[(i,menu)] if args.phase=='projected' else None)
                return {'case_index':i,'phase':args.phase,**row}
            finally:pool.workers.put(worker)
        work=jobs(args.phase,indices)
        try:
            with (args.out/'records.jsonl').open('x') as stream,ThreadPoolExecutor(pool.size) as executor:
                for count,row in enumerate(executor.map(run,work),1):
                    stream.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n');stream.flush()
                    write(args.out/'progress.json',{'phase':args.phase,'completed':count,'total':len(work)})
        finally:pool.close()


def verify(args):
    args.out.mkdir(parents=True,exist_ok=False);proof={}
    for phase,n in [('controls',20),('projected',400),('exact',200)]:
        a=args.inputs/'initial'/phase/'records.jsonl';b=args.inputs/'repeat'/phase/'records.jsonl'
        rows=[json.loads(s) for s in a.read_text().splitlines()]
        repeats=[json.loads(s) for s in b.read_text().splitlines()]
        if len(rows)!=n or len(repeats)!=n:raise RuntimeError('fixed phase count differs: '+phase)
        if stable(rows)!=stable(repeats):raise RuntimeError('strategic reproduction differs: '+phase)
        ids=[r['case_index'] for r in rows]
        if phase=='controls':
            if len(set(ids))!=20:raise RuntimeError('control identities repeat')
        elif [(r['case_index'],r['menu'],r['backend']) for r in rows]!=jobs(phase,range(200)):
            raise RuntimeError('panel work identities differ')
        proof[phase]={'records':n,'initial_sha256':sha(a),'repeat_sha256':sha(b)}
    write(args.out/'verified.json',{'status':'passed','counts':proof,
        'excluded':'timing counters and opaque process-local handles only; no strategic fields'})


def quote(args):
    args.out.mkdir(parents=True,exist_ok=False)
    phase_times={};startup=[]
    for phase in ('controls','projected','exact'):
        phase_times[phase]=[]
        for line in (args.inputs/phase/'records.jsonl').read_text().splitlines():
            r=json.loads(line)
            phase_times[phase].append(r['roundtrip_seconds'] if phase=='controls' else
                sum(r[k]['roundtrip_seconds'] for k in ('begin','continuation','audit','release')))
        startup += [r['model_and_k50_load_seconds'] for r in json.loads((args.inputs/phase/'startup.json').read_text())]
    # Lower bound assumes ordinary independent requests can use five workers.
    # Upper quote adds a 50% work reserve plus twice observed startup cost.
    mean=lambda v:sum(v)/len(v)
    work=2*(20*mean(phase_times['controls'])+400*mean(phase_times['projected'])/5+200*mean(phase_times['exact'])/5)
    loads=8*max(startup)
    write(args.out/'quote.json',{'status':'quoted','fixed_source_panel_sha256':PANEL_SHA,'seconds':phase_times,
        'observed_startup_seconds':startup,'lower_seconds':work+loads,'upper_seconds':1.5*work+2*loads,
        'scope':'two complete fixed passes, five ordinary workers per panel phase; dense controls one16-thread worker; loading/replay/verification included by reserve, builds/tests separate',
        'no_science_started':True})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['calibrate','measure','verify','quote'])
    for name in ('inputs','out'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('binary','k50','model'):p.add_argument('--'+name,type=Path)
    p.add_argument('--phase',choices=['controls','projected','exact']);args=p.parse_args();args.sha256=SHA
    if args.out.exists():p.error('fresh output required; no automatic retry')
    try:
        if args.command in ('calibrate','measure'):measure(args)
        else:globals()[args.command](args)
    except BaseException as error:
        if args.out.exists():write(args.out/'failure.json',{'error':str(error)})
        raise

if __name__=='__main__':main()
