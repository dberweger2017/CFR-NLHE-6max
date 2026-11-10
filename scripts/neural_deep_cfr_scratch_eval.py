"""Evaluations of the scratch Deep CFR run (docs/neural-deep-cfr-scratch.md).

Step 4's eight tables and fields, as in the warm-start pilot (scripts/neural_deep_cfr_eval.py): arm 0
plays network `start` everywhere and arm 1 network `dcfr`, the scratch strategy network. Every
contrast is arm 1 minus arm 0, all-in adjusted. `DCFR_SCRATCH_EVAL` picks the evaluation:

    monitor-N   a learning diagnostic at iteration N: `start` is step 2's net1; each table's primary
                field and one secondary field, 512 blocks, roots 20261110600000 + 100*N
    e1          final against net1 on the pilot's own roots (20261109500000), every field, 4,096 blocks
    e2          final against the pilot's strategy300-s4000, fresh roots 20261110500000, every field
    e3          run 2's final against run 1's final (docs/neural-deep-cfr-2m.md), roots 20261111500000
    e4          run 2's last checkpoint against run 1's at the same iteration, roots 20261111600000

The networks file names the arms' networks, so the modes differ only in `start` and the roots. In e3
and e4 `start` is run 1's network and `dcfr` run 2's, and the verdicts name the runs.
"""
import os

from scripts import neural_policy_everywhere as everywhere
from scripts import openpoker_phantom_depth as study

PILOT_ROOT = 20261109500000
WARM_ROOT = 20261110500000
MONITOR_ROOT = 20261110600000
EQUAL_TIME_ROOT = 20261111500000
EQUAL_ITERATION_ROOT = 20261111600000
ROOTS = {'e1': PILOT_ROOT, 'e2': WARM_ROOT, 'e3': EQUAL_TIME_ROOT, 'e4': EQUAL_ITERATION_ROOT}
# Monitoring keeps one secondary field per table: the report's harm family needs one, and these two
# are the ones the pilot's reading leaned on (passive play at the short tables, mixed at 100 BB).
MONITOR_SECONDARY = {'short': 'tight-aggressive', 'deep': 'mixed'}


def mode():
    m = os.environ.get('DCFR_SCRATCH_EVAL', '')
    if m in ROOTS or (m.startswith('monitor-') and m[8:].isdigit()):
        return m
    raise SystemExit('set DCFR_SCRATCH_EVAL to monitor-N, e1, e2, e3 or e4')


def tables():
    m = mode()
    out = []
    for t in everywhere.tables(1):
        fields = t['fields']
        if m.startswith('monitor-'):
            primary = next(iter(fields))
            second = MONITOR_SECONDARY[t['study']]
            fields = {primary: fields[primary], second: fields[second]}
        out.append(dict(t, study='scratch-short' if t['study'] == 'short' else 'scratch-deep', fields=fields,
                        fallback=['network-all:start', 'network-all:dcfr']))
    return out


def verdict(table_study, lower, upper):
    better, worse = ('run 2 better', 'run 1 better') if mode() in ('e3', 'e4') else ('scratch better', 'start better')
    if lower > 0:
        return better
    return worse if upper < 0 else 'no difference shown'


def configure():
    m = mode()
    study.tables, study.verdict = tables, verdict
    study.BANKS = 1
    if m in ROOTS:
        study.ROOT, study.BLOCKS = ROOTS[m], 4096
    else:
        study.ROOT, study.BLOCKS = MONITOR_ROOT + 100 * int(m[8:]), 512
    study.HARM_STUDIES = ('scratch-short', 'scratch-deep')
    study.FORMAT = f'neural-deep-cfr-scratch-eval-v1-{m}'
    study.__doc__ = __doc__


def main():
    configure()
    study.main()


if __name__ == '__main__':
    main()
