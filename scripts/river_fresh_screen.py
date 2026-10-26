"""Fixed PR396 fresh-deal screening; original player/binary stays frozen."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import statistics
import subprocess
from time import monotonic
from types import SimpleNamespace

from scripts.river_whole_hand_pilot import manifest, pair_proof, read, sha, write, stats
from scripts.river_arena_expectation import reference, value_signature, trace_prefix

LINEUPS = ('trained', 'call-pressure')
ROOTS = (2026102239601, 2026102239602)
BINARY_SHA = 'aaa1308888998f6013d88c21c556dd802617143f79504ad51d5b52b9157bb886'


def rows(path):
    with Path(path).open() as f:
        for line in f:
            yield json.loads(line)


def inventory(case):
    result = {}; seen_hands = set()
    records = rows(case['trace']); next(records)
    for hand in records:
        for decision, ledger in enumerate(hand['search_ledgers']):
            if ledger is None or ledger['mode'] != 'root':
                continue
            key = f"{case['name'][:-3]}/{hand['hand']:04d}/{decision:04d}"
            if key in result or hand['hand'] in seen_hands:
                raise ValueError('duplicate root/hand')
            seen_hands.add(hand['hand'])
            result[key] = {'id': key, 'hand': hand['hand'], 'block': hand['block'],
                'permutation': hand['permutation'], 'decision': decision,
                'expected': ledger['search'], 'ledger': ledger,
                'public_state': {k: v for k, v in hand['states'][decision].items() if k != 'holes'},
                'focal_hole': hand['states'][decision]['holes'][hand['identities'].index(0)],
                'chosen_action': hand['actions'][decision]}
    return result


def expectation_proof(expected, values):
    actual = {r['id']: r for r in values}
    if len(actual) != len(values) or set(actual) != set(expected):
        raise ValueError('complete unique eligible-root values required')
    for key, row in actual.items():
        root = expected[key]['expected']
        if (not row['complete_contrast'] or not math.isfinite(row['contrast_chips']) or
                row['profile_sha256'] != root['profile_sha256'] or
                row['solver_advances'] or row['profile_reconstructions']):
            raise ValueError('incomplete/changed profile or duplicate work: ' + key)
        value_signature(row)
        if root['installed']:
            if row['method'] != 'full-positive-support-enumeration':
                raise ValueError('installed root must enumerate')
            for arm in ('on', 'off'):
                v = row[arm]
                if (not v['complete'] or not math.isfinite(v['expected_chips']) or
                        not 0 < v['visited'] <= 200000):
                    raise ValueError('incomplete/invalid arm')
            if row['contrast_chips'] != row['on']['expected_chips'] - row['off']['expected_chips']:
                raise ValueError('contrast accounting differs')
        elif (row['method'] != 'identical-blueprint-policy-cancellation' or
              row['contrast_chips'] != 0 or row['on'] is not None or row['off'] is not None):
            raise ValueError('quality fallback must cancel identical policies')
    return actual


def block_values(expected, values, blocks):
    actual = expectation_proof(expected, values)
    out = [0.] * blocks
    for key, root in expected.items():
        if (root['hand'] != 6 * root['block'] + root['permutation'] or
                not 0 <= root['block'] < blocks or not 0 <= root['permutation'] < 6):
            raise ValueError('invalid permutation/block identity')
        out[root['block']] += actual[key]['contrast_chips'] / 6
    return out


def describe(values, point_critical, family_critical):
    if len(values) < 2 or not all(math.isfinite(v) for v in values):
        raise ValueError('finite independent block values required')
    mean = statistics.mean(values); sd = statistics.stdev(values); se = sd / math.sqrt(len(values))
    centered = [(v - mean) ** 2 for v in values]; raw = [v*v for v in values]
    def shares(squares):
        total = sum(squares)
        return {str(n): sum(sorted(squares, reverse=True)[:n])/total if total else None for n in (1, 3, 5)}
    return {'blocks': len(values), 'mean_bb100': mean, 'sd_bb100': sd,
        'pointwise95_bb100': [mean-point_critical*se, mean+point_critical*se] if sd else None,
        'family95_bb100': [mean-family_critical*se, mean+family_critical*se] if sd else None,
        'centered_square_concentration': shares(centered), 'uncentered_square_concentration': shares(raw),
        'zero_variance_is_not_a_pass': not bool(sd)}


def tail_blocks(values, expected, evaluated):
    mean = statistics.mean(values); total = sum((v-mean)**2 for v in values); raw = sum(v*v for v in values)
    selected = sorted((i for i,v in enumerate(values) if v > 0), key=lambda i:(-values[i],i))[:3]
    selected += sorted((i for i,v in enumerate(values) if v < 0), key=lambda i:(values[i],i))[:3]
    result = []
    for i in selected:
        roots = sorted((r for r in expected.values() if r['block']==i),
                       key=lambda r:(-abs(evaluated[r['id']]['contrast_chips']),r['hand']))[:3]
        examples = []
        for r in roots:
            l = r['ledger']; s = r['public_state']
            examples.append({'root_id': r['id'], 'hand': r['hand'], 'decision': r['decision'],
                'board': s['board'], 'pot_bb': s['pot']/100, 'focal_hole': r['focal_hole'],
                'actions': l['actions'], 'search_probabilities': l['probabilities'],
                'blueprint_probabilities': r['blueprint_probabilities'],
                'chosen_action': r['chosen_action'], 'blueprint_action': l['blueprint_action'],
                'installed': r['expected']['installed'], 'fallback_reason': r['expected']['fallback_reason'],
                'expected_on_minus_off_bb': evaluated[r['id']]['contrast_chips']/100,
                'explanation_scope': 'Recorded mixes and fixed-deal expected continuation; descriptive, not causal attribution.'})
        result.append({'block': i, 'contrast_bb100': values[i],
            'centered_square_share': (values[i]-mean)**2/total if total else None,
            'uncentered_square_share': values[i]**2/raw if raw else None, 'examples': examples})
    return result


def batch(args, label, blocks, fresh):
    out = args.out/label; out.mkdir()
    m = manifest(args, out, 'main', blocks, 4)
    m['cases'] = [c for c in m['cases'] if c['name'].removesuffix('-on').removesuffix('-off') in LINEUPS]
    for c in m['cases']:
        name = c['name'].removesuffix('-on').removesuffix('-off')
        if fresh: c['root'] = ROOTS[LINEUPS.index(name)]
        if c['search']: c['expectations'] = str(out/(c['name']+'.expectations.jsonl'))
    write(out/'manifest.json', m)
    tick=monotonic()
    with (out/'stdout').open('x') as o, (out/'stderr').open('x') as e:
        subprocess.run([str(args.binary),str(out/'manifest.json')],stdout=o,stderr=e,check=True)
    cost={'wall_seconds':monotonic()-tick,'startup':read(out/'startup.json'),
          'play_and_write_seconds':sum(read(c['summary'])['play_and_write_seconds'] for c in m['cases']),
          'case_play_seconds':{c['name']:read(c['summary'])['play_and_write_seconds'] for c in m['cases']},
          'manifest_sha256':sha(out/'manifest.json')}
    write(out/'costs.json',cost)
    return m,cost


def verify(args, a, b, blocks, fresh):
    from scripts.check_nplayer_policy_replay import check
    records=[]; roots={}; evaluated={}; tick=monotonic()
    for c,d in zip(a['cases'],b['cases']):
        if any(c[k]!=d[k] for k in ('name','root','blocks','opponents','search')):
            raise ValueError('fresh reproduction identity differs')
        digest=sha(c['trace'])
        if digest!=sha(d['trace']) or digest!=read(c['summary'])['trace_sha256']:
            raise ValueError('sampled reproduction differs')
        replay=check(Path(c['trace']))
        if replay['hands']!=blocks*6:raise ValueError('hand count differs')
        records.append({'case':c['name'],'sha256':digest,'independent_replay':replay})
        if c['search']:
            name=c['name'][:-3]; expected=inventory(c)
            values=list(rows(c['expectations'])); other=list(rows(d['expectations']))
            v=expectation_proof(expected,values); w=expectation_proof(expected,other)
            if {k:value_signature(x) for k,x in v.items()}!={k:value_signature(x) for k,x in w.items()}:
                raise ValueError('fresh expectation/profile/work reproduction differs')
            roots[name]=expected; evaluated[name]=v
    if len(records)!=4 or set(roots)!=set(LINEUPS):raise ValueError('fixed lineups/cases required')
    pairing={}
    for name in LINEUPS:
        paths={c['search']:c['trace'] for c in a['cases'] if c['name'] in (name+'-on',name+'-off')}
        pairing[name]=pair_proof(paths[False],paths[True])
        by_hand={r['hand']:r for r in roots[name].values()}
        stream=rows(paths[False]);next(stream)
        for hand in stream:
            root=by_hand.get(hand['hand'])
            if root is None:continue
            decision=root['decision'];state={k:v for k,v in hand['states'][decision].items() if k!='holes'}
            ledger=hand['search_ledgers'][decision]
            if state!=root['public_state'] or ledger is None or ledger['actions']!=root['ledger']['actions']:
                raise ValueError('baseline root observation/action menu differs')
            root['blueprint_probabilities']=ledger['probabilities']
    if not fresh:
        original=read(args.pilot/'measure/initial/manifest.json'); _,oracle=reference(SimpleNamespace(reference=args.reference))
        for c in a['cases']:
            old=next(x for x in original['cases'] if x['name']==c['name'])
            trace_prefix(c['trace'],old['trace'],blocks)
        for v in evaluated.values():
            for key,row in v.items():
                if value_signature(row)!=value_signature(oracle[key]):raise ValueError('qualification differs from frozen oracle')
    proof={'status':'passed','records':records,'pairing':pairing,'blocks_per_lineup':blocks,
        'initial_hands':4*blocks*6,'reproduction_hands':4*blocks*6,'no_exclusions':True,
        'expectation_roots':{k:len(v) for k,v in roots.items()},'all_value_profile_work_reproduced':True,
        'solver_advances':0,'profile_reconstructions':0,'verification_seconds':monotonic()-tick}
    write(args.out/'root-inventory.json',roots);write(args.out/'expectation-records.json',evaluated)
    proof['root_inventory_sha256']=sha(args.out/'root-inventory.json')
    proof['expectation_records_sha256']=sha(args.out/'expectation-records.json')
    write(args.out/'verified.json',proof)
    return proof


def play(args):
    fresh=args.mode=='measure'; blocks=1024 if fresh else 4; tick=monotonic()
    if sha(args.binary)!=BINARY_SHA:raise ValueError('frozen qualified binary differs')
    a,ca=batch(args,'initial',blocks,fresh);b,cb=batch(args,'repeat',blocks,fresh)
    proof=verify(args,a,b,blocks,fresh)
    write(args.out/'costs.json',{'wall_seconds':monotonic()-tick,'batches':{'initial':ca,'repeat':cb},
        'verification_seconds':proof['verification_seconds'],'binary_sha256':BINARY_SHA})


def readout(args):
    from scipy.stats import t
    base=args.input; proof=read(base/'verified.json')
    if proof['status']!='passed' or proof['blocks_per_lineup']!=1024:raise ValueError('verified main required')
    if sha(base/'root-inventory.json')!=proof['root_inventory_sha256'] or sha(base/'expectation-records.json')!=proof['expectation_records_sha256']:
        raise ValueError('verified root/value evidence changed')
    a=read(base/'initial/manifest.json'); expected=read(base/'root-inventory.json'); evaluated=read(base/'expectation-records.json')
    for c in a['cases']:
        p=next(x for x in proof['records'] if x['case']==c['name'])
        if sha(c['trace'])!=p['sha256'] or p['independent_replay']['status']!='passed':raise ValueError('verified trace changed')
    result=[]
    for name in LINEUPS:
        integrated=block_values(expected[name],list(evaluated[name].values()),1024)
        sampled={}; counters=Counter(); seat={str(i):Counter() for i in range(3)}; times=[]
        for c in [c for c in a['cases'] if c['name'] in (name+'-on',name+'-off')]:
            scores=[0.]*1024; stream=rows(c['trace']);next(stream)
            for hand in stream:
                physical=hand['identities'].index(0);scores[hand['block']]+=hand['rewards'][physical]/6
                if c['search']:
                    for l in hand['search_ledgers']:
                        if l is None:continue
                        counters['mode/'+l['mode']]+=1;seat[str(physical)]['mode/'+l['mode']]+=1
                        counters['blueprint_found/'+str(l['blueprint_found'])]+=1
                        if l['mode']=='root':
                            counters['root_installed']+=int(l['search']['installed'])
                            if not l['search']['installed']:
                                reason=l['search']['fallback_reason']
                                counters['root_fallback_reason/'+str(reason)]+=1
                                counters['root_quality_fallback']+=int('quality' in str(reason).lower())
                        if l['search'] and l['search'].get('first_off_tree'):counters['off_tree_hands']+=1
            sampled[c['search']]=scores
            if c['search']:times=[x['seconds'] for x in rows(c['metrics']) if x['mode']=='root']
        contrast=[x-y for x,y in zip(sampled[True],sampled[False])]
        statistics_ = describe(integrated,t.ppf(.975,1023),t.ppf(.9875,1023))
        family=statistics_['family95_bb100']
        result.append({'lineup':name,'integrated':statistics_,
            'sampled':describe(contrast,t.ppf(.975,1023),t.ppf(.9875,1023)),
            'variance_ratio':statistics.variance(integrated)/statistics.variance(contrast) if statistics.variance(contrast) else None,
            'clear_unacceptable_harm_flag':bool(family and family[1]<-5),
            'adverse_direction_clears_zero':bool(family and family[1]<0),
            'peer_promising_signal':bool(name=='trained' and family and family[0]>0),
            'tails':tail_blocks(integrated,expected[name],evaluated[name]),
            'counts':dict(counters),'per_seat_counts':{k:dict(v) for k,v in seat.items()},'root_latency_seconds':stats(times)})
    write(args.out/'results.json',{'status':'settled','screening_only':True,'lineups':result,
        'proof_sha256':sha(base/'verified.json'),'costs':read(base/'costs.json'),
        'harm_flag_margin_bb100':-5,'interval_family':'two lineup means, simultaneous two-sided Bonferroni family95',
        'no_automatic_extension':True,'no_followup_started':True})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['qualify','measure','readout'])
    p.add_argument('--out',type=Path,required=True)
    for name in ('binary','focal','peer','k50','pilot','reference','input'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    try:readout(a) if a.mode=='readout' else play(a)
    except BaseException as e:write(a.out/'failure.json',{'error':str(e)});raise


if __name__=='__main__':main()
