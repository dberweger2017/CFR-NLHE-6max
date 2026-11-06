"""Wide-grid models for short stacks on Open Poker tables (docs/openpoker-wide-stacks.md).

`widemix` (six players) and `huwide` (heads-up) are live-order 10B models trained with every
seat's depth drawn from the wide grid, 1–250 BB, so short stacks meet deep ones at a table.
Each plays against the route it would replace at tables where some seat holds under 10 BB:
`humix` heads-up, `p3mix` at three players and `mix` at four and six, all through the
projected view. Every contrast is arm 1 minus arm 0, all-in adjusted, over blocks. Collection,
replay, scanning and the report reuse the phantom/depth study's code with these tables and rules.

`--seed-run` picks one of three independently seeded model pairs: run 1 decides, on four banks;
runs 2 and 3 replicate, on one bank each and on their own roots.
"""
import sys

from scripts import openpoker_phantom_depth as study

ROOT = 20261106100000
SCRIPT_FIELDS = ('pot-pressure', 'tight-aggressive', 'check-call', 'random')
# Tables are already in the client's capped form: no seat holds more than the largest other seat.
HEADS_UP = {'2p-3bb': (3, 3), '2p-5bb': (5, 5), '2p-8bb': (8, 8)}
SHORT = {3: {'3p-5bb': (5, 5, 5), '3p-short-deep': (4, 100, 100), '3p-unequal': (8, 40, 100)},
         4: {'4p-short-deep': (5, 100, 100, 100)},
         6: {'6p-5bb': (5,) * 6, '6p-short-deep': (3, 100, 100, 100, 100, 100),
             '6p-unequal': (8, 100, 50, 100, 150, 100)}}
CURRENT = {2: 'humix', 3: 'p3mix', 4: 'mix', 6: 'mix'}


def wide(n):
    return 'huwide' if n == 2 else 'widemix'


def tables():
    """Each table: its study, game, focals (arm 0, arm 1), views and fields; the first field is primary."""
    views = ['projected', 'projected']
    out = []
    for name, stacks in HEADS_UP.items():
        fields = {'current': ['humix']}
        fields.update({s: [s] for s in SCRIPT_FIELDS})
        fields['wide-copies'] = ['huwide']
        out.append(dict(study='short', table=name, players=2, stack_bb=100, stacks_bb=list(stacks),
                        focals=['humix', 'huwide'], views=views, fields=fields))
    for n, named in SHORT.items():
        rest = n - 1
        for name, stacks in named.items():
            fields = {'mixed': list(study.MIXED[n])}
            fields.update({s: [s] * rest for s in SCRIPT_FIELDS})
            fields['current-copies'] = [CURRENT[n]] * rest
            fields['wide-copies'] = [wide(n)] * rest
            out.append(dict(study='short', table=name, players=n, stack_bb=100, stacks_bb=list(stacks),
                            focals=[CURRENT[n], wide(n)], views=views, fields=fields))
    return out


def verdict(table_study, lower, upper):
    if lower > 0:
        return 'wide better'
    return 'current better' if upper < 0 else 'no difference shown'


def main():
    run = 1
    if '--seed-run' in sys.argv:
        i = sys.argv.index('--seed-run')
        run = int(sys.argv[i + 1])
        del sys.argv[i:i + 2]
    if run not in (1, 2, 3):
        raise ValueError('--seed-run is 1, 2 or 3')
    study.tables, study.verdict = tables, verdict
    study.ROOT = ROOT + 100_000 * (run - 1)
    study.BANKS = 4 if run == 1 else 1
    study.HARM_STUDIES = ('short',)
    study.FORMAT = 'openpoker-wide-stacks-v1'
    study.__doc__ = __doc__
    study.main()


if __name__ == '__main__':
    main()
