"""Proof-gated same-observation policy diagnostics; no play or action sampling."""
import argparse
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
from scripts import nplayer_paired_evidence as evidence

STREETS=('preflop','flop','turn','river')
LABELS=evidence.LABELS[:3]


def fingerprint(row,index):
    """Independent serialization of the native acting-seat-only projection."""
    state=row['states'][index];actor=row['actors'][index];history=[];actions=0
    for event in row['history']:
        if len(event)!=2:
            if actions==index:break
            actions+=1
        history.append(event)
    if actions!=index:raise ValueError('shared observation history count')
    value=dict(format='nplayer-legal-observation-v1',seat=actor,button=row['button'],hole=state['holes'][actor],
        board=state['board'],street=state['street'],actor=state['actor'],stacks=row['stacks'],sb=row['sb'],bb=row['bb'],
        players=state['players'],legal=state['legal'],history=history)
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def menu(row,index):
    state=row['states'][index];legal=state['legal'];actor=row['actors'][index]
    choices=[(1,['check',0])] if legal['check'] else [(0,['fold',0]),(2,['call',0])]
    if legal['raise_to'] is not None:
        low,high=legal['raise_to'];matched=state['players'][actor][1]+legal['call'];after=sum(p[2] for p in state['players'])+legal['call']
        target=max(low,min(high,matched+after))
        for label,value in [(3,low),(4,target),(5,high)]:
            if label==5 and high-matched>2*after and high!=low:continue
            action=['raise',value]
            if action not in [a for _,a in choices]:choices.append((label,action))
    return choices


def query_rows(row,index,header):
    lookup=row['lookups'][index];shared=lookup.get('shared');specs=header.get('shared_models')
    if not shared or not isinstance(specs,list) or len(specs)!=2:raise ValueError('missing shared observation or model inventory')
    aliases=[s['alias'] for s in specs]
    if len(set(aliases))!=2 or row['identities'][row['actors'][index]]!=0:raise ValueError('shared observation is not focal')
    choices=menu(row,index)
    if (shared['format']!='nplayer-shared-observation-v1' or shared['key']!=lookup['key']
            or shared['observation_sha256']!=fingerprint(row,index) or shared['actions']!=[a for _,a in choices]
            or len(shared['queries'])!=2):raise ValueError('shared legal observation/key/menu differs')
    for query,alias in zip(shared['queries'],aliases):
        probs=query['probabilities'];status=query['status']
        if query['alias']!=alias or status not in LABELS or len(probs)!=len(choices) or not probs:raise ValueError('shared model/status/probability inventory')
        if any(type(p) not in (float,int) or not math.isfinite(p) or p<0 for p in probs) or not math.isclose(sum(probs),1,rel_tol=0,abs_tol=1e-10):raise ValueError('shared invalid distribution')
        if status in ('missing','zero_mass') and any(not math.isclose(p,1/len(probs),rel_tol=0,abs_tol=1e-14) for p in probs):raise ValueError('shared fallback not uniform')
    own=header['policies'][0]
    matches=[q for q,spec in zip(shared['queries'],specs) if spec['pin']['sha256']==own['sha256']]
    if len(matches)!=1 or matches[0]['status']!=lookup['status']:raise ValueError('shared source-arm lookup differs')
    return shared['queries']


def verified_diagnostics(a,b,repeat_a,repeat_b,proof_a,proof_b):
    """All occurrences from both arms, equally weighted; no abstract-key dedup."""
    for trace,repeat,proof in ((a,repeat_a,proof_a),(b,repeat_b,proof_b)):
        p=json.loads(Path(proof).read_text())
        if p['status']!='passed' or evidence.sha(trace)!=p['trace_sha256'] or evidence.sha(trace)!=evidence.sha(repeat):raise ValueError('shared replay/reproduction barrier')
    streams=[evidence.rows(a),evidence.rows(b)];headers=[next(s) for s in streams]
    for h in headers:evidence.header_check(h)
    if headers[0].get('shared_models')!=headers[1].get('shared_models') or len(headers[0].get('shared_models',[]))!=2:raise ValueError('shared model pins differ')
    if any(headers[0][k]!=headers[1][k] for k in ['identity','hands','blocks','seed','schedule']) or headers[0]['policies'][1:]!=headers[1]['policies'][1:]:raise ValueError('shared fixed field differs')
    groups={};digest=hashlib.sha256();total=0;count=0;block_counts={}
    for count,pair in enumerate(itertools.zip_longest(*streams),1):
        if None in pair:raise ValueError('shared unequal hand inventory')
        if any(pair[0][k]!=pair[1][k] for k in ['hand','block','permutation','identities','deck','button']):raise ValueError('shared paired deals differ')
        for arm,(row,h) in enumerate(zip(pair,headers)):
            n,schedule=evidence.header_check(h);evidence.validate_row(row,count-1,h,n,schedule)
            for i,actor in enumerate(row['actors']):
                focal=row['identities'][actor]==0;lookup=row['lookups'][i]
                if not focal:
                    if 'shared' in lookup:raise ValueError('unexpected nonfocal shared observation')
                    continue
                queries=query_rows(row,i,h);street=STREETS.index(row['states'][i]['street']);key=f'{arm}/{street}'
                g=groups.setdefault(key,dict(origin_arm=arm,street=street,observations=0,models=[dict.fromkeys(LABELS,0),dict.fromkeys(LABELS,0)],transition_counts={},sum_probability_tv=0.,max_probability_tv=0.))
                g['observations']+=1;total+=1
                for j,q in enumerate(queries):g['models'][j][q['status']]+=1
                transition=queries[0]['status']+'->'+queries[1]['status'];g['transition_counts'][transition]=g['transition_counts'].get(transition,0)+1
                tv=sum(abs(x-y) for x,y in zip(queries[0]['probabilities'],queries[1]['probabilities']))/2;g['sum_probability_tv']+=tv;g['max_probability_tv']=max(g['max_probability_tv'],tv)
                digest.update(json.dumps([arm,row['hand'],i,lookup['shared']],sort_keys=True,separators=(',',':')).encode()+b'\n')
                block_key=f"{row['block']}/{arm}/{street}";block_counts[block_key]=block_counts.get(block_key,0)+1
    if count!=headers[0]['hands']:raise ValueError('shared incomplete hands')
    for g in groups.values():
        if any(sum(z.values())!=g['observations'] for z in g['models']) or sum(g['transition_counts'].values())!=g['observations']:raise ValueError('shared counts failed reconciliation')
        g['mean_probability_tv']=g['sum_probability_tv']/g['observations']
    if sum(block_counts.values())!=total:raise ValueError('shared blocks failed reconciliation')
    return dict(status='verified',hands_per_arm=count,root=headers[0]['seed'],blocks=headers[0]['blocks'],shared_models=headers[0]['shared_models'],
        observations=total,paired_queries=2*total,query_inventory_sha256=digest.hexdigest(),groups=groups,block_counts=block_counts,
        weighting='Every focal-decision occurrence from both arms equally weighted; each source-arm stratum retained; no key dedup, no return/action/status filtering; repeat is proof only.',
        no_causal_payoff_claim=True)


def ordinary_payload_parity(left,right):
    streams=[evidence.rows(p) for p in (left,right)];headers=[next(s) for s in streams]
    for h in headers:h.pop('shared_models',None)
    if headers[0]!=headers[1]:raise ValueError('diagnostics changed ordinary header')
    count=0
    for count,rows in enumerate(itertools.zip_longest(*streams),1):
        if None in rows:raise ValueError('diagnostics changed hand count')
        for row in rows:
            for lookup in row['lookups']:lookup.pop('shared',None)
        if rows[0]!=rows[1]:raise ValueError('diagnostics changed action/RNG/ordinary trace')
    if count!=headers[0]['hands']:raise ValueError('diagnostics incomplete parity')
    return dict(status='passed',hands=count,ordinary_trace_and_rng_unchanged=True)


def audit_source_rows(traces,catalog):
    """Small qualification only: independently stream original float64 exports."""
    wanted={alias:{} for alias in catalog};pins={};observations=0
    for trace in traces:
        stream=evidence.rows(trace);h=next(stream)
        for spec in h['shared_models']:
            old=pins.setdefault(spec['alias'],spec['pin'])
            if old!=spec['pin']:raise ValueError('shared source pin changed')
        for row in stream:
            for i,actor in enumerate(row['actors']):
                if row['identities'][actor]!=0:continue
                queries=query_rows(row,i,h);observations+=1;code=sum(1<<label for label,_ in menu(row,i))
                owner=(actor-row['button'])%len(row['identities']);street=STREETS.index(row['states'][i]['street']);key=row['lookups'][i]['key']
                for q in queries:
                    value=(owner,street,code,tuple(q['probabilities']),q['status']);old=wanted[q['alias']].setdefault(key,value)
                    if old!=value:raise ValueError('same key queried inconsistently')
    for alias,queries in wanted.items():
        spec=catalog[alias];path=Path(spec['source_policy']);mass=Path(spec['mass']);receipt=json.loads((mass/'receipt.json').read_text())
        if evidence.sha(path)!=spec['source_policy_sha256'] or evidence.sha(mass/'receipt.json')!=spec['mass_sha256'] or pins[alias]['mass_sha256']!=spec['mass_sha256']:raise ValueError('shared source export/mass pins changed')
        zeros=mass/'zero-keys.bin'
        if evidence.sha(zeros)!=receipt['zero_keys_sha256']:raise ValueError('shared zero-key pin changed')
        zero_bytes=zeros.read_bytes()
        if len(zero_bytes)!=16*receipt['zero_mass_rows']:raise ValueError('shared zero-key count differs')
        zero_set={zero_bytes[i:i+16].hex() for i in range(0,len(zero_bytes),16)}
        if len(zero_set)!=receipt['zero_mass_rows']:raise ValueError('shared duplicate zero keys')
        found=set()
        with gzip.open(path,'rt') as f:
            header=json.loads(next(f));rows=0
            if header['source_checkpoint_sha256']!=pins[alias]['source_checkpoint_sha256']:raise ValueError('shared checkpoint pin differs')
            for line in f:
                record=json.loads(line);rows+=1;key=record[0]
                if key not in queries:continue
                status='zero_mass' if key in zero_set else 'positive_mass';expected=tuple(record[1:4])+(tuple(record[4]),status)
                if queries[key]!=expected:raise ValueError('shared float64 source row differs')
                found.add(key)
            if rows!=header['entries']:raise ValueError('shared source export incomplete')
        if any(queries[k][-1]!='missing' for k in queries.keys()-found):raise ValueError('shared nonexistent source row marked found')
    return dict(status='passed',observations=observations,models=len(wanted),exact_float64_source_rows=True,original_mass_tags_verified=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['pair','parity','source']);p.add_argument('paths',type=Path,nargs='+');a=p.parse_args()
    if a.mode=='pair' and len(a.paths)==6:r=verified_diagnostics(*a.paths)
    elif a.mode=='parity' and len(a.paths)==2:r=ordinary_payload_parity(*a.paths)
    elif a.mode=='source' and len(a.paths)>1:r=audit_source_rows(a.paths[1:],json.loads(a.paths[0].read_text()))
    else:raise ValueError('pair6paths,parity2traces,or sourceCATALOG TRACES...')
    print(json.dumps(r,indent=2,allow_nan=False))


if __name__=='__main__':main()
