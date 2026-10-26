"""Saved public cases21/91: cap-excluded all-ins and idempotent BP fallback.

Qualification only. Forced legal public paths are not observed policy actions,
new poker samples or evidence of the value of an alternative continuation.
"""
import argparse
import copy
import json
from pathlib import Path
from time import monotonic

from scripts.qualify_river_continuation import solve_request
from scripts.river_search_panel import Worker
from scripts.river_whole_hand_pilot import FOCAL_SHA, sha, write

PANEL_SHA='f5b6b2706a0b6ee8912a52961b6b8e2795158bd982bea18fa43227f74924b919'


def check(args):
    if sha(args.panel)!=PANEL_SHA:
        raise ValueError('saved public panel changed')
    cases=json.loads(args.panel.read_text())['cases']
    worker=Worker(args.binary,args.k50,args.focal,FOCAL_SHA)
    proofs=[]
    try:
        for index,path in [(21,[900,1800,6300,9600]),(91,[800,1600,5600,9600])]:
            request=solve_request(cases[index],'deployment','pot-jam-cap3-root-min-responses-v1')
            request['omitted']=False
            begin=worker.ask({'mode':'retained-begin','hand_id':f'public-control-{index}','observation':request})
            if begin['status']!='ok' or not begin['result']['session']['installed_search']:
                raise ValueError('saved qualified control did not install')
            context={'hand_id':f'public-control-{index}','handle':begin['result']['session']['handle']}
            observation=copy.deepcopy(cases[index]['request']);observation.pop('mode',None)
            seat=observation['seat'];live=[i for i,p in enumerate(observation['players']) if not p[3]]
            opponent=next(i for i in live if i!=seat)
            for i,to in enumerate(path):
                actor=seat if i%2==0 else opponent
                player=observation['players'][actor];paid=to-player[1]
                if paid<0 or paid>player[0]:raise ValueError('invalid forced public payment')
                player[0]-=paid;player[1]=to;player[2]+=paid
                observation['actions'].append([actor,3,'raise',to,paid])
            own=observation['players'][seat]
            observation['legal']={'check':False,'call_amount':min(own[0],path[-1]-own[1]),'raise_to':None}
            req={'mode':'retained-continue',**context,'observation':observation}
            first=worker.ask(req);second=worker.ask(req)
            if first['status']!='ok' or second['status']!='ok' or first['result']!=second['result']:
                raise ValueError('continuation is not idempotent')
            result=first['result'];entry=result['off_tree_entry']
            if (result['solver_advances']!=0 or result['installed_search'] is not False
                    or result['fallback_reason']!='off-tree action; blueprint for rest of river'
                    or not entry['cap_reached'] or not entry['all_in']
                    or entry['action']!=['raise',9600] or entry['raises_before']!=3):
                raise ValueError('cap/all-in fallback differs')
            worker.ask({'mode':'retained-release',**context})
            proofs.append({'case_index':index,'profile_sha256':begin['result']['session']['binding']['profile_sha256'],
                           'forced_path':path,'result':result})
    finally:
        worker.close()
    return {'status':'passed','panel_sha256':PANEL_SHA,'startup':worker.ready,'controls':proofs,
            'scope':'forced legal public continuation qualification; no strength or deployment-frequency inference'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('binary','k50','focal','panel','out'):p.add_argument('--'+key,type=Path,required=True)
    args=p.parse_args()
    if args.out.exists():p.error('fresh output required')
    tick=monotonic();result=check(args);result['wall_seconds']=monotonic()-tick;write(args.out,result)


if __name__=='__main__':main()
