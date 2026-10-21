"""Prepared all-root assessment; requires explicit acceptance of the cost quote.

No new deals or strength run. Invoke through the thermal/mutex guardian.
"""
import argparse
import json
import math
from pathlib import Path
import random
import statistics
import subprocess
from time import monotonic

from scripts.river_conditional_evaluation import block_contrasts
from scripts.river_whole_hand_pilot import LINEUPS, read, sha, traces, write

INVENTORY_SHA = 'e003c039d8a32eca48d1dd7bcc32bb82734401371490c82bd358c728899855d4'
QUOTE_SHA = '86f9226fd8e194e029a9a175f732e17fc295a66b234a5b7f7cbf1adf1fef9c98'
BINARY_SHA = '5351380efd82e52f381d5c2197c349e29ffac9be9bee969b2cb82aa0eb5ef282'


def admission(quote, actual_sha, accepted_sha, budget):
    """Acceptance is an operator input, never inferred from outcomes or time."""
    if actual_sha != QUOTE_SHA or accepted_sha != actual_sha:
        raise ValueError('explicit acceptance of the unchanged published quote required')
    if (quote['status'] != 'calibrated' or quote['complete_roots'] != 13
            or quote['incomplete_ids'] or not quote['profile_identities_passed']):
        raise ValueError('successful original calibration required')
    if not math.isfinite(budget) or budget < quote['all384_two_pass_reserved_upper_seconds']:
        raise ValueError('accepted planning allowance below the published reserve')
    return {'quote_sha256': actual_sha, 'accepted_budget_seconds': budget,
            'budget_is_not_elapsed_kill_guard': True}


def strategic(value):
    """Compare all non-timing fields, preserving float64 values and signed zero."""
    if isinstance(value, dict):
        return {k: strategic(v) for k, v in value.items()
                if k not in ('seconds', 'prepare_seconds', 'total_seconds')}
    if isinstance(value, list):
        return [strategic(v) for v in value]
    return value.hex() if isinstance(value, float) else value


def verified_rows(roots, initial, repeat):
    ids = [r['id'] for r in roots]
    if len(set(ids)) != len(ids) or any([r['id'] for r in rows] != ids for rows in (initial, repeat)):
        raise ValueError('complete ordered unique coverage required on both passes')
    for root, a, b in zip(roots, initial, repeat):
        for row in (a, b):
            if (not row['identity_verified'] or not row['complete_contrast']
                    or row['profile_sha256'] != root['expected']['profile_sha256']):
                raise ValueError('incomplete or changed original profile: ' + root['id'])
            contrast = row['contrast_chips']
            if not isinstance(contrast, (int, float)) or not math.isfinite(contrast):
                raise ValueError('nonfinite contrast')
            if root['expected']['installed']:
                if row['method'] != 'full-positive-support-enumeration':
                    raise ValueError('installed root must enumerate both arms')
                for arm in ('on', 'off'):
                    v = row[arm]
                    if (not v['complete'] or not isinstance(v['expected_chips'], (int, float))
                            or not math.isfinite(v['expected_chips']) or not 0 < v['visited'] <= 200000):
                        raise ValueError('incomplete or invalid arm')
                if contrast != row['on']['expected_chips'] - row['off']['expected_chips']:
                    raise ValueError('contrast accounting differs')
            elif (row['method'] != 'identical-blueprint-policy-cancellation'
                  or contrast != 0 or row['on'] is not None or row['off'] is not None):
                raise ValueError('quality fallback must cancel identical policies')
        if strategic(a) != strategic(b):
            raise ValueError('fresh strategic reproduction differs: ' + root['id'])
    return {r['id']: r for r in initial}


def ratio_stats(sampled, integrated, rng, repetitions=10000):
    """Paired original blocks; no extra samples from the second pass."""
    n = len(sampled)
    if n != len(integrated) or n < 2 or not all(math.isfinite(v) for v in sampled + integrated):
        raise ValueError('finite matched independent blocks required')
    a, b = statistics.variance(sampled), statistics.variance(integrated)
    ratios = []
    for _ in range(repetitions):
        indexes = [rng.randrange(n) for _ in range(n)]
        x = [sampled[i] for i in indexes]; y = [integrated[i] for i in indexes]
        vx = statistics.variance(x)
        if vx:
            ratios.append(statistics.variance(y) / vx)
    ratios.sort()
    def share(xs):
        centered = [(x-statistics.mean(xs))**2 for x in xs]
        return max(centered)/sum(centered) if sum(centered) else None
    return {'blocks': n, 'sampled_mean_bb100': statistics.mean(sampled),
            'integrated_mean_bb100': statistics.mean(integrated),
            'sampled_sd_bb100': math.sqrt(a), 'integrated_sd_bb100': math.sqrt(b),
            'integrated_over_sampled_variance': b/a if a else None,
            'variance_ratio_bootstrap95': [ratios[int(.025*len(ratios))],
                                          ratios[min(len(ratios)-1,int(.975*len(ratios)))]] if ratios else None,
            'bootstrap_defined_replicates': len(ratios),
            'sampled_largest_centered_square_share': share(sampled),
            'integrated_largest_centered_square_share': share(integrated)}


def batch(args, inventory, label):
    out = args.out/label; out.mkdir()
    manifest = {**inventory, 'output': str(out/'records.jsonl'), 'startup': str(out/'startup.json')}
    write(out/'manifest.json', manifest)
    tick = monotonic()
    with (out/'stdout').open('x') as o, (out/'stderr').open('x') as e:
        subprocess.run([str(args.binary), str(out/'manifest.json')], stdout=o, stderr=e, check=True)
    startup = read(out/'startup.json')
    if (startup['binary_sha256'] != BINARY_SHA
            or {v['alias']: v['sha256'] for v in startup['model_pins']}
            != {alias: model['sha256'] for alias, model in inventory['models'].items()}):
        raise ValueError('runtime binary/model identity differs')
    costs = {'wall_seconds': monotonic()-tick, 'startup': startup,
             'records_sha256': sha(out/'records.jsonl'), 'manifest_sha256': sha(out/'manifest.json')}
    write(out/'costs.json', costs)
    return [json.loads(s) for s in (out/'records.jsonl').read_text().splitlines()], costs


def original_blocks(inventory):
    """Read only original independently replayed, hash-pinned pilot outcomes."""
    root = Path(inventory['pilot_root'])
    if sha(root/'readout/results.json') != inventory['pilot_result_sha256']:
        raise ValueError('settled pilot changed')
    cases = read(root/'measure/initial/manifest.json')['cases']
    expected = {p['case']: p['sha256'] for p in inventory['trace_pins']}
    records = {}
    for c in cases:
        if sha(c['trace']) != expected[c['name']]:
            raise ValueError('original independently replayed trace changed')
        header, hands = traces(c['trace'])
        if header['hands'] != 768 or len(hands) != 768:
            raise ValueError('original hand count differs')
        blocks = [0.] * 128
        for i, h in enumerate(hands):
            if h['hand'] != i or h['block'] != i//6 or h['permutation'] != i%6:
                raise ValueError('original block identity differs')
            blocks[i//6] += h['rewards'][h['identities'].index(0)]/6
        records[c['name']] = blocks
    return {name: [a-b for a,b in zip(records[name+'-on'],records[name+'-off'])] for name,_ in LINEUPS}


def assess(args):
    tick = monotonic()
    if sha(args.inventory) != INVENTORY_SHA or sha(args.binary) != BINARY_SHA:
        raise ValueError('qualified inventory/binary pin differs')
    q = read(args.calibration/'quote.json')
    accepted = admission(q, sha(args.calibration/'quote.json'), args.accepted_quote_sha256,
                         args.accepted_budget_seconds)
    write(args.out/'accepted-quote.json', accepted)
    inventory = read(args.inventory)
    if len(inventory['roots']) != 384 or inventory['max_nodes_per_arm'] != 200000:
        raise ValueError('frozen count/work limit differs')
    a, ca = batch(args, inventory, 'initial')
    b, cb = batch(args, inventory, 'repeat')
    verified = verified_rows(inventory['roots'], a, b)
    write(args.out/'verified.json', {'status': 'passed', 'roots': 384,
          'inventory_sha256': INVENTORY_SHA, 'binary_sha256': BINARY_SHA,
          'records_sha256': [ca['records_sha256'], cb['records_sha256']],
          'float64_values_and_profiles_reproduced': True})
    # Only after every required value/profile passes global verification.
    integrated = block_contrasts(inventory['roots'], verified)
    sampled = original_blocks(inventory)
    cost = read(Path(__file__).resolve().parents[1]/'docs/reports/river-whole-hand-pilot/costs.json')
    sampled_cold = sum(s['wall_seconds'] for s in cost['main_stage_costs'])
    sampled_load = sum(s['startup']['model_and_k50_load_seconds'] for s in cost['batch_costs'].values())
    sampled_amortized = sampled_cold-sampled_load
    rng = random.Random(2026102239001)
    results = []
    for name,_ in LINEUPS:
        s = ratio_stats(sampled[name], integrated[name], rng)
        results.append({'lineup': name, **s})
    # Include input hashing, both batches, global proof and bootstrap/readout;
    # native solve/enumeration time alone is not a complete evaluation cost.
    extra_cold = monotonic()-tick
    extra_amortized = extra_cold-ca['startup']['model_and_k50_seconds']-cb['startup']['model_and_k50_seconds']
    for s in results:
        ratio = s['integrated_over_sampled_variance']
        # Whole-panel shared cost basis, explicitly not measured per-lineup time.
        # Conservatively retain the entire old generate/play/replay pipeline as
        # prefix allowance, then add the newly measured expectation passes.
        s.update({
            'cold_variance_times_cost_ratio': ratio*(sampled_cold+extra_cold)/sampled_cold if ratio is not None else None,
            'amortized_variance_times_cost_ratio': ratio*(sampled_amortized+extra_amortized)/sampled_amortized if ratio is not None else None})
    write(args.out/'results.json', {'status': 'settled', 'lineups': results,
        'blocks_per_lineup': 128, 'root_count': 384, 'no_strength_gate': True,
        'bootstrap': {'replicates': 10000, 'seed': 2026102239001, 'generator': 'Python random.Random'},
        'cost_basis': {'sampled_cold_seconds': sampled_cold, 'sampled_amortized_seconds': sampled_amortized,
            'extra_expectation_cold_seconds': extra_cold, 'extra_expectation_amortized_seconds': extra_amortized,
            'scope': 'Whole-panel common cost basis for each separate lineup. Conservative prefix allowance retains entire measured PR388 generation/play/replay pipeline, plus new two-pass reconstruction/enumeration. Not a measured fresh integrated pipeline or per-lineup cost/speedup.'},
        'limitations': 'Saved development deals, one focal lineage; paired bootstrap may miss rare tails. No automatic fresh study, target selection, cap change or retry.'})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('inventory','binary','calibration','out'):
        p.add_argument('--'+key, type=Path, required=True)
    p.add_argument('--accepted-quote-sha256', required=True)
    p.add_argument('--accepted-budget-seconds', type=float, required=True)
    args = p.parse_args(); args.out.mkdir(parents=True, exist_ok=False)
    try:
        assess(args)
    except BaseException as error:
        write(args.out/'failure.json', {'error': str(error)})
        raise


if __name__ == '__main__':
    main()
