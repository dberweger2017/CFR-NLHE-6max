"""PR380 fixed engineering panel; no arena, training, adaptive arms or retries.

Trace creation/replay and thermal process supervision are external stages. This
driver freezes observations, measures declared requests and verifies reproduction.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from random import Random
from statistics import median
from time import monotonic

from scripts.river_search_panel import Worker, extract
from scripts.river_search_round2_compare import describe, metric
from scripts.river_search_stage2 import Pool

SHA = 'd835f61f4a5407bd47e8f8a5da849ef82c16ad21fce32f15dce72d5997275189'
MENUS = ['pot-jam-cap3-v1', 'pot-jam-cap3-root-check-min-v1']
STRICT = [64,128,256,512,1024,2048,4096,8192]
DEPLOY = [8,16,32,64,128,256,512,1024,2048]
TRACE_SEEDS = [202610216501,202610216502]
PANEL_SEEDS = [202610216511,202610216512]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def write(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def control_selection(cases):
    order=sorted(range(len(cases)),key=lambda i:hashlib.sha256(f"{cases[i]['panel']}/{cases[i]['hand']}".encode()).hexdigest())
    bands=[[],[],[],[]]
    for i in order:
        pot=sum(p[2] for p in cases[i]['request']['players'])/100
        bands[0 if pot<5 else 1 if pot<15 else 2 if pot<40 else 3].append(i)
    chosen=[i for band in bands for i in band[:5]]
    chosen += [i for i in order if i not in chosen][:20-len(chosen)]
    return {'case_indices':chosen,'band_counts':[len(b) for b in bands],
            'selected_band_counts':[sum(i in chosen for i in b) for b in bands],
            'rule':'sha256(panel-id/hand-id), five per public-pot band, global hash fill'}


def solve_request(case,phase,menu):
    checkpoints=STRICT if phase=='strict' else DEPLOY
    return {**case['request'],'mode':'solve','search_menu':menu,'algorithm':'dcfr-1.5-0-2',
            'sweeps':checkpoints[-1],'checkpoints':checkpoints,'stop_at_target':True,
            'target':{'pot_fraction':0.002 if phase=='strict' else 0.01,'cap_bb':0.02 if phase=='strict' else 0.1},
            'omitted':phase=='strict'}


def control_request(case):
    return {**case['request'],'mode':'belief-control','search_menu':MENUS[1],
            'checkpoints':STRICT,'reference_checkpoints':STRICT,'reference_tolerance_bb':0.01,'matched_accuracy':True}


def expected(response):
    if response['status']=='ok':return
    reason=response.get('reason','')
    if reason!='own holding has zero modeled root reach' and not reason.startswith('unsupported '):
        raise RuntimeError(f'unexpected valid-observation refusal: {reason}')


def ask(worker,request):
    tick=monotonic();response=worker.ask(request);response['roundtrip_seconds']=monotonic()-tick
    expected(response)
    return response


def retained(worker,case):
    begin=ask(worker,{'mode':'retained-begin','hand_id':f"{case['panel']}/{case['hand']}",
                      'observation':solve_request(case,'deployment',MENUS[1])})
    if begin['status']!='ok':raise RuntimeError('valid retained root could not begin')
    session=begin['result']['session']
    context={'hand_id':session['hand_id'],'handle':session['handle']}
    audit=ask(worker,{'mode':'retained-audit',**context})
    release=ask(worker,{'mode':'retained-release',**context})
    if audit['status']!='ok' or release['status']!='ok' or audit['result']['solver_advances']!=0:
        raise RuntimeError('retained audit/release failed')
    return {'begin':begin,'audit':audit,'release':release}


def freeze(args):
    args.out.mkdir(exist_ok=False,parents=True)
    pool=Pool(5,args)
    cases=[];composition=[]
    try:
        for index in range(2):
            trace=args.inputs/f'trace-{index}.jsonl'
            repeat=args.inputs/f'trace-{index}-repeat.jsonl'
            if sha(trace)!=sha(repeat):raise RuntimeError('self-play reproduction differs')
            proof=json.loads((args.inputs/f'replay-{index}.json').read_text())
            if proof['status']!='passed' or proof['trace_sha256']!=sha(trace) or proof['hands']!=5000:
                raise RuntimeError('independent replay proof differs')
            header,counts,eligible=extract(trace)
            if header['seed']!=TRACE_SEEDS[index] or header['hands']!=5000 or any(p['sha256']!=SHA for p in header['policies']):
                raise RuntimeError('fresh trace identity differs')
            if len(eligible)<100:raise RuntimeError('inconclusive: fewer than 100 eligible roots; no added hands')
            panel=f'panel-{PANEL_SEEDS[index]}'
            with (args.out/f'classification-{index}.jsonl').open('x') as stream,ThreadPoolExecutor(5) as executor:
                for row,response in zip(eligible,executor.map(pool.ask,({**r['request'],'search_menu':MENUS[1]} for r in eligible))):
                    expected(response)
                    if response['status']!='ok':raise RuntimeError('classification failed')
                    stream.write(json.dumps({'hand':row['hand'],**response},separators=(',',':'))+'\n');stream.flush()
            selected=sorted(Random(PANEL_SEEDS[index]).sample(range(len(eligible)),100))
            cases += [{**eligible[i],'panel':panel} for i in selected]
            composition.append({'panel':panel,'seed':header['seed'],'trace_sha256':sha(trace),
                                'repeat_sha256':sha(repeat),'replay_proof':proof,'eligible':len(eligible),'composition':counts})
    finally:pool.close()
    write(args.out/'cases.json',{'format':'river-continuation-cases-v1','cases':cases})
    write(args.out/'freeze.json',{'format':'river-continuation-freeze-v1','model_sha256':SHA,
          'cases_sha256':sha(args.out/'cases.json'),'source':args.source,'composition':composition,
          'controls':control_selection(cases),'cases':len(cases),'menus':MENUS,'workers':5})


def measure(args):
    args.out.mkdir(exist_ok=False,parents=True)
    frozen=json.loads((args.inputs/'freeze.json').read_text())
    if frozen['cases_sha256']!=sha(args.inputs/'cases.json'):raise RuntimeError('frozen cases changed')
    cases=json.loads((args.inputs/'cases.json').read_text())['cases']
    if len(cases)!=200:raise RuntimeError('expected 200 fresh cases')
    if args.phase=='belief':
        worker=Worker(args.binary,args.k50,args.model,SHA)
        try:
            with (args.out/'records.jsonl').open('x') as stream:
                for i in frozen['controls']['case_indices']:
                    record={'case_index':i,'phase':'belief',**ask(worker,control_request(cases[i]))}
                    stream.write(json.dumps(record,separators=(',',':'))+'\n');stream.flush()
                    write(args.out/'progress.json',{'phase':'belief','completed':sum(1 for _ in (args.out/'records.jsonl').open()),'total':20})
        finally:worker.close()
    else:
        pool=Pool(5,args)
        def job(work):
            i,menu=work
            if args.phase!='retained':
                response=pool.ask(solve_request(cases[i],args.phase,menu));expected(response)
            else:
                worker=pool.workers.get()
                try:response=retained(worker,cases[i])
                finally:pool.workers.put(worker)
            return {'case_index':i,'phase':args.phase,'menu':menu,**response}
        jobs=[(i,menu) for i in range(200) for menu in
              ([MENUS[1]] if args.phase=='retained' else MENUS if i%2==0 else MENUS[::-1])]
        try:
            with (args.out/'records.jsonl').open('x') as stream,ThreadPoolExecutor(5) as executor:
                for count,record in enumerate(executor.map(job,jobs),1):
                    stream.write(json.dumps(record,separators=(',',':'))+'\n');stream.flush()
                    write(args.out/'progress.json',{'phase':args.phase,'completed':count,'total':len(jobs)})
        finally:pool.close()


def stable(value):
    """Exclude clocks and opaque session handles; keep every strategic result."""
    if isinstance(value,list):return [stable(v) for v in value]
    if isinstance(value,dict):
        return {k:stable(v) for k,v in value.items() if k not in ('timings','solver_timing','handle')
                and 'seconds' not in k}
    return value


def verify(args):
    args.out.mkdir(exist_ok=False,parents=True)
    counts={}
    for phase,n in [('strict',400),('deployment',400),('retained',200),('belief',20)]:
        a=[json.loads(s) for s in (args.inputs/'initial'/phase/'records.jsonl').read_text().splitlines()]
        b=[json.loads(s) for s in (args.inputs/'repeat'/phase/'records.jsonl').read_text().splitlines()]
        if len(a)!=n or len(b)!=n:raise RuntimeError(f'{phase} count differs')
        if stable(a)!=stable(b):raise RuntimeError(f'{phase} deterministic reproduction differs')
        counts[phase]={'records':n,'initial_sha256':sha(args.inputs/'initial'/phase/'records.jsonl'),
                       'repeat_sha256':sha(args.inputs/'repeat'/phase/'records.jsonl')}
    write(args.out/'verified.json',{'status':'passed','counts':counts,
          'excluded':'timings/solver timing, any seconds counter and opaque per-process session handle; no strategic quantities excluded'})


def calibrate(args):
    args.out.mkdir(exist_ok=False,parents=True)
    rows=[json.loads(s) for s in args.inputs.read_text().splitlines()][:2]
    cases=[{**r,'panel':'existing-development'} for r in rows]
    worker=Worker(args.binary,args.k50,args.model,SHA)
    records=[]
    try:
        for phase in ['strict','deployment']:
            for i,case in enumerate(cases):
                for menu in MENUS:
                    records.append({'phase':phase,'case_index':i,'menu':menu,**ask(worker,solve_request(case,phase,menu))})
        for i,case in enumerate(cases):records.append({'phase':'retained','case_index':i,**retained(worker,case)})
        records.append({'phase':'belief','case_index':0,**ask(worker,control_request(cases[0]))})
    finally:worker.close()
    write(args.out/'records.json',records)
    times={phase:[r['roundtrip_seconds'] for r in records if r['phase']==phase] for phase in ['strict','deployment','belief']}
    # Serial-work extrapolation divided only for the five ordinary workers;
    # exact controls remain serial. This is a cost quote, not fresh results.
    seconds=2*(sum(times['strict'])/4*400/5+sum(times['deployment'])/4*600/5+times['belief'][0]*20)
    write(args.out/'quote.json',{'model_sha256':SHA,'development_cases':2,'worker_ready':worker.ready,
          'seconds':times,'measurement_work_estimate_seconds':seconds,
          'scope':'two complete passes; five ordinary workers, one serial 16-thread exact worker; excludes trace generation/replay, startup phases and build',
          'fresh_observations_read':False})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['freeze','measure','verify','calibrate'])
    for name in ['inputs','out']:p.add_argument('--'+name,type=Path,required=True)
    for name in ['binary','k50','model']:p.add_argument('--'+name,type=Path)
    p.add_argument('--phase',choices=['strict','deployment','retained','belief'])
    p.add_argument('--source')
    args=p.parse_args();args.sha256=SHA
    if args.out.exists():p.error('output root already exists; refusing to overwrite or retry')
    try:globals()[args.command](args)
    except BaseException as error:
        if args.out.exists():write(args.out/'failure.json',{'error':str(error)})
        raise


if __name__=='__main__':main()
