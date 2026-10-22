"""Post-hoc read-only analysis of PR352's verified unpruned singleton traces.

Run on the retained host; stream traces once and emit compact JSON on stdout.
No policy loading, engine calls, new hands or modifications to study roots.
"""
import argparse
import base64
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics


PERMUTATIONS = ((0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0))
STREETS = ('preflop', 'flop', 'turn', 'river')
BOTS = ('random', 'check-call', 'tight-aggressive', 'pot-pressure')
BASELINE = 'c602c3727df28160a9807716d3c9211d988e420c33ed7b0c04c2fd899afef06b'


def interval(values, comparisons=1):
    from scipy.stats import t
    n = len(values)
    if n < 2:
        raise ValueError('at least two independent blocks required')
    mean = statistics.mean(values)
    se = statistics.stdev(values) / math.sqrt(n)
    width = float(t.ppf(1 - .05 / (2 * comparisons), n - 1)) * se
    return dict(mean_bb100=mean, se_bb100=se, lower=mean-width, upper=mean+width, blocks=n)


def allowed_actions(state):
    """Mirror the pinned min/pot/conditional-jam menu, using public fields only."""
    legal = state['legal']
    actions = {('check' if legal['check'] else 'fold', 0)}
    if not legal['check']:
        actions.add(('call', 0))
    if legal['raise_to'] is not None:
        low, high = legal['raise_to']
        matched = state['players'][state['actor']][1] + legal['call']
        after_call = sum(p[2] for p in state['players']) + legal['call']
        actions.add(('raise', low))
        actions.add(('raise', min(high, max(low, matched + after_call))))
        if high-matched <= 2*after_call or high == low:
            actions.add(('raise', high))
    return actions


def classify(row, seat):
    own = [e for e in row['history'] if len(e) == 5 and e[1] == seat]
    pre = '/'.join(e[2] for e in own if e[0] == 'preflop') or 'none'
    fold = next((e[0] for e in own if e[2] == 'fold'), None)
    # A non-folding hand may end uncontested, not necessarily at showdown.
    live = sum(not p[3] for p in row['states'][-1]['players'])
    end = 'fold-'+fold if fold else ('showdown' if live > 1 else 'uncontested')
    pos = ('BTN', 'SB', 'BB')[(seat-row['button']) % 3]
    return f'{pos}: {pre} -> {end}'


def scan(path, expected_sha, bot, root):
    digest = hashlib.sha256()
    total = 0
    blocks, seats, positions = [], [[], [], []], [[], [], []]
    groups = defaultdict(lambda: dict(hands=0, sum_bb100=0., example=None))
    decisions = [0]*4
    off_menu = 0
    river_hands = two_live_river_hands = river_decisions = two_live_river_decisions = 0
    with path.open('rb') as stream:
        raw = next(stream)
        digest.update(raw)
        header = json.loads(raw)
        if (header['policies'][0]['sha256'] != BASELINE or header['seed'] != root
                or header['policies'][1:] != [dict(script=bot, version='nplayer-scripts-v1')]*2
                or header['identity']['stacks'] != [10000]*3 or header['identity']['big_blind'] != 100
                or header['identity']['schema'] != 'nplayer-button-live-actor-history-equity-k50-v1'):
            raise ValueError('trace/model/recipe identity mismatch')
        block_values, block_seats, block_positions = [], [[], [], []], [[], [], []]
        deck = None
        for raw in stream:
            digest.update(raw)
            row = json.loads(raw)
            block, perm = divmod(total, 6)
            if (row['hand'] != total or row['block'] != block or row['permutation'] != perm
                    or tuple(row['identities']) != PERMUTATIONS[perm] or row['button'] != block % 3
                    or row['bb'] != 100 or sum(row['rewards']) != 0):
                raise ValueError('invalid block, identity or payoff accounting')
            if perm == 0:
                deck = row['deck']
            elif deck != row['deck']:
                raise ValueError('duplicate block cards differ')
            seat = row['identities'].index(0)
            position = (seat-row['button']) % 3
            value = row['rewards'][seat]*100/row['bb']
            block_values.append(value)
            block_seats[seat].append(value)
            block_positions[position].append(value)
            has_river = has_two = False
            if len(row['states']) != len(row['actions'])+1 or len(row['actors']) != len(row['actions']):
                raise ValueError('incomplete decision snapshots')
            for state, action, actor in zip(row['states'], row['actions'], row['actors']):
                if state['actor'] != actor:
                    raise ValueError('snapshot actor mismatch')
                off_menu += tuple(action) not in allowed_actions(state)
                if actor != seat:
                    continue
                decisions[STREETS.index(state['street'])] += 1
                if state['street'] == 'river':
                    river_decisions += 1
                    has_river = True
                    if sum(not p[3] for p in state['players']) == 2:
                        has_two = True
                        two_live_river_decisions += 1
            river_hands += has_river
            two_live_river_hands += has_two
            path_name = classify(row, seat)
            pot = sum(p[0] for p in row['settlement']['pots'])/row['bb']
            pot_band = '<5BB' if pot < 5 else ('5-20BB' if pot < 20 else ('20-50BB' if pot < 50 else '>=50BB'))
            for key in ['path|'+path_name, 'pot|'+pot_band]:
                g = groups[key]
                g['hands'] += 1
                g['sum_bb100'] += value
                if g['example'] is None:
                    g['example'] = dict(root=root, block=block, permutation=perm, hand=total)
            total += 1
            if perm == 5:
                blocks.append(statistics.mean(block_values))
                for i in range(3):
                    seats[i].append(statistics.mean(block_seats[i]))
                    positions[i].append(statistics.mean(block_positions[i]))
                block_values, block_seats, block_positions = [], [[], [], []], [[], [], []]
    if total != header['hands'] or len(blocks) != header['blocks'] or total != len(blocks)*6:
        raise ValueError('incomplete trace')
    if digest.hexdigest() != expected_sha:
        raise ValueError('trace checksum mismatch')
    return dict(hands=total, blocks=blocks, seats=seats, positions=positions, groups=dict(groups),
                decisions=decisions, off_menu_actions=off_menu, sha256=expected_sha,
                river=dict(hands=river_hands, two_live_hands=two_live_river_hands,
                           decisions=river_decisions, two_live_decisions=two_live_river_decisions))


def analyze(root, receipt):
    final = root/'results.json'
    if ((root/'failure.json').exists() or json.loads((root/'status.json').read_text())['status'] != 'complete'
            or hashlib.sha256(final.read_bytes()).hexdigest() != receipt['results_sha256']):
        raise ValueError('settled parent receipt mismatch')
    by_bot = {}
    provenance = []
    for bot_index, bot in enumerate(BOTS):
        runs = []
        misses, decisions = [0]*4, [0]*4
        for phase, seed_base in [('nodes', 20261019351101), ('clock', 20261019351201)]:
            case = bot+'-baseline'
            directory = root/('comparison-'+phase)
            proof = json.loads((directory/'evaluation-verified.json').read_text())
            manifest_sha = hashlib.sha256((directory/'evaluation-manifest.json').read_bytes()).hexdigest()
            if proof != receipt['phases'][phase]['proof'] or proof['manifest_sha256'] != manifest_sha:
                raise ValueError('verified matrix identity mismatch')
            summary = receipt['phases'][phase]['summaries'][case]
            path = directory/'evaluation'/case/'play-0.jsonl'
            run = scan(path, summary['trace_sha256'], bot, seed_base+bot_index+1)
            if run['decisions'] != summary['decisions_by_identity_street'][0]:
                raise ValueError('decision counter mismatch')
            runs.append(run)
            for i in range(4):
                decisions[i] += run['decisions'][i]
                misses[i] += summary['misses_by_identity_street'][0][i]
            provenance.append(dict(phase=phase, case=case, path=str(path), sha256=run['sha256'],
                                   hands=run['hands'], off_menu_actions=run['off_menu_actions']))
        values = runs[0]['blocks']+runs[1]['blocks']
        hands = sum(r['hands'] for r in runs)
        groups = defaultdict(lambda: dict(hands=0, sum_bb100=0., examples=[]))
        for run in runs:
            for key, g in run['groups'].items():
                groups[key]['hands'] += g['hands']
                groups[key]['sum_bb100'] += g['sum_bb100']
                groups[key]['examples'].append(g['example'])
        for g in groups.values():
            g.update(frequency=g['hands']/hands, conditional_bb100=g['sum_bb100']/g['hands'],
                     contribution_bb100=g['sum_bb100']/hands)
        by_bot[bot] = dict(hands=hands, return95=interval(values), return_family95=interval(values, 4),
                          cohorts=[interval(r['blocks']) for r in runs],
                          by_seat=[interval(runs[0]['seats'][i]+runs[1]['seats'][i]) for i in range(3)],
                          by_position=[interval(runs[0]['positions'][i]+runs[1]['positions'][i]) for i in range(3)],
                          coverage=[dict(street=s, decisions=decisions[i], misses=misses[i],
                                         missing_fraction=misses[i]/decisions[i]) for i, s in enumerate(STREETS)],
                          river={k:sum(r['river'][k] for r in runs) for k in runs[0]['river']},
                          groups=dict(groups))
    return dict(status='complete', scope='post-hoc fixed unpruned PR350 3B; existing PR352 scripted hands only',
                baseline_policy_sha256=BASELINE, parent_results_sha256=receipt['results_sha256'],
                statistical_unit='six-hand deal block; cohorts pooled equally; exploratory family of four scripts',
                provenance=provenance, by_bot=by_bot)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--receipt-base64', required=True)
    a = p.parse_args()
    receipt = json.loads(base64.b64decode(a.receipt_base64))
    print(json.dumps(analyze(a.root, receipt), indent=2, allow_nan=False))
