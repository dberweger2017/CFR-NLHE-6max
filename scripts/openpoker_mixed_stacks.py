"""Mixed-stack training for Open Poker tables (docs/openpoker-mixed-stacks.md).

#431's six-player live-order 10B, trained at 100 BB only, and a six-player live-order 10B
trained with every seat's depth drawn from 10–250 BB play the same deals, both through the
projected view. Tables: 100 BB (the fixed model's home), 50, 20 and 200 BB, two unequal
six-seat tables and an unequal four-seat table. Every contrast is mixed minus fixed (arm 1
minus arm 0), all-in adjusted, over blocks. Collection, replay, scanning and the report reuse
the phantom/depth study's code with these tables and rules.
"""
from scripts import openpoker_phantom_depth as study

ROOT = 20261027600000
UNEQUAL = {'unequal-a': (100, 50, 150, 80, 100, 200), 'unequal-b': (250, 30, 100, 15, 200, 65)}
UNEQUAL_4P = (200, 50, 100, 30)


def tables():
    """Each table: its study, game, focals (arm 0, arm 1), views and fields; the first field is primary."""
    scripts = study.SCRIPTS
    views = ['projected', 'projected']

    def six(primary, players=6):
        fields = dict(primary)
        fields.update({s: [s] * (players - 1) for s in scripts})
        fields['mixed'] = list(study.MIXED[players])
        return fields

    out = [dict(study='home', table='100bb', players=6, stack_bb=100, stacks_bb=None, focals=['six', 'mix'], views=views,
                fields=six({'trained': ['six'] * 5, 'mix': ['mix'] * 5})),
           dict(study='depth', table='50bb', players=6, stack_bb=50, stacks_bb=None, focals=['six', 'mix'], views=views,
                fields=six({'trained': ['six50'] * 5, 'mix': ['mix'] * 5}))]
    for depth in (20, 200):
        out.append(dict(study='depth', table=f'{depth}bb', players=6, stack_bb=depth, stacks_bb=None, focals=['six', 'mix'],
                        views=views, fields=six({'mixed': list(study.MIXED[6]), 'mix': ['mix'] * 5})))
    for name, stacks in UNEQUAL.items():
        out.append(dict(study='depth', table=name, players=6, stack_bb=100, stacks_bb=list(stacks), focals=['six', 'mix'],
                        views=views, fields=six({'mixed': list(study.MIXED[6]), 'mix': ['mix'] * 5})))
    out.append(dict(study='depth', table='unequal-4p', players=4, stack_bb=100, stacks_bb=list(UNEQUAL_4P),
                    focals=['six', 'mix'], views=views, fields=six({'mixed': list(study.MIXED[4])}, players=4)))
    return out


def verdict(table_study, lower, upper):
    if table_study == 'home':
        if lower > -study.MARGIN:
            return 'mixed adequate at 100 BB'
        return 'mixed loses at 100 BB' if upper < -study.MARGIN else 'inconclusive'
    if lower > 0:
        return 'mixed better'
    return 'fixed better' if upper < 0 else 'no difference shown'


def main():
    study.tables, study.verdict, study.ROOT = tables, verdict, ROOT
    study.FORMAT = 'openpoker-mixed-stacks-v1'
    study.__doc__ = __doc__
    study.main()


if __name__ == '__main__':
    main()
