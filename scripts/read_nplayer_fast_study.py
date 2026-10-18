"""Read paired strength only after the complete PR335 matrix verifies."""
import argparse
from itertools import zip_longest
import json
from pathlib import Path
import statistics

from scripts.analyze_nplayer_arena import PERMUTATIONS, interval, sha
from scripts.run_nplayer_fast_study import SEEDS, cases


def paired_blocks(left,right,expected_root):
    a,b=Path(left).open(),Path(right).open()
    try:
        x,y=json.loads(next(a)),json.loads(next(b))
        if x['seed']!=expected_root or y['seed']!=expected_root:raise ValueError('paired root mismatch')
        if x['blocks']!=y['blocks'] or x['identity']!=y['identity']:raise ValueError('paired metadata mismatch')
        bb=x['identity']['big_blind'];current=[];count=0
        for index,(u,v) in enumerate(zip_longest(a,b)):
            if u is None or v is None:raise ValueError('paired trace length mismatch')
            u,v=json.loads(u),json.loads(v);block,p=divmod(index,6)
            for row in [u,v]:
                if row['block']!=block or row['permutation']!=p or tuple(row['identities'])!=PERMUTATIONS[p]:raise ValueError('paired block/permutation mismatch')
                if sum(row['rewards'])!=0:raise ValueError('nonzero-sum payoff')
            if u['deck']!=v['deck']:raise ValueError('paired deals differ')
            values=[row['rewards'][row['identities'].index(0)]*100/bb for row in [u,v]]
            seat=u['identities'].index(0)
            current.append((values,seat,(seat-block%3)%3));count+=1
            if p==5:
                left_mean=statistics.mean(row[0][0] for row in current);right_mean=statistics.mean(row[0][1] for row in current)
                detail={}
                for label,column in [('fast',0),('production',1)]:
                    for group,index in [('seat',1),('position',2)]:
                        detail[label+'_by_'+group]=[statistics.mean(row[0][column] for row in current if row[index]==i) for i in range(3)]
                yield dict(advantage=(left_mean-right_mean)/2,fast_singleton=left_mean,production_singleton=right_mean,**detail)
                current=[]
        if current or count!=6*x['blocks']:raise ValueError('incomplete paired blocks')
    finally:a.close();b.close()


def global_gate(root):
    if (root/'failure.json').exists():raise ValueError('campaign failed; no settled readout')
    status=json.loads((root/'status.json').read_text())
    if status['status']!='all-science-verified-readout-ready':raise ValueError('campaign has not passed its global barrier')
    manifest=json.loads((root/'evaluation-manifest.json').read_text())
    verified=json.loads((root/'evaluation-verified.json').read_text())
    if manifest['cases']!=cases() or verified['status']!='passed' or verified['final_hands']!=589824 or verified['manifest_sha256']!=sha(root/'evaluation-manifest.json'):raise ValueError('global matrix mismatch')
    for case in cases():
        d=root/'evaluation'/case['name'];result=json.loads((d/'result.json').read_text());replay=json.loads((d/'replay.json').read_text())
        if result['status']!='passed' or result['case']!=case or result['hands']!=49152 or replay['status']!='passed' or replay['hands']!=49152:raise ValueError('unverified case')
        digest=sha(d/'play-0.jsonl')
        if digest!=result['trace_sha256'] or digest!=replay['trace_sha256'] or digest!=sha(d/'play-1.jsonl'):raise ValueError('trace verification mismatch')
    return manifest


def read(root):
    manifest=global_gate(root)
    rows=[]
    for seed in SEEDS:
        for scope in ['nodes','clock']:
            pair=[c for c in cases() if c['seed']==seed and c['scope']==scope]
            blocks=list(paired_blocks(root/'evaluation'/pair[0]['name']/'play-0.jsonl',root/'evaluation'/pair[1]['name']/'play-0.jsonl',pair[0]['root']))
            if len(blocks)!=8192:raise ValueError('wrong statistical block count')
            detail={key:[interval([b[key][i] for b in blocks]) for i in range(3)] for key in
                ['fast_by_seat','production_by_seat','fast_by_position','production_by_position']}
            rows.append(dict(seed=seed,scope=scope,blocks=len(blocks),advantage=interval([b['advantage'] for b in blocks]),
                fast_singleton=interval([b['fast_singleton'] for b in blocks]),production_singleton=interval([b['production_singleton'] for b in blocks]),**detail))
    return dict(status='settled',rows=rows,final_hands=589824,reproduction_hands=589824,
        equal_node_noninferiority_passed=all(r['advantage']['lower95_bb100']>-5 for r in rows if r['scope']=='nodes'),
        equal_time_consistent_gain_passed=all(r['advantage']['lower95_bb100']>0 for r in rows if r['scope']=='clock'),
        manifest_sha256=sha(root/'evaluation-manifest.json'),models=manifest['models'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();result=read(a.root)
    with a.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['rows','models']}))
