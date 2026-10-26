"""Descriptive first-divergence accounting of the already verified PR415 traces."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
from scripts import nplayer_paired_evidence as evidence

EXPECTED='cdf3d1430b216afdbe28f4d9728f8668f76cd6e42932cb7f6f2e25902a3306be'


def public(state):
    return {k:v for k,v in state.items() if k not in ('holes','rewards')}


def first_divergence(left,right):
    for key in ('hand','block','permutation','identities','deck','button','stacks','sb','bb'):
        if left[key]!=right[key]:raise ValueError('paired deal/identity mismatch')
    focal=left['identities'].index(0)
    for i,(a,b) in enumerate(itertools.zip_longest(left['actions'],right['actions'])):
        if a is None or b is None:raise ValueError('unequal trajectory before action divergence')
        if left['actors'][i]!=right['actors'][i] or public(left['states'][i])!=public(right['states'][i]):raise ValueError('state/actor mismatch before divergence')
        if a!=b:
            if left['actors'][i]!=focal:raise ValueError('fixed opponent diverged before focal')
            la,lb=left['lookups'][i],right['lookups'][i]
            if la['key']!=lb['key']:raise ValueError('same observed state has different key')
            if la['status']=='missing' and lb['status']=='missing':raise ValueError('same uniform missing fallback diverged')
            return dict(index=i,street=left['states'][i]['street'],position=(focal-left['button'])%len(left['identities']),
                left_status=la['status'],right_status=lb['status'],left_action=a[0],right_action=b[0],left_raise_to=a[1],right_raise_to=b[1])
    if left['rewards']!=right['rewards'] or left['settlement']!=right['settlement']:raise ValueError('unchanged trajectory has different payoff')
    return None


class Accounting:
    def __init__(self):self.groups={};self.hands=0;self.delta=0;self.actions={};self.first_count=0
    def add(self,left,right):
        first=first_divergence(left,right);focal=left['identities'].index(0);delta=(right['rewards'][focal]-left['rewards'][focal])*100/left['bb'];self.hands+=1;self.delta+=delta
        dimensions={'street':'unchanged','lookup_pair':'unchanged','action_pair':'unchanged','position':'unchanged','street_lookup':'unchanged'}
        if first:
            self.first_count+=1;dimensions=dict(street=first['street'],lookup_pair=first['left_status']+'→'+first['right_status'],action_pair=first['left_action']+'→'+first['right_action'],position=str(first['position']),street_lookup=first['street']+'/'+first['left_status']+'→'+first['right_status'])
        for dim,key in dimensions.items():
            row=self.groups.setdefault(dim,{}).setdefault(key,dict(hands=0,sum_delta_bb100=0.));row['hands']+=1;row['sum_delta_bb100']+=delta
        for arm,row in zip(('3B','10B'),(left,right)):
            for actor,state,lookup,action in zip(row['actors'],row['states'],row['lookups'],row['actions']):
                if actor!=focal:continue
                key='/'.join((arm,state['street'],lookup['status'],action[0]));z=self.actions.setdefault(key,dict(decisions=0,raise_to_sum_bb=0.,raise_to_over_pot_sum=0.))
                z['decisions']+=1
                if action[0]=='raise':
                    z['raise_to_sum_bb']+=action[1]/row['bb'];z['raise_to_over_pot_sum']+=action[1]/max(row['bb'],state['pot'])
        return first
    def result(self):
        for rows in self.groups.values():
            if sum(z['hands'] for z in rows.values())!=self.hands:raise ValueError('group counts do not reconcile')
            if abs(sum(z['sum_delta_bb100'] for z in rows.values())-self.delta)>1e-7:raise ValueError('group returns do not reconcile')
            for z in rows.values():z['contribution_bb100']=z['sum_delta_bb100']/self.hands
        return dict(hands=self.hands,first_divergences=self.first_count,no_divergence_hands=self.hands-self.first_count,
            paired_mean_bb100=self.delta/self.hands,first_divergence_groups=self.groups,reached_focal_action_groups=self.actions)


def run(input_root,output):
    if output.exists():raise FileExistsError('diagnosis output exists; no retry')
    root=Path(input_root);raw=root/'results.json';status=json.loads((root/'status.json').read_text());digest=evidence.sha(raw)
    if digest!=EXPECTED or status['status']!='complete' or status['result_sha256']!=digest or (root/'failure.json').exists():raise ValueError('verified PR415 result required')
    old=json.loads(raw.read_text());manifest=json.loads((root/'initial-manifest.json').read_text());verified=json.loads((root/'evaluation-verified.json').read_text())
    if verified['status']!='passed' or verified['initial_hands']!=655360 or evidence.sha(root/'initial-manifest.json')!=verified['manifests']['initial']:raise ValueError('PR415 proof differs')
    fields={}
    for case in manifest['cases']:
        streams=[];headers=[];hashes=[];files=[];account=Accounting();name=case['name'];cost=json.loads(Path(case['summary']).read_text())
        try:
            for path in case['traces']:
                f=Path(path).open('rb');files.append(f);line=next(f);h=hashlib.sha256(line);hashes.append(h);headers.append(json.loads(line));streams.append(f)
            left,right=headers;n,schedule=evidence.header_check(left);evidence.header_check(right)
            if n!=5 or any(left[k]!=right[k] for k in ('identity','hands','blocks','seed','schedule','distinct_policy_instances')) or left['policies'][1:]!=right['policies'][1:]:raise ValueError('paired headers differ')
            for i,lines in enumerate(itertools.zip_longest(*streams)):
                if None in lines:raise ValueError('unequal hand count')
                rows=[]
                for line,h in zip(lines,hashes):h.update(line);rows.append(json.loads(line))
                for row,header in zip(rows,headers):evidence.validate_row(row,i,header,n,schedule)
                account.add(*rows)
            if account.hands!=left['hands'] or [h.hexdigest() for h in hashes]!=cost['trace_sha256']:raise ValueError('trace count/hash differs')
            result=account.result();pair=old['pairs'][name]
            if abs(result['paired_mean_bb100']-pair['contrast']['mean_bb100'])>1e-8:raise ValueError('paired return failed reconciliation')
            # Reached focal counters must also match the independently verified coverage totals.
            for arm,coverage in zip(('3B','10B'),pair['coverage']):
                for street,counts in zip(('preflop','flop','turn','river'),coverage['by_identity'][0]):
                    for label,count in zip(pair['lookup_labels'],counts):
                        observed=sum(z['decisions'] for k,z in account.actions.items() if k.startswith(arm+'/'+street+'/'+label+'/'))
                        if observed!=count:raise ValueError('lookup counts failed reconciliation')
            fields[name]=dict(result,trace_sha256=cost['trace_sha256'],root=case['root'],blocks=left['blocks'],seatings=len(schedule))
        finally:
            for f in files:f.close()
    if len(fields)!=8:raise ValueError('incomplete field inventory')
    result=dict(status='complete-descriptive-diagnosis',input_results_sha256=digest,initial_hands=655360,fields=fields,
        limitations=['Already inspected outcomes; descriptive localization, not fresh confirmation or causal attribution.','Full sampled trajectories only, no full policy probabilities or legal-belief alternative values.','After divergence reached histories differ. Category contributions reconcile but do not identify causal action value.','No new hands, training, rollouts, native model loads or outcome-selected exclusions.'])
    with output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.input_root,a.output)


if __name__=='__main__':main()
