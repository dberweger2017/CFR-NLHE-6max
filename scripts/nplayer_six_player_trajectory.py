"""All-hand descriptive PR417 trajectory accounting; no game or model execution."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
from scripts import nplayer_paired_evidence as evidence
from scripts.nplayer_trace_divergence import first_divergence

EXPECTED='361e40b70f195d578592d1155738340917d753fdd2cbd3866236adee3bd3e5c1'
CONTRASTS=('3b-10b','10b-15b')
STREETS=('preflop','flop','turn','river')
STATUSES=('positive_mass','zero_mass','missing')


class Accounting:
    def __init__(self,labels,seatings):
        self.labels=labels;self.seatings=seatings;self.hands=0;self.changed=0
        self.delta_chips=0;self.groups={};self.actions={};self.prefix={}
        self.block_sum=0;self.block_n=0;self.block_mean=0.;self.block_m2=0.
    def add(self,a,b):
        first=first_divergence(a,b);focal=a['identities'].index(0)
        if first and first['left_status'] in STATUSES[1:] and first['right_status'] in STATUSES[1:]:
            raise ValueError('identical uniform fallback cannot first diverge')
        delta=b['rewards'][focal]-a['rewards'][focal];self.hands+=1;self.delta_chips+=delta
        if first:
            self.changed+=1;look=first['left_status']+'->'+first['right_status'];action=first['left_action']+'->'+first['right_action']
            size='not-two-raises'
            if action=='raise->raise':size='higher' if first['right_raise_to']>first['left_raise_to'] else 'lower'
            later=[]
            for row in (a,b):
                missing=any(actor==focal and lookup['status']=='missing' for actor,lookup in zip(row['actors'][first['index']+1:],row['lookups'][first['index']+1:]))
                later.append(str(int(missing)))
            dims=dict(street=first['street'],lookup_pair=look,action_pair=action,raise_size_direction=size,position=str(first['position']),street_lookup=first['street']+'/'+look,later_missing=first['street']+'/'+look+'/'+''.join(later))
        else:dims=dict.fromkeys(('street','lookup_pair','action_pair','raise_size_direction','position','street_lookup','later_missing'),'unchanged')
        for dim,key in dims.items():
            g=self.groups.setdefault(dim,{}).setdefault(key,dict(hands=0,sum_delta_chips=0));g['hands']+=1;g['sum_delta_chips']+=delta
        end=first['index'] if first else len(a['actions'])
        for i in range(end):
            if a['actors'][i]!=focal:continue
            if a['lookups'][i]['key']!=b['lookups'][i]['key']:raise ValueError('unchanged prefix key differs')
            key='/'.join((a['states'][i]['street'],a['lookups'][i]['status'],b['lookups'][i]['status'],a['actions'][i][0]))
            self.prefix[key]=self.prefix.get(key,0)+1
        for tag,row in zip(self.labels,(a,b)):
            for actor,state,lookup,action in zip(row['actors'],row['states'],row['lookups'],row['actions']):
                if actor!=focal:continue
                key='/'.join((tag,state['street'],lookup['status'],action[0]));g=self.actions.setdefault(key,dict(decisions=0,sum_raise_to_chips=0))
                g['decisions']+=1
                if action[0]=='raise':g['sum_raise_to_chips']+=action[1]
        self.block_sum+=delta
        if self.hands%self.seatings==0:
            value=self.block_sum*100/(a['bb']*self.seatings);self.block_sum=0;self.block_n+=1
            d=value-self.block_mean;self.block_mean+=d/self.block_n;self.block_m2+=d*(value-self.block_mean)
        return first
    def result(self,bb):
        if not self.hands or self.hands%self.seatings:raise ValueError('incomplete deal block')
        for rows in self.groups.values():
            if sum(g['hands'] for g in rows.values())!=self.hands or sum(g['sum_delta_chips'] for g in rows.values())!=self.delta_chips:raise ValueError('partition reconciliation')
            for g in rows.values():
                g['fraction_hands']=g['hands']/self.hands
                g['conditional_mean_delta_bb100']=g['sum_delta_chips']*100/(bb*g['hands'])
                g['unconditional_contribution_bb100']=g['sum_delta_chips']*100/(bb*self.hands)
        return dict(hands=self.hands,blocks=self.block_n,first_divergences=self.changed,unchanged_hands=self.hands-self.changed,mean_bb100=self.block_mean,standard_error_bb100=math.sqrt(self.block_m2/(self.block_n-1)/self.block_n) if self.block_n>1 else 0.,groups=self.groups,reached_focal_actions=self.actions,matched_prefix_unchanged_actions=self.prefix)


def validate_inventory(m):
    if m['format']!='nplayer-six-player-trajectory-inventory-v1' or m['source_result_sha256']!=EXPECTED or len(m['files'])!=24 or len(m['panels'])!=16:raise ValueError('frozen inventory scope')
    names=[f['name'] for f in m['files']]
    if len(set(names))!=24 or any(Path(n).name!=n for n in names):raise ValueError('unsafe/duplicate file name')
    for f in m['files']:
        p=f['proof']
        if p['status']!='passed' or p['trace_sha256']!=f['sha256'] or p['hands']!=49152:raise ValueError('recorded replay proof differs')
        if any(len(f[k])!=64 or any(c not in '0123456789abcdef' for c in f[k]) for k in ['sha256','proof_sha256']):raise ValueError('invalid recorded digest')
    keys={(p['contrast'],p['field']) for p in m['panels']}
    if len(keys)!=16 or {c for c,f in keys}!=set(CONTRASTS) or len({f for c,f in keys})!=8:raise ValueError('incomplete contrast/field inventory')
    if set(names)!={n for p in m['panels'] for n in p['files']}:raise ValueError('unused/missing input inventory')
    for p in m['panels']:
        if p['blocks']!=4096 or len(evidence.seating(6,p['schedule']))!=12 or p['lookup_labels']!=list(evidence.LABELS):raise ValueError('block/schedule/lookup scope')
    if sum(f['bytes'] for f in m['files'])!=m['transfer_bytes']:raise ValueError('byte inventory differs')


def scan_panel(panel,files,directory):
    headers=[];streams=[];hashes=[];opened=[];acc=Accounting(panel['contrast'].split('-'),len(panel['schedule']))
    try:
        for name in panel['files']:
            p=directory/name
            if p.stat().st_size!=files[name]['bytes']:raise ValueError('input byte count differs')
            f=p.open('rb');opened.append(f);raw=next(f);headers.append(json.loads(raw));hashes.append(hashlib.sha256(raw));streams.append(f)
        a,b=headers;n,s=evidence.header_check(a);evidence.header_check(b)
        if n!=6 or a['seed']!=panel['root'] or a['blocks']!=panel['blocks'] or s!=panel['schedule']:raise ValueError('frozen panel header differs')
        if any(a[k]!=b[k] for k in ['identity','hands','blocks','seed','schedule','distinct_policy_instances']) or a['policies'][1:]!=b['policies'][1:]:raise ValueError('fixed paired field differs')
        if [h['policies'][0]['sha256'] for h in headers]!=panel['focal_sha256s']:raise ValueError('focal checkpoint pins differ')
        for i,lines in enumerate(itertools.zip_longest(*streams)):
            if None in lines:raise ValueError('unequal hand inventory')
            rows=[]
            for line,h,header in zip(lines,hashes,headers):
                h.update(line);row=json.loads(line);evidence.validate_row(row,i,header,n,s);rows.append(row)
            acc.add(*rows)
        if acc.hands!=a['hands'] or [h.hexdigest() for h in hashes]!=[files[n]['sha256'] for n in panel['files']]:raise ValueError('full trace hash/count differs')
        out=acc.result(a['identity']['big_blind']);ref=panel['reference_contrast']
        for key in ['mean_bb100','standard_error_bb100']:
            if not math.isclose(out[key],ref[key],rel_tol=0,abs_tol=1e-8):raise ValueError('verified block contrast differs')
        for tag,counts in zip(acc.labels,panel['reference_focal_coverage']):
            for street,expected in zip(STREETS,counts):
                for status,count in zip(evidence.LABELS,expected):
                    observed=sum(g['decisions'] for key,g in acc.actions.items() if key.startswith('/'.join((tag,street,status))+'/'))
                    if observed!=count:raise ValueError('verified focal lookup counts differ')
        return dict(out,field=panel['field'],contrast=panel['contrast'],trace_sha256=[h.hexdigest() for h in hashes],reference_contrast=ref,no_exclusions=True)
    finally:
        for f in opened:f.close()


def run(inventory,directory,output):
    if output.exists():raise FileExistsError('output exists; preserve attempts')
    raw=inventory.read_bytes();m=json.loads(raw);validate_inventory(m);files={f['name']:f for f in m['files']};panels={}
    for f in files.values():
        p=directory/f['name']
        if not p.is_file() or p.stat().st_size!=f['bytes']:raise ValueError('complete input set required')
    for panel in m['panels']:
        panels[panel['contrast']+'/'+panel['field']]=scan_panel(panel,files,directory)
    if inventory.read_bytes()!=raw:raise ValueError('inventory mutated')
    result=dict(status='complete-descriptive-diagnosis',inventory_sha256=hashlib.sha256(raw).hexdigest(),source_result_sha256=EXPECTED,unique_input_files=24,unique_physical_hands=m['unique_hands'],paired_hand_comparisons=sum(p['hands'] for p in panels.values()),panels=panels,limitations=['Previously inspected deals; descriptive associations only, no new strength confirmation.','First changed sampled action does not identify the first changed probability distribution.','Group whole-hand return contributions are additive partitions, not causal action values.','Reached actions and post-divergence missing exposure use different histories.','One training lineage and two circular orders; no general or cross-seed conclusion.','No new hands, models, policies, training, search, off-tree solving or release changes.'])
    with output.open('x') as f:json.dump(result,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--traces',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.inventory,a.traces,a.output)


if __name__=='__main__':main()
