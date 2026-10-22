"""Bounded live-arena integration; saved PR388 deals and frozen PR391 oracle only."""
import argparse
import json
from pathlib import Path
import subprocess
from time import monotonic

from scripts.river_whole_hand_pilot import manifest, read, write, sha, LINEUPS
from scripts.assess_river_conditional_evaluation import INVENTORY_SHA, strategic, verified_rows


def value_signature(row):
    if not row['complete_contrast']:
        raise ValueError('incomplete expectation cannot qualify')
    value = {k: row[k] for k in ('id','method','complete_contrast','contrast_chips','profile_sha256')}
    if row['contrast_chips'] is None:
        raise ValueError('missing contrast')
    for arm in ('on','off'):
        v = row[arm]
        value[arm] = {k:v[k] for k in ('complete','expected_chips','visited','terminals','policy_rows')} if v else None
    # This also preserves signed zero and the original float64 values.
    return strategic(value)


def expectation_parity(roots, reference, rows, blocks):
    expected = {r['id'] for r in roots if r['hand'] < blocks*6}
    actual = {r['id']:r for r in rows}
    if len(actual) != len(rows) or set(actual) != expected:
        raise ValueError('complete unique eligible-root coverage required')
    for key,row in actual.items():
        if row['solver_advances'] != 0 or row['profile_reconstructions'] != 0:
            raise ValueError('inline evaluation duplicated solver/profile work')
        if value_signature(row) != value_signature(reference[key]):
            raise ValueError('frozen expected value/profile/work differs: '+key)
    return {'status':'passed','roots':len(expected),'no_exclusions':True,
            'float64_value_profile_and_work_match':True,'solver_advances':0,'profile_reconstructions':0}


def trace_prefix(new, original, blocks):
    with Path(new).open('rb') as a, Path(original).open('rb') as b:
        h,old=json.loads(next(a)),json.loads(next(b))
        if h['blocks'] != blocks or h['hands'] != blocks*6 or old['blocks'] != 128:
            raise ValueError('fixed block count differs')
        if {k:v for k,v in h.items() if k not in ('blocks','hands')} != {k:v for k,v in old.items() if k not in ('blocks','hands')}:
            raise ValueError('original replay header differs')
        count=0
        for line in a:
            if line != b.readline():
                raise ValueError('evaluation changed original played hand')
            count+=1
        if count != blocks*6:
            raise ValueError('original hand coverage differs')
    return count


def reference(args):
    p=Path(__file__).resolve().parents[1]/'docs/reports/river-conditional-evaluation/assessment-provenance.json'
    pin=read(p);base=args.reference/'assessment-v1';body=base/'assess'
    if ((base/'failure.json').exists() or read(base/'status.json')['status']!='complete'
            or sha(body/'results.json')!=pin['result_sha256'] or sha(body/'verified.json')!=pin['proof_sha256']):
        raise ValueError('unchanged completed PR391 reference required')
    proof=read(body/'verified.json')
    inventory=args.reference/'qualification-v1/inventory/inventory.json'
    if proof['status']!='passed' or proof['roots']!=384 or sha(inventory)!=INVENTORY_SHA:
        raise ValueError('reference inventory/proof differs')
    rows=[]
    for i,label in enumerate(('initial','repeat')):
        path=body/label/'records.jsonl'
        if sha(path)!=proof['records_sha256'][i]:raise ValueError('verified reference records changed')
        rows.append([json.loads(s) for s in path.read_text().splitlines()])
    roots=read(inventory)['roots']
    return roots,verified_rows(roots,*rows)


def batch(args, label, blocks):
    out=args.out/label;out.mkdir()
    m=manifest(args,out,'main',blocks,4)
    for c in m['cases']:
        if c['search']:c['expectations']=str(out/(c['name']+'.expectations.jsonl'))
    write(out/'manifest.json',m)
    tick=monotonic()
    with (out/'stdout').open('x') as o,(out/'stderr').open('x') as e:
        subprocess.run([str(args.binary),str(out/'manifest.json')],stdout=o,stderr=e,check=True)
    costs={'wall_seconds':monotonic()-tick,'startup':read(out/'startup.json'),
           'play_and_write_seconds':sum(read(c['summary'])['play_and_write_seconds'] for c in m['cases']),
           'trace_bytes':sum(Path(c['trace']).stat().st_size for c in m['cases'])}
    write(out/'costs.json',costs)
    return m,costs


def verify(args, initial, repeat, blocks, roots, oracle):
    from scripts.check_nplayer_policy_replay import check
    original=read(args.pilot/'measure/initial/manifest.json')
    old_proof=read(args.pilot/'measure/verified.json')
    old_pin=read(Path(__file__).resolve().parents[1]/'docs/reports/river-whole-hand-pilot/provenance.json')
    if sha(args.pilot/'readout/results.json')!=old_pin['result_sha256']:
        raise ValueError('settled original pilot changed')
    records=[];expectations=[[],[]]
    for c,d in zip(initial['cases'],repeat['cases']):
        old=next(x for x in original['cases'] if x['name']==c['name'])
        old_receipt=next(x for x in old_proof['records'] if x['case']==c['name'])
        if old_receipt['independent_replay']['status']!='passed' or sha(old['trace'])!=old_receipt['sha256']:
            raise ValueError('original independent replay/trace changed')
        digest=sha(c['trace'])
        if digest!=sha(d['trace']) or digest!=read(c['summary'])['trace_sha256']:
            raise ValueError('fresh played-trace reproduction differs')
        trace_prefix(c['trace'],old['trace'],blocks)
        records.append({'case':c['name'],'sha256':digest,'original_hand_parity':True,
                        'independent_replay':check(Path(c['trace']))})
        if c['search']:
            for target,case in zip(expectations,(c,d)):
                target.extend(json.loads(s) for s in Path(case['expectations']).read_text().splitlines())
    parity=[expectation_parity(roots,oracle,x,blocks) for x in expectations]
    if {r['id']:value_signature(r) for r in expectations[0]}!={r['id']:value_signature(r) for r in expectations[1]}:
        raise ValueError('fresh expectation reproduction differs')
    return {'status':'passed','cases':records,'expectations':parity,'blocks_per_lineup':blocks,
            'initial_hands':12*blocks*6,'repeat_hands':12*blocks*6,
            'player_unchanged':True,'no_new_deals':True}


def measure(args):
    tick=monotonic();roots,oracle=reference(args)
    if args.mode=='measure':
        q=args.calibration/'quote.json'
        accepted=read(args.acceptance)
        if (accepted['source']!=args.source or accepted['quote_sha256']!=sha(q)
                or accepted['accepted_budget_seconds']<read(q)['upper_seconds']):
            raise ValueError('explicit accepted unchanged quote required')
        write(args.out/'accepted-quote.json',accepted)
    blocks=4 if args.mode=='calibrate' else 128
    initial,ca=batch(args,'initial',blocks);repeat,cb=batch(args,'repeat',blocks)
    proof_tick=monotonic();proof=verify(args,initial,repeat,blocks,roots,oracle)
    proof_seconds=monotonic()-proof_tick;write(args.out/'verified.json',proof)
    costs={'wall_seconds':monotonic()-tick,'batches':{'initial':ca,'repeat':cb},
           'verification_seconds':proof_seconds,'binary_sha256':sha(args.binary),
           'reference_values_reused':True,'no_profile_reconstructions':True}
    write(args.out/'costs.json',costs)
    if args.mode=='calibrate':
        play=ca['play_and_write_seconds']+cb['play_and_write_seconds']
        loads=ca['startup']['model_and_k50_load_seconds']+cb['startup']['model_and_k50_load_seconds']
        prior=read(Path(__file__).resolve().parents[1]/'docs/reports/river-whole-hand-pilot/costs.json')
        old_play=sum(x['play_and_write_seconds'] for x in prior['batch_costs'].values())
        # Cost-only projection; fixed first4 old blocks, no return selection.
        quote={'status':'quoted','source':args.source,'calibration_blocks':4,'parity':proof['expectations'],
               'lower_seconds':loads+play*32+proof_seconds*32,
               'upper_seconds':2*loads+max(3*play*32,2*old_play)+max(600,2*proof_seconds*32),
               'scope':'Fixed128 old blocks,12cases,4workers, one initial+repeat, all384referencevalues; no new deals or strength run.',
               'assumptions':'Ordinary host caches; fresh model process each pass.3x projected play or2x measured old full work,2x model loads,>=600s verification reserve. Planning allowance not time stop or completion guarantee.',
               'full_measurement_started':False,'explicit_budget_acceptance_required':True,'no_outcomes_used_for_selection':True}
        write(args.out/'quote.json',quote)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['calibrate','measure'])
    for name in ('out','binary','pilot','reference','focal','peer','k50'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--source',required=True)
    p.add_argument('--calibration',type=Path);p.add_argument('--acceptance',type=Path)
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    try:measure(args)
    except BaseException as e:write(args.out/'failure.json',{'error':str(e)});raise


if __name__=='__main__':main()
