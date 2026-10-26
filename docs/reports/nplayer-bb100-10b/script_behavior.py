"""Post-hoc descriptive audit of existing PR355 script traces; no new hands."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import statistics
import time

STREETS = ('preflop', 'flop', 'turn', 'river')


def fresh_group():
    return dict(hands=0, reward_bb_sum=0, positive_net_hands=0, positive_net_bb_sum=0,
                gross_pot_awards_bb_sum_in_positive_hands=0, final_total_pot_bb_sum_in_positive_hands=0,
                actions={name: Counter() for name in ('all',) + STREETS},
                raise_ratios={name: [] for name in ('all',) + STREETS})


def audit(root, out):
    start = time.monotonic()
    load = lambda p: json.loads(p.read_text())
    assert load(root/'status.json')['status'] == 'complete' and not (root/'failure.json').exists()
    result = load(root/'results.json')
    assert result['status'] == 'settled'
    proof = load(root/'comparison/evaluation-verified.json')
    assert proof['status'] == 'passed' and proof['cases'] == 18 and proof['hands'] == 884736
    out.mkdir(parents=True, exist_ok=False)
    os.sched_setaffinity(0, {0})
    groups, sources = {}, {}
    for opponent in ('random', 'check-call'):
        expected = next(x for x in result['results']['rows'] if x['opponent'] == opponent)
        for model in ('baseline', 'candidate'):
            case = opponent + '-' + model
            folder = root/'comparison/evaluation'/case
            path = folder/'play-0.jsonl'
            before = path.stat()
            g = groups[case] = fresh_group()
            pooled = groups.setdefault('pooled-' + model, fresh_group())
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                line = next(stream);digest.update(line);header = json.loads(line)
                assert header['hands'] == 49152 and header['blocks'] == 8192
                assert header['policies'][0]['sha256'] == result['results']['models'][model]['sha256']
                for line in stream:
                    digest.update(line);row = json.loads(line)
                    hero = row['identities'].index(0)
                    assert sum(row['rewards']) == 0 and len(row['states']) == len(row['actions']) + 1
                    reward = row['rewards'][hero] / row['bb']
                    gross = (row['rewards'][hero] + row['settlement']['contributions'][hero] - row['settlement']['refunds'][hero]) / row['bb']
                    assert gross >= 0
                    total_pot = sum(p[0] for p in row['settlement']['pots']) / row['bb']
                    for group in (g, pooled):
                        group['hands'] += 1;group['reward_bb_sum'] += reward
                        if reward > 0:
                            group['positive_net_hands'] += 1;group['positive_net_bb_sum'] += reward
                            group['gross_pot_awards_bb_sum_in_positive_hands'] += gross
                            group['final_total_pot_bb_sum_in_positive_hands'] += total_pot
                    for state, action in zip(row['states'][:-1], row['actions']):
                        if state['actor'] != hero:
                            continue
                        kind, target = action
                        street, legal = state['street'], state['legal']
                        assert kind in ('check', 'fold', 'call', 'raise') and street in STREETS
                        facing_bet = legal['call'] > 0
                        facing_allin = facing_bet and any(p[0] == 0 and not p[3] for i, p in enumerate(state['players']) if i != hero)
                        ratio = None
                        if kind == 'raise':
                            assert target > state['wager']
                            ratio = (target - state['wager']) / max(1, state['pot'] + legal['call'])
                        for group in (g, pooled):
                            for label in ('all', street):
                                c = group['actions'][label]
                                c['decisions'] += 1;c[kind] += 1
                                c['check_opportunities'] += bool(legal['check'])
                                c['raise_opportunities'] += legal['raise_to'] is not None
                                if facing_bet:
                                    c['facing_bet'] += 1;c['fold_facing_bet'] += kind == 'fold'
                                if facing_allin:
                                    c['facing_allin'] += 1;c['fold_facing_allin'] += kind == 'fold'
                                if kind == 'raise':
                                    c['allin_raise'] += target == state['players'][hero][0] + state['players'][hero][1]
                                    group['raise_ratios'][label].append(ratio)
            actual = digest.hexdigest()
            assert actual == load(folder/'result.json')['trace_sha256'] == load(folder/'replay.json')['trace_sha256']
            assert path.stat().st_size == before.st_size and path.stat().st_mtime_ns == before.st_mtime_ns
            assert g['hands'] == 49152
            assert abs(g['reward_bb_sum'] * 100 / g['hands'] - expected[model+'_absolute']['mean_bb100']) < 1e-8
            sources[case] = dict(path=str(path), bytes=before.st_size, mtime_ns=before.st_mtime_ns,
                                 trace_sha256=actual, hands=g['hands'], header_seed=header['seed'])
            print(json.dumps(dict(event='trace-audited', case=case, hands=g['hands'])), flush=True)
    for g in groups.values():
        g['mean_bb100'] = 100 * g['reward_bb_sum'] / g['hands']
        wins = g['positive_net_hands']
        g['mean_positive_net_bb'] = g['positive_net_bb_sum'] / wins
        g['mean_gross_pot_award_bb_positive_net'] = g['gross_pot_awards_bb_sum_in_positive_hands'] / wins
        g['mean_final_total_pot_bb_positive_net'] = g['final_total_pot_bb_sum_in_positive_hands'] / wins
        for label, c in g['actions'].items():
            assert sum(c[k] for k in ('check', 'call', 'fold', 'raise')) == c['decisions']
            for action in ('check', 'call', 'fold', 'raise'):
                c[action+'_pct_decisions'] = 100 * c[action] / c['decisions']
            for numerator, denominator, name in [('check', 'check_opportunities', 'check_pct_opportunities'),
                    ('raise', 'raise_opportunities', 'raise_pct_opportunities'),
                    ('fold_facing_bet', 'facing_bet', 'fold_pct_facing_bet'),
                    ('fold_facing_allin', 'facing_allin', 'fold_pct_facing_allin')]:
                c[name] = 100 * c[numerator] / c[denominator] if c[denominator] else None
            ratios = g['raise_ratios'][label]
            c['mean_raise_increment_over_after_call_pot'] = statistics.mean(ratios) if ratios else None
            c['median_raise_increment_over_after_call_pot'] = statistics.median(ratios) if ratios else None
        del g['raise_ratios']
    value = dict(status='descriptive-posthoc', root=str(root), completed_utc=datetime.now(timezone.utc).isoformat(),
                 wall_seconds=time.monotonic()-start, analyzed_initial_hands=196608, newly_played_hands=0,
                 cpu_affinity=[0], sources=sources, groups=groups,
                 interpretation='All four complete pure-script initial traces; identity0 only; no hand selection, reproduction double-counting, new outcomes, hand-strength inference, causal test or Nash/exploitability measurement.')
    (out/'script-behavior.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(event='complete', path=str(out/'script-behavior.json'), wall_seconds=value['wall_seconds'])),flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    with open('/tmp/cfr-nplayer-bb100-10b.lock','a') as own, open('/tmp/cfr-cygnus-exclusive.lock','a') as normal:
        for lock in (own,normal):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        audit(a.root,a.out)
