"""Outcome-blind public-state extraction and conditional Monte Carlo readout."""
import argparse
from collections import Counter,defaultdict
import hashlib
import heapq
import json
import math
from pathlib import Path
import statistics


def digest(*parts):
    return hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).hexdigest()


def legal_state(row,index,*,seed,field,reached,root):
    """The only projection from privileged trace to belief input. No deck/payoff access."""
    public=row['states'][index];hero=public['actor']
    if row['identities'][hero]!=0:raise ValueError('not the singleton observation')
    names=['random']*3
    for seat,identity in enumerate(row['identities']):
        names[seat]='hero' if identity==0 else ('tight-aggressive' if field=='random-tight' and identity==2 else 'random')
    block=row['block']
    split='discovery' if int(digest('block-split',seed,root,block),16)%2==0 else 'heldout'
    street=('preflop','flop','turn','river').index(public['street'])
    return dict(id=digest('state',seed,field,reached,block,row['permutation'],index),hero=hero,button=row['button'],
        hole=list(public['holes'][hero]),board=list(public['board']),
        actions=[[actor,*action] for actor,action in zip(row['actors'][:index],row['actions'][:index])],
        opponents=names,street=street,expected_key=row['lookups'][index]['key'],
        stratum=f'{field}:{reached}:{street}',split=split)


def extract(tasks,out,limit=32):
    """One perm/decision per six-hand block; priority sample each declared stratum."""
    if limit!=32:raise ValueError('fixed observation sample size')
    buckets=defaultdict(list);eligible=Counter();source_hands=0
    for t in tasks:
        for street in range(4):
            for split in ('discovery','heldout'):
                k=f"{t['field']}:{t['reached']}:{street}:{split}";buckets[k]=[];eligible[k]=0
    for task in tasks:
        path=Path(task['path'])
        with path.open('rb') as f:
            if hashlib.file_digest(f,'sha256').hexdigest()!=task['sha256']:raise ValueError('trace pin differs')
        with path.open() as f:
            header=json.loads(next(f))
            if header['seed']!=task['root'] or header['blocks']!=8192:raise ValueError('archived schedule differs')
            for line in f:
                row=json.loads(line);source_hands+=1
                if row['permutation']!=int(digest('permutation',task['seed'],task['root'],row['block']),16)%6:continue
                ordinal=int(digest('decision',task['seed'],task['root'],row['block']),16)%16
                seen=0;i=None
                for index,actor in enumerate(row['actors']):
                    if row['identities'][actor]!=0:continue
                    if seen==ordinal:i=index;break
                    seen+=1
                if i is None:continue
                state=legal_state(row,i,seed=task['seed'],field=task['field'],reached=task['reached'],root=task['root'])
                key=state['stratum']+':'+state['split'];eligible[key]+=1
                priority=int(digest('priority',state['id']),16)
                bucket=buckets[key];item=(-priority,state['id'],state)
                if len(bucket)<limit:heapq.heappush(bucket,item)
                elif priority < -bucket[0][0]:heapq.heapreplace(bucket,item)
    out=Path(out)
    with out.open('x') as f:
        for key,bucket in sorted(buckets.items()):
            for _,_,state in sorted(bucket,key=lambda x:(-x[0],x[1])):f.write(json.dumps(state,sort_keys=True)+'\n')
    return dict(status='passed',source_hands=source_hands,eligible=dict(eligible),retained={k:len(v) for k,v in buckets.items()},
        states=sum(map(len,buckets.values())),states_sha256=hashlib.file_digest(out.open('rb'),'sha256').hexdigest(),
        limits='Fixed per-stratum sample, not a population-weighted estimate; whole-block discovery split.')


def interval(values,critical,width):
    if len(values)!=512 or any(not math.isfinite(x) for x in values):raise ValueError('heldout world count/numerics differ')
    mean=statistics.mean(values);se=statistics.stdev(values)/len(values)**0.5
    log=math.log(4*512/.05)
    radius=math.sqrt(2*statistics.variance(values)*log/len(values))+7*width*log/(3*(len(values)-1))
    return dict(mean=mean,standard_error=se,lower=mean-radius,upper=mean+radius,
        range_width=width,normal_lower=mean-critical*se,normal_upper=mean+critical*se)


def readout(folder):
    folder=Path(folder);m=json.loads((folder/'manifest.json').read_text());native=json.loads((folder/'native-result.json').read_text())
    if native['status']!='passed':raise ValueError('native result missing')
    if native.get('manifest_sha256')!=hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest():raise ValueError('manifest changed')
    for field,file in [('matched','matched.jsonl'),('selected','selected.jsonl'),('values','values.jsonl')]:
        with (folder/file).open('rb') as f:
            if hashlib.file_digest(f,'sha256').hexdigest()!=native[field+'_sha256']:raise ValueError('native output changed')
    matched_stats=defaultdict(lambda:dict(count=0,tv=0.,baseline=Counter(),candidate=Counter(),mass=Counter()))
    with (folder/'matched.jsonl').open() as f:
        for line in f:
            r=json.loads(line);s=r['state'];g=matched_stats[s['stratum']+':'+s['split']];g['count']+=1;g['tv']+=r['total_variation'];g['mass']['->'.join(r['statuses'])]+=1
            for index,name in enumerate(('baseline','candidate')):
                for action,p in zip(r['actions'],r['probabilities'][index]):g[name][action[0]]+=p
    for g in matched_stats.values():
        g['mean_total_variation']=g.pop('tv')/g['count']
        for name in ('baseline','candidate'):g[name]={a:v/g['count'] for a,v in g[name].items()}
    selected={}
    with (folder/'selected.jsonl').open() as f:
        for line in f:
            r=json.loads(line);key=r['matched']['state']['id']
            if key in selected:raise ValueError('duplicate selected state')
            selected[key]=r
    worlds=defaultdict(dict)
    with (folder/'values.jsonl').open() as f:
        for line in f:
            r=json.loads(line);sid=r['state_id'];i=r['world']
            if sid not in selected or i in worlds[sid] or not 0<=i<512:raise ValueError('world identity differs')
            worlds[sid][i]=r
    # Upper family size32 states ×2 continuation recipes ×(2 primary contrasts
    # +at most6 action-vs-passive contrasts), fixed before outcomes.
    critical=statistics.NormalDist().inv_cdf(1-.05/(2*512))
    panel=[]
    for sid,r in selected.items():
        if set(worlds[sid])!=set(range(512)):raise ValueError('incomplete heldout worlds')
        p0,p1=r['matched']['probabilities'];actions=r['matched']['actions'];best=r['selected_action_index'];n=len(actions)
        if len(p0)!=n or len(p1)!=n or not 0<=best<n:raise ValueError('selected menu identity differs')
        reference=next((i for i,a in enumerate(actions) if a[0] in ('check','call')),0)
        shares=[worlds[sid][i]['showdown_share'] for i in range(512)]
        if any(not math.isfinite(v) or not 0<=v<=1 for v in shares):raise ValueError('invalid belief showdown share')
        equity=dict(mean=statistics.mean(shares),standard_error=statistics.stdev(shares)/512**0.5,scope='Current live players reaching showdown on independent belief runouts; descriptive card equity, not strategy value')
        for continuation in range(2):
            qs=[worlds[sid][i]['q'][continuation] for i in range(512)]
            if any(len(q)!=n or any(not math.isfinite(v) or not -100<=v<=200 for v in q) for q in qs):raise ValueError('invalid branch payoff')
            base=[sum(p*x for p,x in zip(p0,q)) for q in qs];cand=[sum(p*x for p,x in zip(p1,q)) for q in qs]
            contrasts=[interval([q[a]-q[reference] for q in qs],critical,0. if a==reference else 600.) for a in range(n)]
            mean_q=[statistics.mean(q[a] for q in qs) for a in range(n)]
            panel.append(dict(state_id=sid,state=r['matched']['state'],continuation=('baseline','candidate')[continuation],
                actions=actions,probabilities=[p0,p1],visible_strength=r['matched'].get('visible_strength'),belief_showdown_share=equity,action_values_bb=mean_q,reference_action=reference,
                action_minus_passive=contrasts,mixture_candidate_minus_baseline_bb=interval([a-b for a,b in zip(cand,base)],critical,300*sum(abs(b-a) for a,b in zip(p0,p1))),
                selected_minus_candidate_bb=interval([q[best]-c for q,c in zip(qs,cand)],critical,300*sum(abs((1. if i==best else 0.)-p) for i,p in enumerate(p1))),
                selected_action=best,belief=r['belief'],
                contributions_bb=[(b-a)*(q-mean_q[reference]) for a,b,q in zip(p0,p1,mean_q)]))
    return dict(status='settled',native=native,extraction=json.loads((folder/'extraction.json').read_text()) if (folder/'extraction.json').exists() else None,matched=dict(matched_stats),panel=panel,family_size_upper_bound=512,
        critical=critical,interval_method='Primary: two-sided empirical Bernstein, Maurer-Pontil2009 theorem4, Bonferroni upper family512 at95%; width300*L1(coefficients),512 iid heldout worlds conditional on selected observation/discovery. Normal intervals auxiliary; not a full-policy strength CI',
        limitations='Targeted discovery-state selection; one state per stratum at most; known scripted beliefs only; action/continuation contrasts do not identify aggregate win-rate regression or Nash convergence.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['extract','read']);p.add_argument('folder',type=Path);a=p.parse_args()
    if a.mode=='extract':value=extract(json.loads((a.folder/'trace-inputs.json').read_text()),a.folder/'legal-states.jsonl')
    else:value=readout(a.folder)
    (a.folder/('extraction.json' if a.mode=='extract' else 'results.json')).write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(status=value['status'])))


if __name__=='__main__':main()
