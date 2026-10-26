"""How far a coarser n-player history key would merge the focal decisions of saved arena traces.

The exact history part is what `nplayer-button-live-actor-history-equity-k50-v1`
encodes besides the card class: position, street, live and all-in seats and every
public action with its amounts. The summary keeps the current street's actions
exactly and replaces earlier streets by the pot and each live seat's
stack-to-pot ratio at the street's start (in buckets), each earlier street's
capped raise count and the previous street's last aggressor.

`--level` coarsens further: 2 also summarizes the current street by its capped raise
count, last aggressor and the price to call (call over pot after calling, in buckets);
3 also replaces the live and all-in seat sets by the number of live players and the
hero's and last aggressor's order among them; 4 is 3 but keeps the hero's own
button-relative seat, which every n-player row requires to be fixed.

Traces don't record card classes, so both parts exclude them. Merged classes are
therefore an upper bound on what shares a full key; `missing_with_learned_sibling`
counts missing lookups whose summary class also contains a positive-mass lookup
of the same field, an optimistic proxy for coverage a coarser key could gain.
"""
import argparse
import gzip
import json
from bisect import bisect_right
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

STREETS = ('preflop', 'flop', 'turn', 'river')
KINDS = {'fold': 0, 'check': 1, 'call': 2, 'raise': 3}
# Pot in big blinds and stack-to-pot ratio at the start of the current street.
POT_EDGES = (2, 4, 8, 16, 32, 64, 128)
SPR_EDGES = (0.5, 1, 2, 4, 8, 16)
PRICE_EDGES = (0.1, 0.2, 0.3, 0.4)
RAISE_CAP = 3


def summary(history, state, seat, button, n, bb, level=1):
    """(exact, summary) history parts for the decision whose prefix is `history`."""
    rel = lambda s: (s - button) % n
    street = STREETS.index(state['street'])
    players = state['players']
    live = sum(1 << rel(s) for s, p in enumerate(players) if not p[3])
    all_in = sum(1 << rel(s) for s, p in enumerate(players) if not p[3] and p[0] == 0)
    events = [(STREETS.index(e[0]), rel(e[1]), KINDS[e[2]], e[3], e[4]) for e in history if e[1] != 'board']
    head = (rel(seat), street, live, all_in)
    exact = hash(head + tuple(events))
    current = tuple(e[1:] for e in events if e[0] == street)
    raises = [0] * street
    last_aggressor = -1
    for e in events:
        if e[0] < street and e[2] == KINDS['raise']:
            raises[e[0]] = min(raises[e[0]] + 1, RAISE_CAP)
            if e[0] == street - 1:
                last_aggressor = e[1]
    pot = sum(p[2] - p[1] for p in players) / bb
    spr = tuple(bisect_right(SPR_EDGES, (p[0] + p[1]) / max(pot * bb, 1)) if not p[3] else -1
                for p in (players[(button + i) % n] for i in range(n)))
    if level >= 2:
        street_raises = [e for e in current if e[1] == KINDS['raise']]
        call = state['legal']['call'] if state['legal'] else 0
        price = call / max(state['pot'] + call, 1)
        current = (min(len(street_raises), RAISE_CAP), street_raises[-1][0] if street_raises else -1,
                   bisect_right(PRICE_EDGES, price), len(current))
    if level >= 3:
        order = [r for r in range(n) if live >> r & 1]
        index = lambda r: order.index(r) if r in order else -1
        head = (len(order), index(rel(seat)), street, bin(all_in).count('1')) + ((rel(seat),) if level == 4 else ())
        spr = tuple(sorted(x for x in spr if x >= 0))
        last_aggressor = index(last_aggressor) if last_aggressor >= 0 else -1
        current = (current[0], index(current[1]) if current[1] >= 0 else -1) + current[2:]
    coarse = hash(head + (bisect_right(POT_EDGES, pot),) + spr + tuple(raises) + (last_aggressor,) + current)
    return exact, coarse


def scan(job):
    path, field, level = job
    exact, coarse = defaultdict(set), defaultdict(set)
    learned, missing = defaultdict(set), defaultdict(list)
    decisions = defaultdict(int)
    # A real key fixes the exact history part, so one key with two exact parts is a reconstruction error.
    key_history, conflicts = {}, 0
    with gzip.open(path, 'rt') as f:
        header = json.loads(next(f))
        bb = header['identity']['big_blind']
        for line in f:
            row = json.loads(line)
            n, button = len(row['stacks']), row['button']
            # The i-th action's prefix is every history event before it, board markers included.
            positions = [j for j, e in enumerate(row['history']) if e[1] != 'board']
            for i, lookup in enumerate(row['lookups']):
                if lookup.get('identity') != 0:
                    continue
                e, c = summary(row['history'][:positions[i]], row['states'][i], lookup['seat'], button, n, bb, level)
                if key_history.setdefault(lookup['key'], e) != e:
                    conflicts += 1
                street = lookup['street']
                decisions[street] += 1
                exact[street].add(e)
                coarse[street].add(c)
                if lookup['status'] == 'positive_mass':
                    learned[street].add(c)
                elif lookup['status'] == 'missing':
                    missing[street].append(c)
    if conflicts:
        raise ValueError(f'{path}: {conflicts} keys with more than one exact history')
    return field, {s: (decisions[s], exact[s], coarse[s], learned[s], missing[s]) for s in decisions}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--traces', type=Path, required=True, help='arena folder with b*/<field>-<arm>.jsonl.gz')
    parser.add_argument('--arm', default='control')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=12)
    parser.add_argument('--level', type=int, choices=(1, 2, 3, 4), default=1)
    args = parser.parse_args()
    jobs = [(str(p), p.name[:-len(f'-{args.arm}.jsonl.gz')], args.level) for p in sorted(args.traces.glob(f'b*/*-{args.arm}.jsonl.gz'))]
    merged = defaultdict(lambda: [0, set(), set(), set(), []])
    with Pool(args.workers) as pool:
        for field, streets in pool.imap_unordered(scan, jobs):
            for street, (d, e, c, l, m) in streets.items():
                for key in (field, 'all'):
                    slot = merged[key, street]
                    slot[0] += d
                    slot[1] |= e
                    slot[2] |= c
                    slot[3] |= l
                    if key == field:
                        slot[4] += m
    rows = []
    for (field, street), (d, e, c, l, m) in sorted(merged.items()):
        if field == 'all':
            m = [x for (f, s), v in merged.items() if f != 'all' and s == street for x in v[4]]
        rows.append({'field': field, 'street': STREETS[street], 'decisions': d, 'exact_histories': len(e),
                     'summary_histories': len(c), 'merge_factor': len(e) / len(c) if c else None,
                     'decisions_per_exact': d / len(e) if e else None, 'decisions_per_summary': d / len(c) if c else None,
                     'missing': len(m), 'missing_with_learned_sibling': sum(1 for x in m if x in l)})
    args.out.write_text(json.dumps({'format': 'nplayer-key-collapse-v1', 'arm': args.arm, 'level': args.level, 'traces': len(jobs),
                                    'pot_edges_bb': POT_EDGES, 'spr_edges': SPR_EDGES, 'raise_cap': RAISE_CAP,
                                    'rows': rows}, indent=1) + '\n')


if __name__ == '__main__':
    main()
