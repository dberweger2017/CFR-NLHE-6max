"""Compare two arms' first preflop actions by hand strength on saved paired arena traces.

For each focal hand it reconstructs the focal hole cards from the trace's deck
(seat button+1+i holds deck[i] and deck[n+i]), takes the focal's first preflop
action and whether a raise came before it, and groups hands by the scripted
bots' preflop score (`multi_arena.rs` `hand_score`). Results are realized chips,
not all-in adjusted: this is a description of ranges, not a strength estimate.
"""
import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path

TIERS = (0.30, 0.45, 0.60)
TIER_NAMES = ('weak (<0.30)', 'medium (0.30-0.45)', 'good (0.45-0.60)', 'strong (>=0.60)')


def score(a, b):
    """The scripted bots' public preflop card score (pairs from 0.61, AKs 0.655)."""
    hi, lo = max(a // 4, b // 4) + 2, min(a // 4, b // 4) + 2
    if hi == lo:
        return 0.55 + hi / 35
    return min(0.95, (hi + lo - 4) / 40 + (0.08 if a % 4 == b % 4 else 0) + (0.06 if hi - lo <= 2 else 0))


def tier(s):
    return sum(s >= t for t in TIERS)


def scan(job):
    path, = job
    out = defaultdict(lambda: [0, 0])
    with gzip.open(path, 'rt') as f:
        next(f)
        for line in f:
            row = json.loads(line)
            n, button = len(row['stacks']), row['button']
            seat = row['identities'].index(0)
            offset = (seat - button - 1) % n
            t = tier(score(row['deck'][offset], row['deck'][n + offset]))
            raised_before = False
            action = None
            for e in row['history']:
                if e[0] != 'preflop' or e[1] == 'board':
                    continue
                if e[1] == seat:
                    action = e[2]
                    break
                raised_before |= e[2] == 'raise'
            situation = 'facing a raise' if raised_before else 'unopened'
            for key in ((t, situation, action), (t, situation, 'all'), (t, 'all', action), (t, 'all', 'all')):
                slot = out[key]
                slot[0] += 1
                slot[1] += row['rewards'][seat]
    return dict(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--traces', type=Path, required=True, help='arena folder with b*/<field>-<arm>.jsonl.gz')
    parser.add_argument('--arms', nargs=2, default=('control', 'live'))
    parser.add_argument('--fields', nargs='+', default=('check-call', 'trained', 'pot-pressure'))
    parser.add_argument('--bb', type=int, default=100)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    from multiprocessing import Pool
    result = {'format': 'nplayer-preflop-ranges-v1', 'tiers': TIER_NAMES, 'fields': {}}
    with Pool(16) as pool:
        for field in args.fields:
            result['fields'][field] = {}
            for arm in args.arms:
                totals = defaultdict(lambda: [0, 0])
                for part in pool.map(scan, [(str(p),) for p in sorted(args.traces.glob(f'b*/{field}-{arm}.jsonl.gz'))]):
                    for key, (hands, chips) in part.items():
                        totals[key][0] += hands
                        totals[key][1] += chips
                hands = sum(v[0] for k, v in totals.items() if k[1:] == ('all', 'all'))
                rows = []
                for (t, situation, action), (count, chips) in sorted(totals.items(), key=lambda kv: (kv[0][0], kv[0][1], str(kv[0][2]))):
                    base = totals[t, situation, 'all'][0]
                    rows.append({'tier': TIER_NAMES[t], 'situation': situation, 'action': action, 'hands': count,
                                 'share_of_situation': count / base if base else None,
                                 'bb_per_hand': chips / count / args.bb if count else None,
                                 'bb100_contribution': chips / hands / args.bb * 100})
                result['fields'][field][arm] = {'hands': hands, 'rows': rows}
    args.out.write_text(json.dumps(result, indent=1) + '\n')


if __name__ == '__main__':
    main()
