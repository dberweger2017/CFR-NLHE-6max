"""Five-player cost scenarios from completed PR413 metadata; no model/host access."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist

SOURCE = Path(__file__).resolve().parents[1]
INPUT = 'docs/reports/nplayer-four-player-candidate/results.json'


def proposal():
    path = SOURCE / INPUT
    r = json.loads(path.read_text())
    endpoints = r['results']['endpoints']
    stages = r['costs']['stages']
    old_hands = r['proofs']['evaluation-verified.json']['data']['initial_hands']
    hands = 8 * 4096 * 10 * 2
    ratio = hands / old_hands
    def total(suffix):
        return sum(s['wall_seconds'] for s in stages if s['phase'].endswith(suffix))
    rows = []
    def add(name, value, reserve=2):
        rows.append(dict(name=name, central_seconds=value, reserved_seconds=value * reserve))
    # These multipliers are unmeasured five-player scenarios, not speed claims.
    add('active traversal', sum(e['active_training_seconds'] for e in endpoints.values()) * 1.5)
    add('checkpoint saves', sum(e['save_seconds'] for e in endpoints.values()) * 1.25)
    add('train startup/resume/hash residual', sum(e['stage_wall_seconds'] - e['elapsed_seconds'] for e in endpoints.values()) * 1.5)
    add('average exports', total('-export') * 1.25)
    add('source checkpoint/export audits', sum(s['wall_seconds'] for s in stages if s['phase'].endswith('-audit') and not s['phase'].endswith('-binary-audit')) * 1.25)
    add('binary conversion', total('-convert') * 1.25)
    add('binary full-row audits', total('-binary-audit') * 1.25)
    costs = [c for phase in r['arena_costs'].values() for c in phase.values()]
    load = sum(c['load_seconds'] for c in costs)
    play = sum(c['play_seconds'] for c in costs)
    arena = sum(s['wall_seconds'] for s in stages if s['phase'].startswith('arena-'))
    add('two arena model loads', load * 1.25)
    add('play/write including reproduction', play * ratio * 1.5, 3)
    add('arena process/other residual', max(0, arena-load-play) * 1.25)
    add('initial independent replay', sum(s['wall_seconds'] for s in stages if s['phase'].startswith('replay-')) * ratio * 1.5)
    add('paired block verification/readout', sum(s['wall_seconds'] for s in stages if s['phase'].startswith('pair-')) * ratio * 1.5)
    # Global readout hashes models as well as traces; do not scale it by hands.
    add('global proof/tail readout', total('global-readout') * 1.25)
    add('between-stage source/environment/input validation', r['costs']['between_stage_and_validation_seconds'] * 1.5)
    add('build and tiny correctness qualification', 600)
    add('report preparation/publication', 900, 5/3)
    central = sum(c['central_seconds'] for c in rows)
    reserved = sum(c['reserved_seconds'] for c in rows)
    allocation = math.ceil(reserved/3600)*3600
    # Two retained endpoints: same cap; all derivatives/storage remain scenarios.
    storage = dict(model_derivatives_scenario_bytes=100_000_000_000,
                   all_trace_scenario_bytes=2*hands*8192,
                   manual_headroom_bytes=30*2**30)
    storage['requested_free_bytes'] = sum(storage.values())
    # Prior deal variance is a scenario only: ten seatings and five players differ.
    z = NormalDist().inv_cdf(1-.05/8)
    power = []
    for sd in (400,800,1600):
        se = sd/math.sqrt(4096)
        power.append(dict(assumed_paired_block_sd_bb100=sd, standard_error_bb100=se,
            approximate_adjusted_lower_distance=z*se,
            primary_true_gain25_power=NormalDist().cdf(25/se-z),
            neutral_script_clears_minus5_power=NormalDist().cdf(5/se-z)))
    return dict(status='proposal-no-main-admitted', source_input=INPUT,
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        players=5,stack_bb=100,seed=2026102351001,targets=[3_000_000_000,10_000_000_000],
        entry_threshold=250_000_000,blocks_per_field=4096,fields=8,seatings=10,
        initial_hands=hands,reproduction_hands=hands,
        statistical_unit='independent deal block; mean of ten paired seating contrasts; no reciprocal halving',
        family='eight one-sided95 Student-t/Bonferroni; primary lower>0; seven paired safeguards lower>-5',
        components=rows,central_seconds=central,reserved_seconds=reserved,
        proposed_allocation_seconds=allocation,storage=storage,power_scenarios=power,
        assumptions=dict(training_active_penalty=1.5,save_row_tool_load_penalty=1.25,
            train_residual_and_validation_penalty=1.5,hand_work_penalty=1.5,
            seating_hand_ratio=ratio,main_component_reserve=2,play_component_reserve=3),
        limits='PR413 measured four-player components; five-player mature runtime, support and variance unmeasured. Seating ratio scales only hand work, not the campaign. Scenario/reserve, not a bound or completion guarantee; no time kill or automatic extension.',
        excludes=['archive/upload','release packaging','extra seeds','capacity arms','search'],
        launch_requires=['same-source real five-player qualification','explicit accepted complete allocation','manual storage/RAM/mutex admission'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    with a.out.open('x') as f:
        json.dump(proposal(),f,indent=2,allow_nan=False);f.write('\n')


if __name__=='__main__':main()
