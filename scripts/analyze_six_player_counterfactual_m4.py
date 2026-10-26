"""Proof-gated conditional MC readout for PR438; no arena/whole-game verdict."""
import argparse
from collections import Counter, defaultdict
import csv
import json
import math
from pathlib import Path
import statistics

from scripts.six_player_counterfactual_m4 import sha, dump

FAMILY = 256
DISCOVERY = 64
HELDOUT = 2048


def contrast(qs, coefficients):
    if len(qs) != HELDOUT or not coefficients or any(not math.isfinite(c) for c in coefficients):
        raise ValueError('fixed heldout count/coefficients differ')
    if any(len(q) != len(coefficients) or any(not math.isfinite(v) or not -100 <= v <= 500 for v in q) for q in qs):
        raise ValueError('invalid six-player branch payoff')
    values = [math.fsum(c*v for c, v in zip(coefficients, q)) for q in qs]
    mean = statistics.mean(values)
    variance = statistics.variance(values)
    se = math.sqrt(variance/HELDOUT)
    width = 600*math.fsum(abs(c) for c in coefficients)
    logarithm = math.log(4*FAMILY/.05)
    radius = math.sqrt(2*variance*logarithm/HELDOUT) + 7*width*logarithm/(3*(HELDOUT-1))
    return dict(mean_bb=mean, standard_error_bb=se, lower95_family_bb=mean-radius,
                upper95_family_bb=mean+radius, range_width_bb=width,
                normal_lower95_bb=mean-1.959963984540054*se,
                normal_upper95_bb=mean+1.959963984540054*se)


def choose_discovery(qs):
    if len(qs) != DISCOVERY or not qs or not qs[0]:
        raise ValueError('fixed discovery count differs')
    n = len(qs[0])
    if any(len(q) != n or any(not math.isfinite(v) or not -100 <= v <= 500 for v in q) for q in qs):
        raise ValueError('invalid discovery values')
    means = [statistics.mean(q[a] for q in qs) for a in range(n)]
    return max(range(n), key=lambda a: (means[a], -a))


def root_summary(root, discovery, heldout):
    p = root['probabilities']
    n = len(root['actions'])
    if len(p) != n or not 1 <= n <= 6 or any(not math.isfinite(v) or not 0 <= v <= 1 for v in p) or abs(math.fsum(p)-1) > 1e-12:
        raise ValueError('root probability/menu identity differs')
    if len(discovery) != DISCOVERY or len(discovery[0]) != n:
        raise ValueError('discovery menu differs')
    selected = choose_discovery(discovery)  # heldout cannot choose the alternative.
    qs = [q['values'] for q in heldout]
    values = []
    for a, action in enumerate(root['actions']):
        coefficients = [(1. if a == b else 0.)-p[b] for b in range(n)]
        delta = contrast(qs, coefficients)
        values.append(dict(action_index=a, action=action, probability=p[a],
                           value_bb=statistics.mean(q[a] for q in qs),
                           minus_blueprint=delta))
    reference = next((i for i,a in enumerate(root['actions']) if a[0] in ('check','call')),0)
    # The family event already covers every action-minus-mixture. Subtracting
    # simultaneous endpoints gives valid (conservative) action-minus-passive
    # bounds with no extra tests or retrospective family change.
    baseline = values[reference]['minus_blueprint']
    for a, value in enumerate(values):
        delta = value['minus_blueprint']
        value['minus_passive'] = dict(
            mean_bb=value['value_bb']-values[reference]['value_bb'],
            lower95_family_bb=0. if a==reference else delta['lower95_family_bb']-baseline['upper95_family_bb'],
            upper95_family_bb=0. if a==reference else delta['upper95_family_bb']-baseline['lower95_family_bb'],
            method='Difference of simultaneous action-minus-mixture intervals; no additional test family')
    mixture = [math.fsum(v*w for v, w in zip(p, q)) for q in qs]
    mass = [sum(q['lookups'][i] for q in heldout) for i in range(3)]
    return dict(**root, passive_reference_action_index=reference, selected_action_index=selected,
                selected_action=root['actions'][selected],
                blueprint_value_bb=statistics.mean(mixture),
                blueprint_standard_error_bb=statistics.stdev(mixture)/HELDOUT**.5,
                action_values=values,
                selected_minus_blueprint=values[selected]['minus_blueprint'],
                heldout_continuation_lookups=dict(zip(['positive_mass','zero_mass','missing'],mass)))


def readout(native, inventory, output, *, fixture=False):
    native, output = Path(native), Path(output)
    receipt = json.loads((native/'verified.json').read_text())
    if (receipt['status'] != 'passed' or not receipt.get('full_panel_work')
            or receipt['discovery_worlds'] != DISCOVERY or receipt['heldout_worlds'] != HELDOUT
            or not receipt['float64_and_work_reproduced'] or not receipt['root_profiles_reproduced']
            or bool(receipt['qualification_only']) != fixture or bool(receipt['main_started']) == fixture):
        raise ValueError('full fixed-work native/reproduction barrier not passed')
    for name, key in [('roots.jsonl','roots_sha256'),('worlds.jsonl','worlds_sha256'),('worlds.repeat.jsonl','worlds_repeat_sha256')]:
        if sha(native/name) != receipt[key]:
            raise ValueError('native evidence changed')
    if receipt['worlds_sha256'] != receipt['worlds_repeat_sha256']:
        raise ValueError('byte reproduction differs')
    inventory = json.loads(Path(inventory).read_text())
    if inventory['states_sha256'] != receipt['states_sha256']:
        raise ValueError('panel inventory differs')
    roots = {}
    for line in (native/'roots.jsonl').read_text().splitlines():
        root = json.loads(line)
        if root['id'] in roots:
            raise ValueError('duplicate root')
        roots[root['id']] = root
    if len(roots) != receipt['roots'] or len(roots) != inventory['roots']:
        raise ValueError('incomplete root count')
    worlds = defaultdict(dict)
    with (native/'worlds.jsonl').open() as f:
        for line in f:
            row = json.loads(line)
            sid, phase, i = row['id'], row['phase'], row['world']
            expected = {'discovery': DISCOVERY, 'heldout': HELDOUT}
            if sid not in roots or phase not in expected or type(i) is not int or not 0 <= i < expected[phase]:
                raise ValueError('world identity/phase differs')
            key = (sid,phase)
            if i in worlds[key]:
                raise ValueError('duplicate world')
            if (len(row['lookups']) != 3 or any(type(v) is not int or v < 0 for v in row['lookups'])):
                raise ValueError('lookup counters differ')
            worlds[key][i] = row
    panel = []
    for sid, root in roots.items():
        for phase, count in [('discovery', DISCOVERY),('heldout',HELDOUT)]:
            if set(worlds[sid,phase]) != set(range(count)):
                raise ValueError('incomplete worlds; no exclusions')
        discovery = [worlds[sid,'discovery'][i]['values'] for i in range(DISCOVERY)]
        heldout = [worlds[sid,'heldout'][i] for i in range(HELDOUT)]
        panel.append(root_summary(root,discovery,heldout))
    # Each root has<=6 action-vs-mixture contrasts plus1 selected contrast.
    if sum(len(r['actions'])+1 for r in panel) > FAMILY:
        raise ValueError('predeclared family exceeded')
    output.mkdir(exist_ok=False)
    rows = []
    for root in panel:
        for value in root['action_values']:
            delta = value['minus_blueprint']
            rows.append(dict(id=root['id'],stratum=root['stratum'],hero=root['hero'],street=root['street'],
                             status=root['status'],action_index=value['action_index'],kind=value['action'][0],raise_to=value['action'][1],
                             probability=value['probability'],value_bb=value['value_bb'],blueprint_value_bb=root['blueprint_value_bb'],
                             discovery_selected=value['action_index']==root['selected_action_index'],
                             passive_reference_index=root['passive_reference_action_index'],
                             minus_passive_mean_bb=value['minus_passive']['mean_bb'],
                             minus_passive_lower95_family_bb=value['minus_passive']['lower95_family_bb'],
                             minus_passive_upper95_family_bb=value['minus_passive']['upper95_family_bb'],**delta))
    with (output/'actions.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows)
    result=dict(status='settled',fixture_only=fixture,roots=len(panel),discovery_worlds=DISCOVERY,heldout_worlds=HELDOUT,
                family_size_upper=FAMILY,reported_contrasts=sum(len(r['actions'])+1 for r in panel),
                interval_method='Maurer-Pontil2009 theorem4; two tails, Bonferroni family256, width600*L1(coefficients),2048 independent conditional worlds. Normal95 auxiliary only.',
                root_mass_counts=dict(Counter(r['status'] for r in panel)),
                conditional_roots_with_selected_gain=sum(r['selected_minus_blueprint']['lower95_family_bb']>0 for r in panel),
                panel=panel,native_verified_sha256=sha(native/'verified.json'),
                actions_sha256=sha(output/'actions.csv'),no_whole_hand_strength_verdict=True,
                limitations='Fixed selected conditional roots, known check-call law, one frozen lineage/continuation; not a population-weighted win rate, causal attribution of PR431 regression or equilibrium claim.')
    dump(output/'results.json',result)
    dump(output/'verified.json',dict(status='passed',roots=len(panel),results_sha256=sha(output/'results.json'),
                                    actions_sha256=sha(output/'actions.csv'),no_exclusions=True,fixture_only=fixture))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('native',type=Path);p.add_argument('inventory',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--fixture',action='store_true')
    a=p.parse_args()
    r=readout(a.native,a.inventory,a.output,fixture=a.fixture)
    print(json.dumps(dict(status=r['status'],roots=r['roots'],fixture_only=r['fixture_only'])))

if __name__=='__main__':main()
