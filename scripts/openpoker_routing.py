"""Depth band and short-handed routes for Open Poker tables (docs/openpoker-routing.md).

Band study: #431's six-player 100 BB live-order 10B (`six`) and #447's mixed-stack six-player
10B (`mix`) play the same deals at 65, 80, 125 and 150 BB and at an unequal table near 100 BB.
Short study: at 3, 4 and 5 players, #445's dedicated 100 BB `pN` and `mix` through phantom
folds play the same deals at 100 BB, at 50 BB and at an unequal table. Both focals use the
projected view; every contrast is `mix` minus the fixed model (arm 1 minus arm 0), all-in
adjusted, over blocks. Collection, replay, scanning and the report reuse the phantom/depth
study's code with these tables and rules.
"""
from scripts import openpoker_phantom_depth as study

ROOT = 20261027700000
BAND_BB = (65, 80, 125, 150)
NEAR_100 = (80, 100, 125, 100, 80, 125)
SHORT_UNEQUAL = {3: (150, 40, 100), 4: (65, 150, 100, 30), 5: (100, 50, 200, 30, 125)}


def tables():
    """Each table: its study, game, focals (arm 0, arm 1), views and fields; the first field is primary."""
    views = ['projected', 'projected']
    out = []
    six_fields = {'mixed': list(study.MIXED[6]), 'mix': ['mix'] * 5, 'pot-pressure': ['pot-pressure'] * 5,
                  'tight-aggressive': ['tight-aggressive'] * 5}
    for depth in BAND_BB:
        out.append(dict(study='band', table=f'{depth}bb', players=6, stack_bb=100, stacks_bb=[depth] * 6,
                        focals=['six', 'mix'], views=views, fields=dict(six_fields)))
    out.append(dict(study='band', table='near-100', players=6, stack_bb=100, stacks_bb=list(NEAR_100),
                    focals=['six', 'mix'], views=views, fields=dict(six_fields)))
    for n in (3, 4, 5):
        rest = n - 1
        home = {'dedicated': [f'p{n}'] * rest, 'mixed': list(study.MIXED[n]), 'pot-pressure': ['pot-pressure'] * rest}
        away = {'mixed': list(study.MIXED[n]), 'pot-pressure': ['pot-pressure'] * rest,
                'tight-aggressive': ['tight-aggressive'] * rest}
        for table, stacks, fields in ((f'{n}p-100bb', None, home), (f'{n}p-50bb', [50] * n, away),
                                      (f'{n}p-unequal', list(SHORT_UNEQUAL[n]), dict(away))):
            out.append(dict(study='short', table=table, players=n, stack_bb=100, stacks_bb=stacks,
                            focals=[f'p{n}', 'mix'], views=views, fields=fields))
    return out


def verdict(table_study, lower, upper):
    if lower > 0:
        return 'mixed better'
    return 'fixed better' if upper < 0 else 'no difference shown'


def main():
    study.tables, study.verdict, study.ROOT = tables, verdict, ROOT
    study.FORMAT = 'openpoker-routing-v1'
    study.__doc__ = __doc__
    study.main()


if __name__ == '__main__':
    main()
