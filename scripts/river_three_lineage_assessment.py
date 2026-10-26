"""Fixed final three-lineage assessment; no player or native code changes."""
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
from scripts.river_arena_expectation import value_signature, reference, trace_prefix
from scripts.river_fresh_screen import (
    BINARY_SHA as PREVIOUS_BINARY_SHA, LINEUPS, block_values, describe, expectation_proof,
    inventory, rows, tail_blocks,
)

SEEDS = (2026101935003, 202610200601, 202610200602)
POLICY_SHA = (
    'd835f61f4a5407bd47e8f8a5da849ef82c16ad21fce32f15dce72d5997275189',
    '23599816cf632a51cace45f25d70ed4918fe5e75875c33136d8629052a8a2a70',
    '2911937c047c644324d7a78a944949192f19d44eda373ca333d94a0dcaec8984',
)
BLOCKS = {'trained': 2048, 'call-pressure': 4096}
FINAL_ROOTS = tuple(2026102239701 + i for i in range(6))
QUAL_ROOTS = (2026102239793, 2026102239794, 2026102239795, 2026102239796)
ALLOWANCE = 43200


def native_identity(source, prior, paths):
    changed = []
    example = 'native/hu20-trainer/examples/nplayer_river_arena.rs'
    for name in paths:
        current = (source/name).read_bytes(); old = (prior/name).read_bytes()
        if current == old:
            continue
        if name != example or old.count(b'1..=1024') != 1 or current != old.replace(b'1..=1024', b'1..=4096'):
            raise ValueError('native changes exceed the single CLI count-limit amendment')
        changed.append(name)
    if changed != [example]:
        raise ValueError('exact count-limit amendment required')
    return {'status': 'passed', 'changed_files': changed, 'amendment': 'CLI blocks upper bound1024->4096 only',
        'player_solver_library_byte_identical': True}


def make_manifest(config, out, focal, qualification=False):
    """Keep native settings unchanged; only model aliases, counts and roots vary."""
    args = SimpleNamespace(focal=Path(config['models'][0]), peer=Path(config['models'][1]), k50=Path(config['k50']))
    result = manifest(args, out, 'main', 4, 4)
    result['models'] = {
        alias: {'path': config['models'][i], 'sha256': POLICY_SHA[i]}
        for alias, i in (('focal', focal), ('peer', (focal + 1) % 3))
    }
    result['cases'] = [c for c in result['cases'] if c['name'].removesuffix('-on').removesuffix('-off') in LINEUPS]
    for c in result['cases']:
        name = c['name'].removesuffix('-on').removesuffix('-off')
        j = LINEUPS.index(name)
        c['blocks'] = 4 if qualification else BLOCKS[name]
        if qualification:
            if focal == 0:
                c['root'] = 2026102138801 + (0 if name == 'trained' else 4)
            else:
                c['root'] = QUAL_ROOTS[2 * (focal - 1) + j]
        else:
            c['root'] = FINAL_ROOTS[2 * focal + j]
        if c['search']:
            c['expectations'] = str(out / (c['name'] + '.expectations.jsonl'))
    return result


def batch(config, binary, out, focal, qualification=False):
    out.mkdir(parents=True, exist_ok=False)
    m = make_manifest(config, out, focal, qualification)
    write(out / 'manifest.json', m)
    tick = monotonic()
    with (out/'stdout').open('x') as o, (out/'stderr').open('x') as e:
        subprocess.run([str(binary), str(out/'manifest.json')], stdout=o, stderr=e, check=True)
    costs = {'wall_seconds': monotonic()-tick, 'startup': read(out/'startup.json'),
        'case_play_seconds': {c['name']: read(c['summary'])['play_and_write_seconds'] for c in m['cases']},
        'play_and_write_seconds': sum(read(c['summary'])['play_and_write_seconds'] for c in m['cases']),
        'manifest_sha256': sha(out/'manifest.json')}
    write(out/'costs.json', costs)
    return m, costs


def validate_cases(m, config, out, focal, qualification=False):
    expected = make_manifest(config, out, focal, qualification)
    if m != expected:
        raise ValueError('frozen manifest/settings/paths/counts/roots differ')


def verify(config, out, focal, qualification=False):
    """Complete replay/profile/value proofs before any strength statistics."""
    from scripts.check_nplayer_policy_replay import check
    a = read(out/'initial/manifest.json'); b = read(out/'repeat/manifest.json')
    validate_cases(a, config, out/'initial', focal, qualification)
    validate_cases(b, config, out/'repeat', focal, qualification)
    roots = {}; evaluated = {}; records = []; tick = monotonic()
    for c, d in zip(a['cases'], b['cases']):
        digest = sha(c['trace'])
        if (digest != sha(d['trace']) or digest != read(c['summary'])['trace_sha256']
                or digest != read(d['summary'])['trace_sha256']):
            raise ValueError('trace/reproduction/summary mismatch')
        blocks = c['blocks']; replay = check(Path(c['trace']))
        if replay['status'] != 'passed' or replay['hands'] != blocks*6:
            raise ValueError('independent replay/count failure')
        records.append({'case': c['name'], 'sha256': digest, 'blocks': blocks, 'independent_replay': replay})
        if c['search']:
            name = c['name'][:-3]; expected = inventory(c)
            values = expectation_proof(expected, list(rows(c['expectations'])))
            other = expectation_proof(expected, list(rows(d['expectations'])))
            if {k: value_signature(v) for k, v in values.items()} != {k: value_signature(v) for k, v in other.items()}:
                raise ValueError('value/profile/work reproduction mismatch')
            # Also verify root/block/permutation membership, including zero-root blocks.
            block_values(expected, list(values.values()), blocks)
            roots[name] = expected; evaluated[name] = values
    if len(records) != 4 or set(roots) != set(LINEUPS):
        raise ValueError('missing lineup/arm')
    pairing = {}
    for name in LINEUPS:
        paths = {c['search']: c['trace'] for c in a['cases'] if c['name'] in (name+'-on', name+'-off')}
        pairing[name] = pair_proof(paths[False], paths[True])
        by_hand = {r['hand']: r for r in roots[name].values()}
        stream = rows(paths[False]); next(stream)
        for hand in stream:
            root = by_hand.get(hand['hand'])
            if root is None:
                continue
            i = root['decision']; state = {k: v for k, v in hand['states'][i].items() if k != 'holes'}
            ledger = hand['search_ledgers'][i]
            if state != root['public_state'] or ledger is None or ledger['actions'] != root['ledger']['actions']:
                raise ValueError('matched legal root observation/menu mismatch')
            root['blueprint_probabilities'] = ledger['probabilities']
        if any('blueprint_probabilities' not in r for r in roots[name].values()):
            raise ValueError('matched baseline root missing')
    if qualification and focal == 0:
        original = read(Path(config['pilot'])/'measure/initial/manifest.json')
        _, oracle = reference(SimpleNamespace(reference=Path(config['reference'])))
        for c in a['cases']:
            old = next(x for x in original['cases'] if x['name'] == c['name'])
            trace_prefix(c['trace'], old['trace'], 4)
        for values in evaluated.values():
            for key, row in values.items():
                if value_signature(row) != value_signature(oracle[key]):
                    raise ValueError('count-limit rebuild changed known oracle')
    write(out/'root-inventory.json', roots); write(out/'expectation-records.json', evaluated)
    hands = sum(c['blocks']*6 for c in a['cases'])
    proof = {'status': 'passed', 'focal_seed': SEEDS[focal], 'records': records, 'pairing': pairing,
        'initial_hands': hands, 'reproduction_hands': hands, 'no_exclusions': True,
        'expectation_roots': {k: len(v) for k, v in roots.items()},
        'all_value_profile_work_reproduced': True, 'solver_advances': 0, 'profile_reconstructions': 0,
        'root_inventory_sha256': sha(out/'root-inventory.json'),
        'expectation_records_sha256': sha(out/'expectation-records.json'),
        'verification_seconds': monotonic()-tick}
    write(out/'verified.json', proof)
    return proof


def play(args, config):
    tick = monotonic()
    if sha(args.binary) != config['binary_sha256']:
        raise ValueError('count-limit-qualified binary mismatch')
    costs = {}
    for label in ('initial', 'repeat'):
        _, costs[label] = batch(config, args.binary, args.out/label, args.focal, args.mode == 'qualify')
    proof = verify(config, args.out, args.focal, args.mode == 'qualify')
    write(args.out/'costs.json', {'wall_seconds': monotonic()-tick, 'batches': costs,
        'verification_seconds': proof['verification_seconds'], 'binary_sha256': config['binary_sha256']})


def preflight_quote(proposal, qualifications, spent_seconds):
    """Costs/correctness only; no outcome-dependent admission or sample resizing."""
    if len(qualifications) != 3:
        raise ValueError('all focal qualifications required')
    rates = {d['lineup']: d['measured_play_seconds_per_block_per_pass'] for d in proposal['design']}
    load = proposal['components']['six_process_model_k50_load_seconds']/6
    for costs in qualifications:
        for b in costs['batches'].values():
            load = max(load, b['startup']['model_and_k50_load_seconds'])
            for name in LINEUPS:
                rates[name] = max(rates[name], sum(b['case_play_seconds'][name+'-'+arm] for arm in ('on','off'))/4)
    work = 2*3*sum(BLOCKS[name]*rates[name] for name in LINEUPS)
    loads = 6*load
    proof = proposal['components']['scaled_replay_proof_seconds']
    fixed = max(1800, spent_seconds + 300)
    central = loads + work + proof + fixed
    reserve = 2*loads + 3*work + max(600, 2*proof) + fixed
    return {'status': 'admitted' if reserve <= ALLOWANCE else 'quote-exceeds-allowance',
        'central_seconds': central, 'reserved_seconds': reserve, 'accepted_planning_allowance_seconds': ALLOWANCE,
        'per_lineup_play_seconds_per_block_per_pass': rates, 'model_start_seconds': load,
        'fixed_qualification_readout_archive_seconds': fixed, 'cost_only_no_outcomes': True,
        'main_started': False, 'no_resizing': True,
        'assumptions': 'Max prior1024-block and each fixed4-block qualification rate; max model start;3x play/2x loads,>=600s proof, fixed allowance covers spent preflight+300s. Planning allowance is not a time stop.'}


def bounds(values):
    from scipy.stats import t
    n = len(values)
    if n < 2 or not all(math.isfinite(v) for v in values):
        raise ValueError('finite independent blocks required')
    result = describe(values, t.ppf(.975, n-1), t.ppf(.975, n-1))
    # Separate one-sided lower/upper family bounds, not a joint two-sided band.
    result.pop('family95_bb100')
    se = statistics.stdev(values)/math.sqrt(n)
    critical = float(t.ppf(1-.05/3, n-1))
    mean = result['mean_bb100']
    result.update(family_one_sided95_lower_bb100=mean-critical*se if se else None,
        family_one_sided95_upper_bb100=mean+critical*se if se else None,
        family_size=3, one_sided_alpha=.05/3)
    return result


def decision(results):
    if len(results) != 6 or {(r['focal_seed'], r['lineup']) for r in results} != {(s,n) for s in SEEDS for n in LINEUPS}:
        raise ValueError('all six predeclared panels required')
    benefit = all(r['gate_passed'] for r in results)
    harm = any(r['material_harm_established'] for r in results)
    return {'all_six_gates_passed': benefit, 'material_harm_established': harm,
        'project_decision': ('further-consideration-with-broader-safeguards-outstanding' if benefit else
            'reject-frozen-candidate' if harm else 'defer-frozen-candidate-resume-blueprint-progress'),
        'no_automatic_extension_or_tuning': True}


def summarize_lineup(base, name, expected, evaluated):
    n = BLOCKS[name]; integrated = block_values(expected, list(evaluated.values()), n)
    m = read(base/'initial/manifest.json'); sampled = {}; counters = Counter()
    seats = {str(i): Counter() for i in range(3)}; seat_scores = {}; times = []
    integrated_seats = {str(i): [0.]*n for i in range(3)}
    root_seats = {}
    for c in [c for c in m['cases'] if c['name'] in (name+'-on', name+'-off')]:
        values = [0.]*n; per_seat = {str(i): [0.]*n for i in range(3)}
        stream = rows(c['trace']); next(stream)
        for hand in stream:
            p = hand['identities'].index(0); b = hand['block']; reward = hand['rewards'][p]
            values[b] += reward/6; per_seat[str(p)][b] += reward/2
            if not c['search']:
                continue
            for i, ledger in enumerate(hand['search_ledgers']):
                if ledger is None:
                    continue
                mode = ledger['mode']; counters['mode/'+mode] += 1; seats[str(p)]['mode/'+mode] += 1
                counters['eligibility/'+ledger['eligibility']] += 1
                counters['blueprint_found/'+str(ledger['blueprint_found'])] += 1
                if mode == 'root':
                    key = f"{name}/{hand['hand']:04d}/{i:04d}"; root_seats[key] = str(p)
                    counters['root_installed'] += int(ledger['search']['installed'])
                    if not ledger['search']['installed']:
                        counters['root_fallback_reason/'+str(ledger['search']['fallback_reason'])] += 1
                if ledger['search'] and ledger['search'].get('first_off_tree'):
                    counters['off_tree_hands'] += 1
        sampled[c['search']] = values; seat_scores[c['search']] = per_seat
        if c['search']:
            times = [r['seconds'] for r in rows(c['metrics']) if r['mode'] == 'root']
    if set(root_seats) != set(expected):
        raise ValueError('per-seat root accounting mismatch')
    for key, root in expected.items():
        integrated_seats[root_seats[key]][root['block']] += evaluated[key]['contrast_chips']/2
    if any(not math.isclose(sum(integrated_seats[p][b] for p in integrated_seats)/3, integrated[b], abs_tol=1e-10, rel_tol=1e-12) for b in range(n)):
        raise ValueError('seat contribution accounting mismatch')
    contrast = [x-y for x,y in zip(sampled[True], sampled[False])]
    summary = bounds(integrated); margin = 0 if name == 'trained' else -5
    lower = summary['family_one_sided95_lower_bb100']; upper = summary['family_one_sided95_upper_bb100']
    return {'lineup': name, 'integrated': summary, 'sampled': bounds(contrast),
        'gate_margin_bb100': margin, 'gate_passed': lower is not None and lower > margin,
        'material_harm_established': upper is not None and upper < -5,
        'variance_ratio': statistics.variance(integrated)/statistics.variance(contrast) if statistics.variance(contrast) else None,
        'tails': tail_blocks(integrated, expected, evaluated), 'counts': dict(counters),
        'root_latency_seconds': stats(times),
        'per_seat': {p: {'integrated_descriptive': bounds(integrated_seats[p]),
            'sampled_descriptive': bounds([x-y for x,y in zip(seat_scores[True][p],seat_scores[False][p])]),
            'counts': dict(seats[p]), 'in_confirmatory_family': False} for p in seats}}


def readout(args, config):
    results = []; proofs = {}
    # Entire study must verify before the first global statistical readout.
    for i, seed in enumerate(SEEDS):
        base = args.input/str(seed); proof = read(base/'verified.json')
        if (proof['status'] != 'passed' or proof['focal_seed'] != seed or not proof['no_exclusions'] or
                proof['initial_hands'] != 73728 or proof['reproduction_hands'] != 73728):
            raise ValueError('all complete lineage proofs required')
        for name, key in (('root-inventory.json','root_inventory_sha256'),('expectation-records.json','expectation_records_sha256')):
            if sha(base/name) != proof[key]:
                raise ValueError('verified inventory/value evidence changed')
        for label in ('initial', 'repeat'):
            m = read(base/label/'manifest.json'); validate_cases(m,config,base/label,i)
            for c in m['cases']:
                p = next(p for p in proof['records'] if p['case'] == c['name'])
                if p['independent_replay']['status'] != 'passed' or sha(c['trace']) != p['sha256']:
                    raise ValueError('verified trace changed')
        proofs[str(seed)] = sha(base/'verified.json')
    for i, seed in enumerate(SEEDS):
        base = args.input/str(seed); expected = read(base/'root-inventory.json'); evaluated = read(base/'expectation-records.json')
        for name in LINEUPS:
            results.append({'focal_seed': seed, 'trained_peer_seed': SEEDS[(i+1)%3],
                **summarize_lineup(base, name, expected[name], evaluated[name])})
    write(args.out/'results.json', {'status': 'settled', 'lineups': results, 'decision': decision(results),
        'proof_sha256s': proofs, 'initial_hands': 221184, 'reproduction_hands': 221184,
        'families': 'Separate primary3 lower>0 and scripted3 lower>-5, one-sided Bonferroni95% Student-t; no overall95% family or population-seed claim.',
        'material_harm_reporting': 'One-sided Bonferroni upper<-5 within each declared three-panel family, reported separately from lower gates.',
        'reproduction_adds_samples': False, 'no_followup_started': True})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['qualify','measure','readout'])
    p.add_argument('--config', type=Path, required=True); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--binary',type=Path); p.add_argument('--focal',type=int,choices=range(3)); p.add_argument('--input',type=Path)
    args=p.parse_args(); args.out.mkdir(parents=True,exist_ok=False)
    try:
        config=read(args.config)
        readout(args,config) if args.mode=='readout' else play(args,config)
    except BaseException as e:
        write(args.out/'failure.json',{'error':str(e)}); raise


if __name__ == '__main__':
    main()
