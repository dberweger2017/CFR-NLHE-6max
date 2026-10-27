"""Independent replay and proof-gated paired block statistics, N=4..6."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics


LABELS=('positive_mass','zero_mass','missing','not_applicable')


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def seating(n,rows=None):
    if type(n) is not int or n not in (3,4,5,6):raise ValueError('three to six players required')
    rows=rows if rows is not None else [[(s+r)%n for s in range(n)] for r in range(n)]
    if not rows or len(rows)>720 or len(rows)%n:raise ValueError('schedule count')
    if any(any(type(x) is not int for x in r) or sorted(r)!=list(range(n)) for r in rows) or len({tuple(r) for r in rows})!=len(rows):raise ValueError('schedule permutations')
    if any(sum(row[s]==i for row in rows)!=len(rows)//n for i in range(n) for s in range(n)):raise ValueError('unbalanced schedule')
    return rows


def header_check(h):
    n=h['identity']['players'];schedule=seating(n,h['schedule'])
    if (h['format']!='nplayer-privileged-policy-replay-v1' or h['harness']!='nplayer-paired-v1'
            or type(h['blocks']) is not int or h['blocks']<2 or h['hands']!=h['blocks']*len(schedule)
            or h['distinct_policy_instances']!=n or len(h['policies'])!=n):raise ValueError('paired header')
    return n,schedule


def rows(path):
    with Path(path).open() as f:
        header=json.loads(next(f));yield header
        yield from (json.loads(line) for line in f)


def validate_row(row,index,h,n,schedule):
    block,rotation=divmod(index,len(schedule))
    if (row['hand']!=index or row['block']!=block or row['permutation']!=rotation
            or row['identities']!=schedule[rotation] or row['button']!=block%n
            or row['stacks']!=h['identity']['stacks'] or row['sb']!=h['identity']['small_blind']
            or row['bb']!=h['identity']['big_blind'] or len(row['rewards'])!=n
            or any(type(v) is not int for v in row['rewards']) or sum(row['rewards'])!=0):raise ValueError('row schedule/game/accounting')
    if len(row['lookups'])!=len(row['actions']) or len(row['actors'])!=len(row['actions']) or len(row['states'])!=len(row['actions'])+1:raise ValueError('decision count')
    for actor,state,lookup in zip(row['actors'],row['states'],row['lookups']):
        status=lookup['status'];identity=row['identities'][actor]
        if status not in LABELS:raise ValueError('unknown mass label')
        if 'script' in h['policies'][identity]:
            if lookup!={'status':'not_applicable'}:raise ValueError('script has model lookup')
        else:
            street=('preflop','flop','turn','river').index(state['street'])
            if (status=='not_applicable' or lookup['identity']!=identity or lookup['seat']!=actor
                    or lookup['position']!=(actor-row['button'])%n or lookup['street']!=street
                    or len(lookup['key'])!=32 or any(c not in '0123456789abcdef' for c in lookup['key'])):raise ValueError('lookup coordinates/key')


def replay(path):
    from scripts.check_nplayer_parity import engine_identity, record
    stream=rows(path);h=next(stream);n,schedule=header_check(h);count=decisions=0;deck=None
    for count,row in enumerate(stream,1):
        validate_row(row,count-1,h,n,schedule)
        if row['permutation']==0:deck=row['deck']
        if row['deck']!=deck:raise ValueError('duplicate block deck differs')
        oracle=record(row['hand'],n,preset=row)
        for field in ('actions','states','history','settlement'):
            if row[field]!=oracle[field]:raise ValueError(f'independent replay differs:{count-1}:{field}')
        if row['rewards']!=oracle['states'][-1]['rewards'] or row['actors']!=[s['actor'] for s in oracle['states'][:-1]]:raise ValueError('independent rewards/actors differ')
        decisions+=len(row['actions'])
    if count!=h['hands']:raise ValueError('missing hands')
    return dict(status='passed',trace_sha256=sha(path),hands=count,decisions=decisions,engine=engine_identity(),players=n)


def interval(values):
    from scripts.analyze_nplayer_arena import interval as student
    if all(v==0 for v in values):return dict(mean_bb100=0.,standard_error_bb100=0.,lower95_bb100=0.,upper95_bb100=0.)
    return student(values)


def verified_pair(a,b,repeat_a,repeat_b,proof_a,proof_b):
    receipts=[]
    for trace,repeat,proof in ((a,repeat_a,proof_a),(b,repeat_b,proof_b)):
        p=json.loads(Path(proof).read_text())
        if p['status']!='passed' or p['trace_sha256']!=sha(trace) or sha(repeat)!=sha(trace):raise ValueError('replay/reproduction barrier')
        receipts.append(p)
    streams=[rows(a),rows(b)];headers=[next(s) for s in streams];n,schedule=header_check(headers[0]);header_check(headers[1])
    left,right=headers
    if any(p['hands']!=h['hands'] or p['players']!=n for p,h in zip(receipts,headers)):raise ValueError('incomplete replay count')
    if any(left[k]!=right[k] for k in ('identity','hands','blocks','seed','schedule','distinct_policy_instances')) or left['policies'][1:]!=right['policies'][1:]:raise ValueError('paired field/root/schedule differs')
    coverage=[dict(by_identity=[[[0]*4 for _ in range(4)] for _ in range(n)],by_seat=[[[0]*4 for _ in range(4)] for _ in range(n)],by_position=[[[0]*4 for _ in range(4)] for _ in range(n)]) for _ in range(2)]
    values=[];seat_values=[[] for _ in range(n)];position_values=[[] for _ in range(n)];contrast=0;seat=[[] for _ in range(n)];position=[[] for _ in range(n)];count=0
    for count,pair in enumerate(itertools.zip_longest(*streams),1):
        if None in pair:raise ValueError('paired hand counts differ')
        l,r=pair
        for row,h in zip(pair,headers):validate_row(row,count-1,h,n,schedule)
        if any(l[k]!=r[k] for k in ('hand','block','permutation','identities','deck','button','stacks')):raise ValueError('paired deals/seating differ')
        focal=l['identities'].index(0);delta=r['rewards'][focal]-l['rewards'][focal]
        contrast+=delta;seat[focal].append(delta*100/l['bb']);position[(focal-l['button'])%n].append(delta*100/l['bb'])
        for arm,row in enumerate(pair):
            for actor,state,lookup in zip(row['actors'],row['states'],row['lookups']):
                street=('preflop','flop','turn','river').index(state['street']);label=LABELS.index(lookup['status'])
                for key,index in (('by_identity',row['identities'][actor]),('by_seat',actor),('by_position',(actor-row['button'])%n)):
                    coverage[arm][key][index][street][label]+=1
        if count%len(schedule)==0:
            values.append(contrast*100/l['bb']/len(schedule));contrast=0
            for j in range(n):
                seat_values[j].append(statistics.mean(seat[j]));position_values[j].append(statistics.mean(position[j]))
            seat=[[] for _ in range(n)];position=[[] for _ in range(n)]
    if count!=left['hands'] or len(values)!=left['blocks']:raise ValueError('paired block counts differ')
    same=left['policies']==right['policies']
    if same and (sha(a)!=sha(b) or any(v!=0 for v in values)):raise ValueError('self comparison is not byte-identical/zero')
    return dict(status='verified',players=n,blocks=len(values),hands_per_arm=count,root=left['seed'],schedule=schedule,
        statistic='focal B minus A; mean within independent deal blocks, BB/100; no reciprocal halving',
        contrast=interval(values),block_values_bb100=values,by_seat=[interval(v) for v in seat_values],by_position=[interval(v) for v in position_values],
        lookup_labels=LABELS,coverage=coverage,self_comparison=same,self_exact_zero=same and all(v==0 for v in values),
        no_strength_claim=True)


def audit_lookup_labels(traces,catalog):
    """Qualify tags independently by streaming original exports and audited mass.

    This is a qualification tool for gzip fixture exports, not a requirement to
    reparse mature weights for every production batch.
    """
    import gzip
    import mmap
    wanted={};pins={};lookups=0
    for trace in traces:
        stream=rows(trace);header=next(stream)
        for pin in header['policies']:
            if 'sha256' in pin:
                old=pins.setdefault(pin['sha256'],pin)
                if old!=pin:raise ValueError('same policy has differing mass pins')
        for row in stream:
            for lookup in row['lookups']:
                if lookup['status']=='not_applicable':continue
                digest=header['policies'][lookup['identity']]['sha256']
                group=wanted.setdefault(digest,{})
                labels=group.setdefault(lookup['key'],set());labels.add(lookup['status']);lookups+=1
    by_digest={v['sha256']:v for v in catalog.values()}
    counts={label:0 for label in LABELS[:3]}
    for digest,queries in wanted.items():
        spec=by_digest[digest];policy=Path(spec['path']);receipt=Path(spec['mass'])/'receipt.json'
        if sha(policy)!=digest or sha(receipt)!=spec['mass_sha256'] or pins[digest]['mass_sha256']!=spec['mass_sha256']:raise ValueError('coverage source/mass pin changed')
        mass=json.loads(receipt.read_text());zeros=receipt.parent/'zero-keys.bin'
        if sha(zeros)!=mass['zero_keys_sha256'] or zeros.stat().st_size!=16*mass['zero_mass_rows']:raise ValueError('coverage zero keys changed')
        def contains(data,key):
            lo=0;hi=len(data)//16
            while lo<hi:
                mid=(lo+hi)//2
                if data[mid*16:(mid+1)*16]<key:lo=mid+1
                else:hi=mid
            return lo<len(data)//16 and data[lo*16:(lo+1)*16]==key
        found=set()
        with zeros.open('rb') as z,gzip.open(policy,'rt') as f:
            data=mmap.mmap(z.fileno(),0,access=mmap.ACCESS_READ) if zeros.stat().st_size else b''
            try:
                header=json.loads(next(f))
                if header['source_checkpoint_sha256']!=mass['checkpoint_sha256'] or mass['policy_sha256']!=digest or header['entries']!=mass['rows']:raise ValueError('coverage source lineage/counts')
                count=0
                for line in f:
                    record=json.loads(line);count+=1;key=record[0]
                    if key not in queries:continue
                    status='zero_mass' if contains(data,bytes.fromhex(key)) else 'positive_mass'
                    if queries[key]!={status}:raise ValueError('independent mass classification differs')
                    found.add(key);counts[status]+=1
                if count!=header['entries']:raise ValueError('coverage export incomplete')
                for key in queries.keys()-found:
                    if queries[key]!={'missing'}:raise ValueError('key incorrectly classified as found')
                    counts['missing']+=1
            finally:
                if hasattr(data,'close'):data.close()
    return dict(status='passed',decision_tags=lookups,distinct_queried_keys_by_status=counts,source_policies=len(wanted),no_uniform_probability_inference=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('replay','pair','coverage'));p.add_argument('paths',nargs='+',type=Path);a=p.parse_args()
    if a.mode=='replay' and len(a.paths)==1:value=replay(a.paths[0])
    elif a.mode=='pair' and len(a.paths)==6:value=verified_pair(*a.paths)
    elif a.mode=='coverage' and len(a.paths)>1:value=audit_lookup_labels(a.paths[1:],json.loads(a.paths[0].read_text()))
    else:raise ValueError('replay TRACE or pair A B REPEAT_A REPEAT_B PROOF_A PROOF_B')
    print(json.dumps(value,indent=2,allow_nan=False))


if __name__=='__main__':main()
