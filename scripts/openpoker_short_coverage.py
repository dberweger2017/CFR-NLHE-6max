"""Covering short multiway Open Poker tables (docs/openpoker-short-coverage.md).

Two levers for `widemix`'s untrained postflop rows at short six-player tables: effective-stack
keys (`eff`), short-heavy deals (`short`) and both (`effshort`).

`--stage screen --candidate X`: X against the 4B control `ctrl` at #461's seven short tables, one
bank of 512 blocks on roots shared by every candidate. `coverage` reads the three screens' scan
receipts and applies the fixed advance rule; nothing here makes a chip claim.

`--stage main --seed-run R`: the advancing recipe at 10B (`cand`) against the live `widemix`,
exactly #461's evaluation and rules. Collection, replay, scanning and the report reuse the
phantom/depth study's code.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from scripts import nplayer_loss_diagnosis as diagnosis
from scripts import openpoker_phantom_depth as study
from scripts.openpoker_wide_stacks import SCRIPT_FIELDS, SHORT

SCREEN_ROOT = 20261108100000
MAIN_ROOT = 20261108200000
SCREEN_BLOCKS = 512
CANDIDATES = ('eff', 'short', 'effshort')  # the preference order within 1 point
ADVANCE_POINTS = 10.0
TIE_POINTS = 1.0
POSTFLOP = ('flop', 'turn', 'river')


def tables(focals):
    """#461's tables and fields: `mixed` first, the four scripts and, at six players, live copies."""
    out = []
    for n, named in SHORT.items():
        for name, stacks in named.items():
            fields = {'mixed': list(study.MIXED[n])}
            fields.update({s: [s] * (n - 1) for s in SCRIPT_FIELDS})
            if n == 6:
                fields['live-copies'] = ['widemix'] * (n - 1)
            out.append(dict(study='coverage', table=name, players=n, stack_bb=100, stacks_bb=list(stacks),
                            focals=list(focals), views=['projected', 'projected'], fields=fields))
    return out


def verdict(table_study, lower, upper):
    if lower > 0:
        return 'candidate better'
    return 'widemix better' if upper < 0 else 'no difference shown'


def counts(receipts, arm, table, fields, streets):
    """(untrained, total) decisions of one arm at one table, over its fields and the given streets."""
    untrained = total = 0
    for field in fields:
        for key, (count, _) in receipts[f'{arm}-{table}-b0', field]['decisions'].items():
            street, status = key.split('|')[:2]
            if street in streets:
                total += count
                untrained += count if status in diagnosis.UNTRAINED else 0
    return untrained, total


def share(pair):
    return 100.0 * pair[0] / pair[1] if pair[1] else None


def coverage(args):
    """Stage A's fixed rule over the three screen arenas (one bank each, receipts from `scan`)."""
    six = [name for name in SHORT[6]]
    result = {'format': 'openpoker-short-coverage-screen-v1', 'metric': 'pooled postflop untrained share, six-player tables, all fields',
              'advance_points': ADVANCE_POINTS, 'tie_points': TIE_POINTS, 'candidates': {}}
    for c in CANDIDATES:
        out = args.screens / c / 'out'
        receipts = {(r['label'], r['field']): r for r in (json.loads(p.read_text()) for p in (out / 'receipts').glob('*.json'))}
        if any(r['fallback_violations'] for r in receipts.values()):
            raise ValueError(f'{c}: fallback violations')
        entry = {'tables': {}}
        pooled = {'a0': [0, 0], 'a1': [0, 0]}
        below_each = True
        for t in tables(['ctrl', c]):
            fields = list(t['fields'])
            row = {}
            for arm in ('a0', 'a1'):
                row[arm] = {s: share(counts(receipts, arm, t['table'], fields, (s,))) for s in diagnosis.STREETS}
                post = counts(receipts, arm, t['table'], fields, POSTFLOP)
                row[arm]['postflop'] = share(post)
                if t['table'] in six:
                    pooled[arm][0] += post[0]
                    pooled[arm][1] += post[1]
            if t['table'] in six:
                below_each &= row['a1']['postflop'] < row['a0']['postflop']
            entry['tables'][t['table']] = row
        entry['ctrl_metric'], entry['metric'] = share(pooled['a0']), share(pooled['a1'])
        entry['reduction_points'] = entry['ctrl_metric'] - entry['metric']
        entry['below_ctrl_at_each_six_player_table'] = below_each
        entry['qualifies'] = entry['reduction_points'] >= ADVANCE_POINTS and below_each
        result['candidates'][c] = entry
    qualified = [c for c in CANDIDATES if result['candidates'][c]['qualifies']]
    advance = None
    if qualified:
        best = min(result['candidates'][c]['metric'] for c in qualified)
        advance = next(c for c in qualified if result['candidates'][c]['metric'] <= best + TIE_POINTS)
    result['advance'] = advance
    diagnosis.create(args.out, json.dumps(result, indent=1) + '\n')
    print(json.dumps({c: [round(e['reduction_points'], 2), e['qualifies']] for c, e in result['candidates'].items()} | {'advance': advance}))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'coverage':
        parser = argparse.ArgumentParser(description=coverage.__doc__)
        parser.add_argument('command')
        parser.add_argument('--screens', type=Path, required=True, help='folder holding one screen root per candidate')
        parser.add_argument('--out', type=Path, required=True)
        return coverage(parser.parse_args())
    stage, candidate, run = None, None, 1
    for flag in ('--stage', '--candidate', '--seed-run'):
        if flag in sys.argv:
            i = sys.argv.index(flag)
            value = sys.argv[i + 1]
            del sys.argv[i:i + 2]
            if flag == '--stage':
                stage = value
            elif flag == '--candidate':
                candidate = value
            else:
                run = int(value)
    if stage == 'screen':
        if candidate not in CANDIDATES:
            raise ValueError(f'--candidate is one of {CANDIDATES}')
        study.tables = lambda: tables(['ctrl', candidate])
        study.ROOT, study.BANKS, study.BLOCKS = SCREEN_ROOT, 1, SCREEN_BLOCKS
    elif stage == 'main':
        if run not in (1, 2, 3):
            raise ValueError('--seed-run is 1, 2 or 3')
        study.tables = lambda: tables(['widemix', 'cand'])
        study.ROOT = MAIN_ROOT + 100_000 * (run - 1)
        study.BANKS = 4 if run == 1 else 1
    else:
        raise ValueError('--stage is screen or main')
    study.verdict = verdict
    study.HARM_STUDIES = ('coverage',)
    study.FORMAT = 'openpoker-short-coverage-v1'
    study.__doc__ = __doc__
    study.main()


if __name__ == '__main__':
    main()
