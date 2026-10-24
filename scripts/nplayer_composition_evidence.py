"""Independent small-fixture row oracle and all-decision composition accounting."""
import gzip
import hashlib
import itertools
import json
import math
import struct
from pathlib import Path
from scripts import nplayer_paired_evidence as evidence
from scripts import nplayer_shared_observations as shared

FORMAT='nplayer-missing-positive-v1'


def pinned_rows(spec):
    """Qualification only: bound before reading; never load mature models here."""
    receipt=Path(spec['mass'])/'receipt.json';mass=json.loads(receipt.read_text())
    if evidence.sha(receipt)!=spec['mass_sha256'] or mass['rows']>100000 or mass['status']!='passed':raise ValueError('small pinned mass fixture required')
    zero=Path(spec['mass'])/'zero-keys.bin';raw=zero.read_bytes()
    if evidence.sha(zero)!=mass['zero_keys_sha256'] or len(raw)!=16*mass['zero_mass_rows']:raise ValueError('fixture zero keys differ')
    zeros={raw[i:i+16].hex() for i in range(0,len(raw),16)}
    path=Path(spec['source_policy'])
    if evidence.sha(path)!=spec['source_policy_sha256']:raise ValueError('fixture source probabilities changed')
    with gzip.open(path,'rt') as f:
        header=json.loads(next(f));rows={}
        if header['entries']!=mass['rows'] or header['source_checkpoint_sha256']!=mass['checkpoint_sha256']:raise ValueError('fixture source lineage/count differs')
        for line in f:
            key,owner,street,code,probabilities=json.loads(line)
            if key in rows:raise ValueError('duplicate fixture row')
            status='zero_mass' if key in zeros else 'positive_mass'
            if status=='zero_mass' and any(abs(p-1/len(probabilities))>1e-14 for p in probabilities):raise ValueError('fixture zero probabilities differ')
            rows[key]=(owner,street,code,probabilities,status)
    if len(rows)!=mass['rows'] or not zeros.issubset(rows):raise ValueError('fixture inventory differs')
    return rows


def selection(base,donor,n):
    if n<=0:raise ValueError('empty legal menu')
    if base is not None:
        return dict(format=FORMAT,source='base',base_status=base[-1],donor_status='not_queried',probabilities=base[3]),base[-1]
    if donor is not None and donor[-1]=='positive_mass':
        return dict(format=FORMAT,source='donor',base_status='missing',donor_status='positive_mass',probabilities=donor[3]),'positive_mass'
    return dict(format=FORMAT,source='uniform',base_status='missing',donor_status='missing' if donor is None else donor[-1],probabilities=[1/n]*n),'missing'


def same_float64(a,b):
    return len(a)==len(b) and all(struct.pack('!d',x)==struct.pack('!d',y) for x,y in zip(a,b))


def audit(trace,base,donor,catalog):
    stream=evidence.rows(trace);header=next(stream);n,schedule=evidence.header_check(header)
    pin=header['policies'][0]
    if pin.get('composition')!=FORMAT or pin['base']['sha256']!=catalog['control']['sha256'] or pin['donor']['sha256']!=catalog['donor']['sha256']:raise ValueError('composed physical source pins differ')
    unsigned={k:v for k,v in pin.items() if k!='sha256'}
    if hashlib.sha256(json.dumps(unsigned,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=pin['sha256']:raise ValueError('composed virtual identity differs')
    counts={};streets={};count=decisions=0
    for count,row in enumerate(stream,1):
        evidence.validate_row(row,count-1,header,n,schedule)
        for index,(actor,lookup) in enumerate(zip(row['actors'],row['lookups'])):
            if row['identities'][actor]!=0:
                if 'composition' in lookup:raise ValueError('composition leaked into fixed opponent')
                continue
            choices=shared.menu(row,index);code=sum(1<<label for label,_ in choices);key=lookup['key']
            expected,status=selection(base.get(key),donor.get(key),len(choices))
            used=base.get(key) if expected['source']=='base' else donor.get(key) if expected['source']=='donor' else None
            if used is not None and used[:3] != ((actor-row['button'])%n,lookup['street'],code):raise ValueError('selected source key/action identity differs')
            actual=lookup.get('composition')
            if not isinstance(actual,dict) or set(actual)!=set(expected):raise ValueError('composition decision omitted/extra diagnostic')
            if any(actual[k]!=expected[k] for k in expected if k!='probabilities') or not same_float64(actual['probabilities'],expected['probabilities']) or lookup['status']!=status:raise ValueError('composition selection/source float64 mismatch')
            if row['actions'][index] not in [a for _,a in choices]:raise ValueError('selected action outside legal menu')
            decisions+=1;counts[expected['source']]=counts.get(expected['source'],0)+1
            street=row['states'][index]['street'];s=streets.setdefault(street,{});s[expected['source']]=s.get(expected['source'],0)+1
    if count!=header['hands']:raise ValueError('composition trace incomplete')
    return dict(status='passed',trace_sha256=evidence.sha(trace),hands=count,decisions=decisions,selection_counts=counts,by_street=streets,exact_source_float64=True,no_exclusions=True)


def payload_parity(a,b,strip_composition=False):
    streams=[evidence.rows(a),evidence.rows(b)];headers=[next(s) for s in streams]
    if any(headers[0][k]!=headers[1][k] for k in ['identity','hands','blocks','seed','schedule','distinct_policy_instances']):raise ValueError('RNG parity game/root/field differs')
    for left,right in itertools.zip_longest(*streams):
        if left is None or right is None:raise ValueError('RNG parity incomplete')
        if strip_composition:
            for row in [left,right]:
                for lookup in row['lookups']:lookup.pop('composition',None)
        if left!=right:raise ValueError('action RNG/ordinary payload changed')
    return dict(status='passed',all_hand_payloads_equal=True)


def structural(trace):
    """Mature arena: reconcile every declared selector tag, without model loading.

    Exact source probabilities are qualified independently on small exported rows;
    the main pins audited existing binaries/mass receipts and the same native code.
    This check alone is not a second full source-row audit of mature policies.
    """
    stream=evidence.rows(trace);h=next(stream);n,schedule=evidence.header_check(h);counts={};hands=decisions=0
    if h['policies'][0].get('composition')!=FORMAT:raise ValueError('composed focal required')
    for hands,row in enumerate(stream,1):
        evidence.validate_row(row,hands-1,h,n,schedule)
        for index,(actor,l) in enumerate(zip(row['actors'],row['lookups'])):
            if row['identities'][actor]!=0:
                if 'composition' in l:raise ValueError('nonfocal composition')
                continue
            x=l['composition'];source=x['source'];b=x['base_status'];d=x['donor_status'];p=x['probabilities']
            if x['format']!=FORMAT or len(p)!=len(shared.menu(row,index)) or not p or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in p) or abs(sum(p)-1)>1e-12:raise ValueError('bad composition probabilities')
            if source=='base':ok=b in ('positive_mass','zero_mass') and d=='not_queried' and l['status']==b
            elif source=='donor':ok=b=='missing' and d=='positive_mass' and l['status']=='positive_mass'
            elif source=='uniform':ok=b=='missing' and d in ('missing','zero_mass') and l['status']=='missing'
            else:ok=False
            if not ok:raise ValueError('composition precedence violated')
            if source=='uniform' or b=='zero_mass':
                if any(abs(v-1/len(p))>1e-14 for v in p):raise ValueError('composition fallback changed')
            counts[source]=counts.get(source,0)+1;decisions+=1
    if hands!=h['hands']:raise ValueError('composition incomplete')
    return dict(status='passed',hands=hands,decisions=decisions,selection_counts=counts,trace_sha256=evidence.sha(trace),exact_source_audit=False)
