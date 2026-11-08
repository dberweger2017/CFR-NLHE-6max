"""The step-2 network at every focal decision (docs/neural-policy-everywhere.md).

Gate S: at #461's seven short tables, arm 0 is the live client (`widemix` through the projected
view with the `net1` fallback, #470) and arm 1 plays network k at every focal decision. At six
players `live-copies` are copies of that live client. Gate D: at a six-player 100 BB table, arm 0
is `six` (#431's live-order 10B) and arm 1 plays network k everywhere; the primary field is #434's
seed-2026102661001 live-order 10B. Every contrast is arm 1 minus arm 0, all-in adjusted, over
blocks. Collection, replay, scanning and the report reuse the phantom/depth study's code.

`--seed-run` picks the network: run 1 decides on four banks; runs 2 and 3 replicate on one bank
each, on their own roots. `decide` applies the protocol's gates to the three runs' results.
"""
import argparse
import json
import sys
from pathlib import Path

from scripts import nplayer_loss_diagnosis as diagnosis
from scripts import openpoker_phantom_depth as study
from scripts.openpoker_wide_stacks import SCRIPT_FIELDS, SHORT

ROOT = 20261109100000
MARGIN = 10.0
# Gate D's check-call is reported but not gating: #434 flagged it for live-order keys themselves.
EXEMPT = {'deep': ('check-call',)}


def tables(run):
    out = []
    for n, named in SHORT.items():
        for name, stacks in named.items():
            fields = {'mixed': list(study.MIXED[n])}
            fields.update({s: [s] * (n - 1) for s in SCRIPT_FIELDS})
            if n == 6:
                fields['live-copies'] = ['live:widemix:net1'] * (n - 1)
            out.append(dict(study='short', table=name, players=n, stack_bb=100, stacks_bb=list(stacks),
                            focals=['widemix', 'widemix'], views=['projected', 'projected'], fields=fields,
                            fallback=['network:net1', f'network-all:net{run}']))
    fields = {'trained': ['peer'] * 5}
    fields.update({s: [s] * 5 for s in SCRIPT_FIELDS})
    fields['mixed'] = list(study.MIXED[6])
    out.append(dict(study='deep', table='6p-100bb', players=6, stack_bb=100, stacks_bb=None,
                    focals=['six', 'six'], views=['native', 'native'], fields=fields,
                    fallback=['uniform', f'network-all:net{run}']))
    return out


def verdict(table_study, lower, upper):
    if table_study == 'deep':
        if lower > -MARGIN:
            return 'non-inferior'
        return 'inferior' if upper < -MARGIN else 'non-inferiority not shown'
    if lower > 0:
        return 'network better'
    return 'table better' if upper < 0 else 'no difference shown'


def harmed(entry, table_study):
    return [f for f, v in entry['fields'].items() if v.get('harm_flag') and f not in EXEMPT.get(table_study, ())]


def decide(results):
    """The protocol's gates from the three runs' `results.json`."""
    r1, r2, r3 = (json.loads(Path(p).read_text()) for p in results)
    primary = lambda r, t: r['tables'][t]['fields'][r['tables'][t]['primary']]
    point = lambda r, t: primary(r, t)['change']['adjusted']['mean_bb100']
    short = [t for t, e in r1['tables'].items() if e['study'] == 'short']
    rows = {}
    for t in short:
        v = primary(r1, t)['verdict']
        rows[t] = {'run1': point(r1, t), 'interval': primary(r1, t)['decision_interval'], 'verdict': v,
                   'run2': point(r2, t), 'run3': point(r3, t), 'harm': harmed(r1['tables'][t], 'short'),
                   'replicates': v == 'network better' and point(r2, t) > 0 and point(r3, t) > 0}
    gate_s = (all(r['verdict'] != 'table better' for r in rows.values()) and any(r['replicates'] for r in rows.values())
              and not any(r['harm'] for r in rows.values()))
    deep = next(t for t, e in r1['tables'].items() if e['study'] == 'deep')
    d = {'run1': point(r1, deep), 'interval': primary(r1, deep)['decision_interval'], 'verdict': primary(r1, deep)['verdict'],
         'run2': point(r2, deep), 'run3': point(r3, deep), 'harm': harmed(r1['tables'][deep], 'deep'),
         'check_call_harm_flag': bool(r1['tables'][deep]['fields']['check-call'].get('harm_flag'))}
    gate_d = d['verdict'] == 'non-inferior' and not d['harm'] and d['run2'] > -MARGIN and d['run3'] > -MARGIN
    return {'format': 'neural-policy-everywhere-decision-v1', 'gate_s': {'passed': gate_s, 'tables': rows},
            'gate_d': {'passed': gate_d, 'table': deep, **d}}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'decide':
        p = argparse.ArgumentParser()
        p.add_argument('decide')
        p.add_argument('--results', type=Path, nargs=3, required=True)
        p.add_argument('--out', type=Path, required=True)
        a = p.parse_args()
        decision = decide(a.results)
        diagnosis.create(a.out, json.dumps(decision, indent=1) + '\n')
        print(json.dumps({'gate_s': decision['gate_s']['passed'], 'gate_d': decision['gate_d']['passed']}))
        return
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
    study.HARM_STUDIES = ('short', 'deep')
    study.MARGIN = MARGIN
    study.FORMAT = 'neural-policy-everywhere-v1'
    study.__doc__ = __doc__
    study.main()


if __name__ == '__main__':
    main()
