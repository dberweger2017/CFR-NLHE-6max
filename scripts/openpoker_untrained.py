"""Restricted fallbacks at untrained rows for Open Poker tables (docs/openpoker-untrained-fallback.md).

#447's mixed-stack six-player 10B (`mix`) plays the same deals in both arms. Arm 0 keeps the
uniform fallback at decisions without a positive-mass row; arm 1 plays one candidate there:
`no-all-in` (uniform over the menu without a raise to the whole stack) or `no-raise` (uniform
over check/fold and call). Both arms use the projected view. Every contrast is the candidate
minus uniform, all-in adjusted, over blocks. Collection, replay, scanning and the report reuse
the phantom/depth study's code with these tables and rules.
"""
from scripts import openpoker_phantom_depth as study

ROOT = 20261028100000
CANDIDATES = ('no-all-in', 'no-raise')
TABLES = {'100bb': [100] * 6, '50bb': [50] * 6, 'unequal': [100, 50, 150, 80, 100, 200],
          # Like the first live table: one opponent far deeper than the trained grid.
          'deep-outlier': [100, 2000, 100, 125, 150, 80]}
SCRIPT_FIELDS = ('pot-pressure', 'tight-aggressive', 'check-call', 'random')


def tables():
    """Each table: its study (the candidate), game, focals, views, fallbacks and fields; the first field is primary.
    `mix` copies play natively, so they sit only where every stack is on the trained grid."""
    out = []
    for c in CANDIDATES:
        for name, stacks in TABLES.items():
            fields = {'mixed': list(study.MIXED[6])}
            if name != 'deep-outlier':
                fields['mix'] = ['mix'] * 5
            fields.update({s: [s] * 5 for s in SCRIPT_FIELDS})
            out.append(dict(study=c, table=f'{name}-{c}', players=6, stack_bb=100, stacks_bb=stacks, focals=['mix', 'mix'],
                            views=['projected', 'projected'], fallback=['uniform', c], fields=fields))
    return out


def verdict(table_study, lower, upper):
    if lower > 0:
        return 'candidate better'
    return 'uniform better' if upper < 0 else 'no difference shown'


def main():
    study.tables, study.verdict, study.ROOT = tables, verdict, ROOT
    study.HARM_STUDIES = CANDIDATES
    study.FORMAT = 'openpoker-untrained-fallback-v1'
    study.__doc__ = __doc__
    study.main()


if __name__ == '__main__':
    main()
