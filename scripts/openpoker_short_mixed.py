"""Mixed-stack models for 3, 4 and 5 players (docs/openpoker-short-mixed.md).

At each size N, a dedicated mixed-stack live-order 10B (`pNmix`) is compared with the route it
would replace. Home study, at 100 BB: `pNmix` minus #445's dedicated 100 BB `pN`. Depth study,
at 50, 20 and 200 BB and at an unequal table: `pNmix` minus #447's six-player `mix` through
phantom folds. Both focals use the projected view; every contrast is arm 1 minus arm 0, all-in
adjusted, over blocks. Collection, replay, scanning and the report reuse the phantom/depth
study's code with these tables and rules.
"""
from scripts import openpoker_phantom_depth as study

ROOT = 20261028200000
SIZES = (3, 4, 5)
DEPTHS_BB = (50, 20, 200)
UNEQUAL = {3: (150, 40, 100), 4: (65, 150, 100, 30), 5: (100, 50, 200, 30, 125)}


def tables():
    """Each table: its study, game, focals (arm 0, arm 1), views and fields; the first field is primary."""
    views = ['projected', 'projected']
    out = []
    for n in SIZES:
        rest, mixed = n - 1, f'p{n}mix'
        out.append(dict(study='home', table=f'{n}p-100bb', players=n, stack_bb=100, stacks_bb=None,
                        focals=[f'p{n}', mixed], views=views,
                        fields={'dedicated': [f'p{n}'] * rest, 'mixed': list(study.MIXED[n]),
                                'pot-pressure': ['pot-pressure'] * rest, 'mixed-copies': [mixed] * rest}))
        away = {'mixed': list(study.MIXED[n]), 'pot-pressure': ['pot-pressure'] * rest,
                'tight-aggressive': ['tight-aggressive'] * rest, 'mixed-copies': [mixed] * rest}
        for depth in DEPTHS_BB:
            out.append(dict(study='depth', table=f'{n}p-{depth}bb', players=n, stack_bb=100, stacks_bb=[depth] * n,
                            focals=['mix', mixed], views=views, fields=dict(away)))
        out.append(dict(study='depth', table=f'{n}p-unequal', players=n, stack_bb=100, stacks_bb=list(UNEQUAL[n]),
                        focals=['mix', mixed], views=views, fields=dict(away)))
    return out


def verdict(table_study, lower, upper):
    if table_study == 'home':
        if lower > -study.MARGIN:
            return 'mixed adequate at 100 BB'
        return 'mixed loses at 100 BB' if upper < -study.MARGIN else 'inconclusive'
    if lower > 0:
        return 'dedicated mixed better'
    return 'six-player mixed better' if upper < 0 else 'no difference shown'


def main():
    study.tables, study.verdict, study.ROOT = tables, verdict, ROOT
    study.FORMAT = 'openpoker-short-mixed-v1'
    study.__doc__ = __doc__
    study.main()


if __name__ == '__main__':
    main()
