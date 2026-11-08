"""The Deep CFR pilot's evaluation (docs/neural-deep-cfr.md): its strategy network against its
starting point, step 2's network, both playing every focal decision.

Step 4's eight tables and fields (scripts/neural_policy_everywhere.py): arm 0 plays network
`start` everywhere, arm 1 network `dcfr`. The focal models (`widemix`, `six`) only supply the rows
the traces record; no row is played. Every contrast is arm 1 minus arm 0, all-in adjusted. One bank
of 4,096 blocks per field on its own roots: a pilot read, not a gate.
"""
import sys

from scripts import neural_policy_everywhere as everywhere
from scripts import openpoker_phantom_depth as study

ROOT = 20261109500000


def tables():
    out = []
    for t in everywhere.tables(1):
        out.append(dict(t, study='pilot-short' if t['study'] == 'short' else 'pilot-deep',
                        fallback=['network-all:start', 'network-all:dcfr']))
    return out


def verdict(table_study, lower, upper):
    if lower > 0:
        return 'deep cfr better'
    return 'start better' if upper < 0 else 'no difference shown'


def main():
    study.tables, study.verdict = tables, verdict
    study.ROOT, study.BANKS = ROOT, 1
    study.HARM_STUDIES = ('pilot-short', 'pilot-deep')
    study.FORMAT = 'neural-deep-cfr-pilot-eval-v1'
    study.__doc__ = __doc__
    study.main()


if __name__ == '__main__':
    main()
