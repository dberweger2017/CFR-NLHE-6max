"""Bounded parallel version of the independent Python accumulator audit."""
import argparse
from collections import deque
from concurrent.futures import ProcessPoolExecutor
import gzip
from itertools import islice, zip_longest
import json
import math
from pathlib import Path

from scripts.audit_nplayer_policy import sha


def check_chunk(task):
    pairs, mode, scope, players = task
    streets = [dict(entries=0, visits=0, zero_visit_entries=0) for _ in range(4)]
    counts = dict(rows=0, average_rows=0, current_rows=0, zero_mass_rows=0)
    first = previous = None
    for left, right in pairs:
        if left is None or right is None:
            raise ValueError('checkpoint/policy row count differs')
        src, row = json.loads(left), json.loads(right)
        if len(src) != 7 or len(row) != 5 or src[:4] != row[:4]:
            raise ValueError('row identity differs')
        key, owner, street, code, visits, regrets, average = src
        if (len(key) != 32 or any(c not in '0123456789abcdef' for c in key)
                or previous is not None and previous >= key
                or not 0 <= owner < players or not 0 <= street < 4 or visits < 0):
            raise ValueError('invalid key/order/owner/street/visits')
        if first is None:
            first = key
        previous = key
        use_average = mode != 'current' and street <= scope
        weights = average if use_average else [max(0., x) for x in regrets]
        if (not weights or len(regrets) != code.bit_count() or len(weights) != code.bit_count()
                or any(not math.isfinite(x) for x in regrets)
                or any(not math.isfinite(x) or x < 0 for x in weights)):
            raise ValueError('invalid source weights')
        total = math.fsum(weights)
        expected = [w / total for w in weights] if total else [1 / len(weights)] * len(weights)
        if (len(row[4]) != len(expected)
                or any(not math.isfinite(x) or not 0 <= x <= 1 for x in row[4])
                or max(abs(x - y) for x, y in zip(row[4], expected)) > 1e-14):
            raise ValueError('exported probability differs')
        stats = streets[street]
        stats['entries'] += 1
        stats['visits'] += visits
        stats['zero_visit_entries'] += visits == 0
        counts['rows'] += 1
        counts['average_rows' if use_average else 'current_rows'] += 1
        counts['zero_mass_rows'] += not total
    return dict(first=first, last=previous, counts=counts, streets=streets)


def audit(checkpoint, policy, workers=8, chunk_rows=16384):
    if not 1 <= workers <= 8 or not 1 <= chunk_rows <= 16384:
        raise ValueError('audit worker/chunk bounds')
    cp_sha, policy_sha = sha(checkpoint), sha(policy)
    streets = [dict(entries=0, visits=0, zero_visit_entries=0) for _ in range(4)]
    counts = dict(rows=0, average_rows=0, current_rows=0, zero_mass_rows=0)
    previous = None

    def merge(result):
        nonlocal previous
        if previous is not None and result['first'] <= previous:
            raise ValueError('key order differs across chunks')
        previous = result['last']
        for key in counts:
            counts[key] += result['counts'][key]
        for out, inc in zip(streets, result['streets']):
            for key in out:
                out[key] += inc[key]

    with gzip.open(checkpoint, 'rt') as a, gzip.open(policy, 'rt') as b:
        source, header = json.loads(next(a)), json.loads(next(b))
        if (source['format'] != 'nplayer-cfr-v1' or header['format'] != 'nplayer-policy-v1'
                or header['source_checkpoint_sha256'] != cp_sha
                or source['game'] != header['identity'] or source['players'] != header['players']
                or source['entries'] != header['entries']
                or source['last_average_street'] != header['last_average_street']):
            raise ValueError('export/checkpoint header or lineage differs')
        mode = header['strategy']
        if (mode not in ('current', 'average', 'scoped-average')
                or header['continuation'] != ('current-after-average-scope' if mode == 'scoped-average' else 'none')
                or mode == 'average' and header['last_average_street'] != 3):
            raise ValueError('averaging mode differs')
        pairs = zip_longest(a, b)
        pending = deque()
        with ProcessPoolExecutor(max_workers=workers) as pool:
            while chunk := list(islice(pairs, chunk_rows)):
                pending.append(pool.submit(check_chunk, (chunk, mode, source['last_average_street'], source['players'])))
                if len(pending) >= 2 * workers:
                    merge(pending.popleft().result())
            while pending:
                merge(pending.popleft().result())
    if counts['rows'] != source['entries']:
        raise ValueError('entry count differs')
    for street, stats in enumerate(streets):
        stats['decisions'] = source['counts']['decisions'][street]
        stats['missing_decisions'] = source['counts']['missing'][street]
        stats['missing_decision_share'] = stats['missing_decisions'] / stats['decisions'] if stats['decisions'] else None
        stats['visits_per_key'] = stats['visits'] / stats['entries'] if stats['entries'] else None
    return dict(by_street=streets, status='passed', checkpoint_sha256=cp_sha,
                policy_sha256=policy_sha, strategy=mode, last_average_street=source['last_average_street'], **counts)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkpoint', type=Path)
    parser.add_argument('policy', type=Path)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    print(json.dumps(audit(args.checkpoint, args.policy, args.workers), indent=2))
