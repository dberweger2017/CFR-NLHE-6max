"""A larger wide-depth model for short multiway Open Poker tables (docs/openpoker-wide-capacity.md).

`widecap` is `widemix`'s recipe with a 400M-entry table instead of 250M: same wide grid, same
10B nodes, new seeds. The live `widemix` (#458 run 1) froze at the cap after about a quarter of
its iterations and still has no trained row for many postflop decisions at short multiway
tables. Each `widecap` plays against the live `widemix` at the seven short 3-, 4- and 6-player
tables of #458, both through the projected view. Every contrast is arm 1 minus arm 0, all-in
adjusted, over blocks. Collection, replay, scanning and the report reuse the phantom/depth
study's code with these tables and rules.

`--seed-run` picks one of three independently seeded models: run 1 decides, on four banks;
runs 2 and 3 replicate, on one bank each and on their own roots.
"""
import sys

from scripts import openpoker_phantom_depth as study
from scripts.openpoker_wide_stacks import SCRIPT_FIELDS, SHORT

ROOT = 20261107100000


def tables():
    """Each table: its study, game, focals (arm 0, arm 1), views and fields; the first field is primary.
    Model opponents play natively, so at six players copies of the live `widemix` fill a field;
    at three and four players no model holds the table's player count."""
    views = ['projected', 'projected']
    out = []
    for n, named in SHORT.items():
        rest = n - 1
        for name, stacks in named.items():
            fields = {'mixed': list(study.MIXED[n])}
            fields.update({s: [s] * rest for s in SCRIPT_FIELDS})
            if n == 6:
                fields['live-copies'] = ['widemix'] * rest
            out.append(dict(study='capacity', table=name, players=n, stack_bb=100, stacks_bb=list(stacks),
                            focals=['widemix', 'widecap'], views=views, fields=fields))
    return out


def verdict(table_study, lower, upper):
    if lower > 0:
        return '400M better'
    return '250M better' if upper < 0 else 'no difference shown'


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
    study.HARM_STUDIES = ('capacity',)
    study.FORMAT = 'openpoker-wide-capacity-v1'
    study.__doc__ = __doc__
    study.main()


if __name__ == '__main__':
    main()
