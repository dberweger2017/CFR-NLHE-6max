"""Heads-up routes for Open Poker tables (docs/openpoker-heads-up.md).

A two-player live-order 10B trained at 100 BB (`hu100`) and one trained with both seats'
depths drawn from the 10–250 BB grid (`humix`) play the same deals, both through the
projected view: at 100 BB (the fixed model's home), 50, 20 and 200 BB and two unequal tables.
Every contrast is `humix` minus `hu100` (arm 1 minus arm 0), all-in adjusted, over blocks.
Collection, replay, scanning and the report reuse the phantom/depth study's code with these
tables and rules.
"""
from scripts import openpoker_mixed_stacks as mixed
from scripts import openpoker_phantom_depth as study

ROOT = 20261027800000
UNEQUAL = {'unequal-a': (150, 40), 'unequal-b': (250, 100)}
SCRIPT_FIELDS = ('pot-pressure', 'tight-aggressive', 'check-call', 'random')


def tables():
    """Each table: its study, game, focals (arm 0, arm 1), views and fields; the first field is primary."""
    views = ['projected', 'projected']

    def fields(trained, *other):
        out = {'trained': [trained]}
        out.update({o: [o] for o in other + SCRIPT_FIELDS})
        return out

    out = [dict(study='home', table='100bb', players=2, stack_bb=100, stacks_bb=None, focals=['hu100', 'humix'],
                views=views, fields=fields('hu100', 'humix'))]
    for depth in (50, 20, 200):
        out.append(dict(study='depth', table=f'{depth}bb', players=2, stack_bb=100, stacks_bb=[depth, depth],
                        focals=['hu100', 'humix'], views=views, fields=fields('humix')))
    for name, stacks in UNEQUAL.items():
        out.append(dict(study='depth', table=name, players=2, stack_bb=100, stacks_bb=list(stacks),
                        focals=['hu100', 'humix'], views=views, fields=fields('humix')))
    return out


def main():
    study.tables, study.verdict, study.ROOT = tables, mixed.verdict, ROOT
    study.FORMAT = 'openpoker-heads-up-v1'
    study.__doc__ = __doc__
    study.main()


if __name__ == '__main__':
    main()
