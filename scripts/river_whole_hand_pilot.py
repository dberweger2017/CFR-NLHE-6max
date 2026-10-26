"""Frozen PR388 whole-hand qualification, cost calibration and verified readout.

No outcome-based selection. Main requires a separately published admitted quote.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
from time import monotonic

FOCAL_SHA = 'd835f61f4a5407bd47e8f8a5da849ef82c16ad21fce32f15dce72d5997275189'
PEER_SHA = '23599816cf632a51cace45f25d70ed4918fe5e75875c33136d8629052a8a2a70'
LINEUPS = [('trained', ['peer', 'peer']),
           ('trained-pressure', ['peer', 'bot=pot-pressure']),
           ('pressure', ['bot=pot-pressure', 'bot=pot-pressure']),
           ('call', ['bot=check-call', 'bot=check-call']),
           ('call-pressure', ['bot=check-call', 'bot=pot-pressure']),
           ('random-tag', ['bot=random', 'bot=tight-aggressive'])]
ROOTS = {'fixture': 2026102138891, 'calibrate': 2026102138871, 'main': 2026102138801}


def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write(p, obj):
    Path(p).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def read(p):
    return json.loads(Path(p).read_text())


def traces(p):
    with Path(p).open() as f:
        return json.loads(next(f)), [json.loads(s) for s in f]


def manifest(args, out, phase, blocks, threads):
    models = {k: {'path': str(v), 'sha256': pin} for k, v, pin in
              [('focal', args.focal, FOCAL_SHA), ('peer', args.peer, PEER_SHA)]}
    cases = []
    for i, (name, opponents) in enumerate(LINEUPS):
        # Fixed alternating arm order; each arm retains identical block streams.
        for enabled in ([False, True] if i % 2 == 0 else [True, False]):
            label = name + ('-on' if enabled else '-off')
            cases.append({'name': label, 'root': ROOTS[phase] + i, 'blocks': blocks,
                          'opponents': opponents, 'search': enabled,
                          **{k: str(out / (label + '.' + suffix)) for k, suffix in
                             [('trace', 'jsonl'), ('metrics', 'metrics.jsonl'), ('summary', 'json')]}})
    return {'format': 'river-whole-hand-arena-v1', 'threads': threads, 'models': models,
            'tables': str(args.k50), 'startup': str(out / 'startup.json'), 'cases': cases}


def batch(args, out, phase, blocks, threads):
    out.mkdir(parents=True, exist_ok=False)
    m = manifest(args, out, phase, blocks, threads)
    write(out / 'manifest.json', m)
    tick = monotonic()
    with (out / 'stdout').open('x') as o, (out / 'stderr').open('x') as e:
        subprocess.run([str(args.binary), str(out / 'manifest.json')], stdout=o, stderr=e, check=True)
    costs = {'wall_seconds': monotonic() - tick, 'manifest_sha256': sha(out / 'manifest.json'),
             'startup': read(out / 'startup.json'),
             'play_and_write_seconds': sum(read(c['summary'])['play_and_write_seconds'] for c in m['cases']),
             'trace_bytes': sum(Path(c['trace']).stat().st_size for c in m['cases'])}
    write(out / 'costs.json', costs)
    return m, costs


def pair_proof(off, on):
    a, b = traces(off), traces(on)
    if any(a[0][k] != b[0][k] for k in ('identity', 'blocks', 'hands', 'seed', 'policies')):
        raise ValueError('paired header identity differs')
    if len(a[1]) != a[0]['hands'] or len(b[1]) != len(a[1]):
        raise ValueError('paired hand count differs')
    changes = 0
    for x, y in zip(a[1], b[1]):
        for k in ('hand', 'block', 'permutation', 'identities', 'deck', 'button'):
            if x[k] != y[k]:
                raise ValueError('paired hand identity differs: ' + k)
        if x['hand'] != x['block'] * 6 + x['permutation']:
            raise ValueError('hand index differs')
        for i in range(min(len(x['actions']), len(y['actions']))):
            if x['states'][i] != y['states'][i] or x['actors'][i] != y['actors'][i]:
                raise ValueError('state diverged before first action change')
            if x['actions'][i] != y['actions'][i]:
                actor = y['actors'][i]
                ledger = y['search_ledgers'][i]
                if (y['identities'][actor] != 0 or y['states'][i]['street'] != 'river'
                        or not ledger['search']['installed']):
                    raise ValueError('first changed action outside installed focal river search')
                changes += 1
                break
        else:
            if x['actions'] != y['actions'] or x['states'] != y['states'] or x['rewards'] != y['rewards']:
                raise ValueError('identical action path did not settle identically')
    return {'hands': len(a[1]), 'hands_with_changed_action_path': changes}


def verify_pass(initial, repeat, independent=True):
    from scripts.check_nplayer_policy_replay import check
    a, b = read(initial / 'manifest.json'), read(repeat / 'manifest.json')
    if len(a['cases']) != 12 or len(b['cases']) != 12:
        raise ValueError('fixed case count differs')
    proofs = []
    tick = monotonic()
    for x, y in zip(a['cases'], b['cases']):
        for k in ('name', 'root', 'blocks', 'opponents', 'search'):
            if x[k] != y[k]:
                raise ValueError('reproduction case differs')
        digest = sha(x['trace'])
        if digest != sha(y['trace']) or digest != read(x['summary'])['trace_sha256']:
            raise ValueError('fresh strategic trace reproduction differs: ' + x['name'])
        proof = check(Path(x['trace'])) if independent else {'status': 'not-run'}
        proofs.append({'case': x['name'], 'sha256': digest, 'independent_replay': proof})
    pairing = {}
    for name, _ in LINEUPS:
        # Match by full case name; call must not include call-pressure.
        paths = {c['search']: c['trace'] for c in a['cases'] if c['name'] in (name+'-on', name+'-off')}
        pairing[name] = pair_proof(paths[False], paths[True])
    return {'status': 'passed', 'records': proofs, 'pairing': pairing,
            'independent_replay_seconds': monotonic() - tick}


def fixture(args):
    _, _ = batch(args, args.out / 'initial', 'fixture', 2, 1)
    batch(args, args.out / 'repeat', 'fixture', 2, 2)
    proof = verify_pass(args.out / 'initial', args.out / 'repeat')
    # A legacy whole-hand run independently checks the new off adapter's RNG,
    # menu ordering and every state against ordinary Policy::choose.
    legacy = args.out / 'legacy.jsonl'
    subprocess.run([str(args.legacy), str(args.k50), '2', str(ROOTS['fixture']), str(legacy),
                    f'policy={args.focal}@{FOCAL_SHA}', f'policy={args.peer}@{PEER_SHA}', '100', '1'],
                   check=True, stdout=(args.out / 'legacy.stdout').open('x'))
    _, old = traces(legacy)
    _, new = traces(args.out / 'initial/trained-off.jsonl')
    for a, b in zip(old, new):
        if a != {k: v for k, v in b.items() if k != 'search_ledgers'}:
            raise ValueError('search-off differs from ordinary arena')
    if len(old) != len(new):
        raise ValueError('legacy hand count differs')
    proof['legacy_off_parity_hands'] = len(old)
    write(args.out / 'verified.json', proof)


def calibrate(args):
    costs = {}
    for threads in (1, 2, 4):
        _, costs[threads] = batch(args, args.out / str(threads), 'calibrate', 4, threads)
        if threads != 1:
            proof = verify_pass(args.out / '1', args.out / str(threads), independent=threads == 2)
            write(args.out / f'verified-{threads}.json', proof)
    # Choose only on measured cost and exact parity, never any return.
    best = min(costs, key=lambda t: costs[t]['play_and_write_seconds'])
    measured = costs[best]
    mean_work = measured['play_and_write_seconds'] * 32 * 2
    loads = measured['startup']['model_and_k50_load_seconds'] * 2
    replay = read(args.out / 'verified-2.json')['independent_replay_seconds'] * 32
    # Sparse calibration calls require substantial reserve; this is a planning
    # envelope, not a confidence bound or a maximum runtime guarantee.
    upper = 3 * mean_work + 2 * loads + max(600, 2 * replay)
    quote = {'status': 'quoted', 'selected_workers': best, 'worker_costs': costs,
             'lower_seconds': mean_work + loads + replay, 'upper_seconds': upper,
             'main_admitted': upper <= 10800, 'limit_seconds': 10800,
             'assumptions': '32x fixed calibration blocks, two fresh passes, measured concurrency; 3x play reserve, 2x load/replay reserve and >=600s replay reserve; sparse/rare-tail risk remains',
             'no_main_started': True, 'no_outcomes_used': True}
    write(args.out / 'quote.json', quote)


def measure(args):
    cal = read(args.calibration / 'quote.json')
    if not cal['main_admitted'] or cal['upper_seconds'] > 10800:
        raise ValueError('quote exceeds accepted pilot; no main launch')
    write(args.out / 'calibration-pin.json', {'path': str(args.calibration), 'quote_sha256': sha(args.calibration/'quote.json')})
    for arm in ('initial', 'repeat'):
        batch(args, args.out / arm, 'main', 128, cal['selected_workers'])
    write(args.out / 'verified.json', verify_pass(args.out/'initial', args.out/'repeat'))


def stats(values):
    if not values:
        return {'n': 0}
    xs = sorted(values)
    return {'n': len(xs), 'mean': statistics.mean(xs), 'median': statistics.median(xs),
            **{f'p{p}': xs[min(len(xs)-1, math.ceil(p/100*len(xs))-1)] for p in (95, 99)}, 'max': xs[-1]}


def readout(args):
    from scipy.stats import t, chi2, norm
    root = args.inputs
    proof = read(root/'verified.json')
    if proof['status'] != 'passed':
        raise ValueError('complete verification required')
    m = read(root/'initial/manifest.json')
    for c in m['cases']:
        p = next(p for p in proof['records'] if p['case'] == c['name'])
        if sha(c['trace']) != p['sha256'] or p['independent_replay']['status'] != 'passed':
            raise ValueError('verified trace changed')
    results = []
    for name, _ in LINEUPS:
        cases = {c['search']: c for c in m['cases'] if c['name'] in (name+'-on', name+'-off')}
        records = {k: traces(c['trace'])[1] for k, c in cases.items()}
        values = []
        counters = Counter()
        times = []
        off_entries = []
        for k in range(128):
            scores = {arm: statistics.mean(r['rewards'][r['identities'].index(0)] for r in rows[k*6:(k+1)*6])
                      for arm, rows in records.items()}
            # bb=100chips: chips/hand numerically equals BB/100.
            values.append(scores[True] - scores[False])
        for hand in records[True]:
            river = [i for i,s in enumerate(hand['states'][:-1]) if s['street']=='river']
            if river:
                s=hand['states'][river[0]];live=[p for p in s['players'] if not p[3]]
                counters['hands_with_river'] += 1
                counters['first_river_live_'+str(len(live))] += 1
                counters['first_river_focal_actor'] += int(hand['identities'][hand['actors'][river[0]]]==0)
            for ledger in hand['search_ledgers']:
                if ledger is None:
                    continue
                counters['focal_decisions'] += 1
                mode=ledger['mode'];counters[mode+'_decisions'] += 1
                counters['eligibility/'+ledger['eligibility']] += 1
                counters['same_draw_action_changes'] += int(ledger['changed_same_draw'])
                search=ledger['search']
                if search is not None:
                    counters[mode+'_installed'] += int(search['installed'])
                    if search['fallback_reason'] is not None:counters['fallback/'+search['fallback_reason']] += 1
                    if search.get('first_off_tree'):
                        counters['hands_off_tree'] += 1;off_entries.append(search['off_tree_entry'])
        for line in Path(cases[True]['metrics']).read_text().splitlines():
            r=json.loads(line)
            if r['mode']=='root':times.append(r['seconds'])
        sd=statistics.stdev(values);se=sd/math.sqrt(128);mean=statistics.mean(values)
        sd_upper=sd*math.sqrt(127/chi2.ppf(.025,127))
        squares=sorted((x*x for x in values),reverse=True);total=sum(squares)
        results.append({'lineup':name,'blocks':128,'paired_mean_bb100':mean,'paired_sd_bb100':sd,'paired_se_bb100':se,
            'exploratory_lower95_bb100':mean-t.ppf(.975,127)*se,'exploratory_upper95_bb100':mean+t.ppf(.975,127)*se,
            'normal_model_sd_upper95_bb100':sd_upper,'largest_squared_contrast_share':squares[0]/total if total else None,
            'counts':dict(counters),'root_latency_seconds':stats(times),'off_tree_entries':off_entries,
            'illustrative_blocks_per_primary':{str(effect):math.ceil(((norm.ppf(1-.05/3)+norm.ppf(.8))*sd_upper/effect)**2)
                                              if sd_upper else None for effect in (1,2,5)},
            'scope':'one fixed focal seed; exploratory deal-cluster intervals; normal-model variance bound does not cover unseen rare tails'})
    write(args.out/'results.json',{'status':'settled','lineups':results,'verification':proof,
          'initial_hands':9216,'reproduction_hands':9216,'no_strength_gate':True})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['fixture','calibrate','measure','readout'])
    p.add_argument('--out',type=Path,required=True)
    for key in ('binary','legacy','k50','focal','peer','inputs','calibration'):
        p.add_argument('--'+key,type=Path)
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    try:
        globals()[args.command](args)
    except BaseException as e:
        write(args.out/'failure.json',{'error':str(e)})
        raise


if __name__=='__main__':
    main()
