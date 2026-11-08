"""The network as the live widemix's fallback at untrained rows (docs/neural-policy-fallback.md).

Arm 0 is the live `widemix` with uniform fallback; arm 1 is the same `widemix` playing a step-2
network's strategy at exactly the focal decisions without a positive-mass row. Both see #461's seven
short tables through the projected view, with #461's fields. Every contrast is arm 1 minus arm 0,
all-in adjusted, over blocks. Collection, replay, scanning and the report reuse the phantom/depth
study's code with these tables and rules.

`--seed-run` picks the network: run 1 (network seed 1) decides on four banks; runs 2 and 3
(network seeds 2 and 3) replicate on one bank each and on their own roots.
"""
import sys

from scripts import openpoker_phantom_depth as study
from scripts.openpoker_wide_stacks import SCRIPT_FIELDS, SHORT

ROOT = 20261108700000


def tables(run):
    views = ['projected', 'projected']
    out = []
    for n, named in SHORT.items():
        for name, stacks in named.items():
            fields = {'mixed': list(study.MIXED[n])}
            fields.update({s: [s] * (n - 1) for s in SCRIPT_FIELDS})
            if n == 6:
                fields['live-copies'] = ['widemix'] * (n - 1)
            out.append(dict(study='fallback', table=name, players=n, stack_bb=100, stacks_bb=list(stacks),
                            focals=['widemix', 'widemix'], views=views, fields=fields,
                            fallback=['uniform', f'network:net{run}']))
    return out


def verdict(table_study, lower, upper):
    if lower > 0:
        return 'network better'
    return 'uniform better' if upper < 0 else 'no difference shown'


def main():
    run = 1
    if '--seed-run' in sys.argv:
        i = sys.argv.index('--seed-run')
        run = int(sys.argv[i + 1])
        del sys.argv[i:i + 2]
    if run not in (1, 2, 3):
        raise ValueError('--seed-run is 1, 2 or 3')
    study.tables, study.verdict = (lambda: tables(run)), verdict
    study.ROOT = ROOT + 100_000 * (run - 1)
    study.BANKS = 4 if run == 1 else 1
    study.HARM_STUDIES = ('fallback',)
    study.FORMAT = 'neural-policy-fallback-v1'
    study.__doc__ = __doc__
    study.main()


if __name__ == '__main__':
    main()
