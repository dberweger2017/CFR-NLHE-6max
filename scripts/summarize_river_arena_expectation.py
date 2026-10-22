"""Offline PR394 accounting and conditional proposal; never launches poker work."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    receipt = read(args.receipt)
    for name, body in receipt['files'].items():
        if hashlib.sha256(body.encode()).hexdigest() != receipt['sha256'][name]:
            raise ValueError('retrieved receipt hash differs: ' + name)
    remote = lambda name: json.loads(receipt['files']['measurement-v1/' + name])
    proof, costs, stages = (remote(p) for p in
                            ('measure/verified.json', 'measure/costs.json', 'stage-costs.json'))
    if (remote('status.json')['status'] != 'complete' or
            'measurement-v1/failure.json' in receipt['files'] or
            any(s['returncode'] for s in stages) or proof['status'] != 'passed'):
        raise ValueError('complete successful verified measurement required')
    if (proof['initial_hands'] != 9216 or proof['repeat_hands'] != 9216 or
            len(proof['cases']) != 12 or not proof['player_unchanged'] or not proof['no_new_deals']):
        raise ValueError('frozen hand/player scope differs')
    if not all(p['roots'] == 384 and p['no_exclusions'] and
               p['float64_value_profile_and_work_match'] and
               p['solver_advances'] == p['profile_reconstructions'] == 0
               for p in proof['expectations']):
        raise ValueError('full expectation parity required')
    if not all(p['original_hand_parity'] and p['independent_replay']['status'] == 'passed'
               and p['independent_replay']['hands'] == 768 for p in proof['cases']):
        raise ValueError('all original hands/replays required')
    reports = Path(__file__).resolve().parents[1] / 'docs/reports'
    old = read(reports / 'river-whole-hand-pilot/costs.json')
    assessment = read(reports / 'river-conditional-evaluation/assessment-analysis.json')
    pilot = read(reports / 'river-whole-hand-pilot/results.json')
    old_wall = sum(s['wall_seconds'] for s in old['main_stage_costs'])
    old_load = sum(b['startup']['model_and_k50_load_seconds'] for b in old['batch_costs'].values())
    wall = sum(s['wall_seconds'] for s in stages)
    load = sum(b['startup']['model_and_k50_load_seconds'] for b in costs['batches'].values())
    multiplier = wall / old_wall
    amortized_multiplier = (wall - load) / (old_wall - old_load)
    rows = []
    for row in assessment['lineups']:
        variance = row['integrated_over_sampled_variance']
        rows.append({**row,
            'inline_cold_wall_efficiency_ratio': variance * multiplier if variance is not None else None,
            'inline_amortized_wall_efficiency_ratio': variance * amortized_multiplier if variance is not None else None})
    summary = {'status': 'verified-full-inline-measurement', 'proof': proof,
        'supervised_stages': stages, 'costs': costs, 'resources': receipt['resources'],
        'work': receipt['work'], 'lineups': rows,
        'old_sampled_wall_seconds': old_wall, 'old_sampled_load_seconds': old_load,
        'inline_wall_seconds': wall, 'inline_load_seconds': load,
        'inline_over_sampled_cold_wall': multiplier,
        'inline_over_sampled_amortized_wall': amortized_multiplier,
        'separate_pipeline_wall_seconds': old_wall + assessment['extra_supervised_wall_seconds'],
        'separate_over_inline_speed_ratio': (old_wall + assessment['extra_supervised_wall_seconds']) / wall,
        'no_variance_refit': True, 'no_strength_gate': True,
        'limits': 'Same saved deals and one focal lineage. Whole-panel common cost basis, not per-lineup efficiency. Ordinary caches; one two-pass job. Preserve PR391 tail/bootstrap limitations.'}
    write(args.out / 'results.json', summary)
    with (args.out / 'lineups.csv').open('w') as f:
        columns = ['lineup', 'sampled_mean_bb100', 'integrated_mean_bb100',
                   'integrated_over_sampled_variance', 'inline_cold_wall_efficiency_ratio',
                   'inline_amortized_wall_efficiency_ratio']
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore', lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)

    # Same df127 normal-model SD upper multiplier as the recorded pilot; no new fit.
    scale = pilot['lineups'][0]['normal_model_sd_upper95_bb100'] / pilot['lineups'][0]['paired_sd_bb100']
    normal = NormalDist()
    # Three primary + twelve non-inferiority tests. Union allocation of type-II
    # error gives nominal80% joint power under the stipulated normal model.
    target_power = 1 - .2 / 15
    designs = []
    for row in rows:
        name = row['lineup']
        seconds = max(sum(receipt['work'][label]['cases'][name + '-' + arm]['play_and_write_seconds']
                          for arm in ('on', 'off')) for label in ('initial', 'repeat')) / 128
        if name == 'call':
            designs.append({'lineup': name, 'blocks_per_lineage': 256, 'family': 'no-intervention control',
                            'play_seconds_per_block_per_pass': seconds})
            continue
        alpha = .05 / (3 if name == 'trained' else 12)
        sd = row['integrated_sd_bb100'] * scale
        blocks = math.ceil((((normal.inv_cdf(1 - alpha) + normal.inv_cdf(target_power)) * sd / 5) ** 2) / 128) * 128
        boundary = 0 if name == 'trained' else -5
        powers = {str(effect): normal.cdf((effect - boundary) * math.sqrt(blocks) / sd - normal.inv_cdf(1 - alpha))
                  for effect in ((0, 2, 5) if name == 'trained' else (-10, -5, 0))}
        designs.append({'lineup': name, 'family': 'primary3' if name == 'trained' else 'safeguards12',
            'blocks_per_lineage': blocks, 'normal_model_sd_upper_bb100': sd,
            'lower_bound_must_exceed_bb100': boundary, 'one_sided_alpha': alpha,
            'conditional_power_by_true_effect_bb100': powers,
            'play_seconds_per_block_per_pass': seconds})
    blocks = sum(d['blocks_per_lineage'] for d in designs)
    play = 3 * 2 * sum(d['blocks_per_lineage'] * d['play_seconds_per_block_per_pass'] for d in designs)
    hands = blocks * 3 * 2 * 6 * 2
    verification = costs['verification_seconds'] * hands / 18432
    central = 3 * load + play + verification + 1800
    reserved = 2 * 3 * load + 3 * play + max(600, 2 * verification) + 1800
    proposal = {'status': 'proposal-only-not-authorized', 'lineups': designs,
        'lineages': [2026101935003, 202610200601, 202610200602],
        'primary_opponents': 'Cyclic next frozen10B lineage duplicated in the two opponent seats; two resident policies, sequential focal lineages.',
        'families': {'primary': 3, 'script_and_mixed_noninferiority': 12, 'check_call_controls': 3},
        'primary_design_true_gain_bb100': 5, 'safeguard_design_true_gain_bb100': 0,
        'proposed_safeguard_margin_bb100': -5,
        'nominal_power_per_test': target_power, 'nominal_joint_power_union_bound': .8,
        'normal_model_sd_multiplier': scale, 'total_initial_plus_reproduction_hand_instances': hands,
        'central_seconds': central, 'reserved_seconds': reserved, 'proposed_planning_budget_seconds': 80 * 3600,
        'cost_components': {'play_both_passes_all_lineages_seconds': play,
            'six_process_startup_seconds': 3 * load, 'scaled_verification_seconds': verification,
            'qualification_readout_archive_allowance_seconds': 1800},
        'cost_limits': 'All three lineages assumed to share measured per-lineup cost/variance. Other two focal lineages unmeasured; no guaranteed bound.3x play/2x loads+verification reserve; 30min fixed qualification/readout/archive allowance. Cold inputs already present; no model conversion/download included.',
        'statistic': 'Mean focal singleton on-minus-off contrast, future river action expectation at every eligible root, six-permutation block as independent unit; reproduction adds no samples.',
        'no_automatic_launch': True,
        'decision_caveat': '80% joint power is only a normal-model design scenario at +5 primary and zero safeguard effects, not the empirical pass chance. Existing check-call/pressure mean is adverse(-14.81); if repeated, the proposed-5 safeguard should fail. Heavy tails and other focal seeds can invalidate forecast.'}
    if reserved > 80 * 3600:
        raise ValueError('proposal exceeds its stated planning budget')
    write(args.out / 'strength-proposal.json', proposal)
    print(json.dumps({'wall_seconds': wall, 'speed_ratio': summary['separate_over_inline_speed_ratio'],
                      'proposal_hours': [central / 3600, reserved / 3600], 'hands': hands}))


if __name__ == '__main__':
    main()
