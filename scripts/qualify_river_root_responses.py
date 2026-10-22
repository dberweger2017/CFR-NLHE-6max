"""Fixed development comparison: retain the opponent's minimum raise after a root bet.

Baseline `pot-jam-cap3-root-check-min-v1` against `pot-jam-cap3-root-min-responses-v1`,
which differs only by that response. Both arms are solved fresh on PR380's
frozen 200-root development panel with projected beliefs (deployment and
strict targets) and exact beliefs (deployment target), then audited in the
full-menu game under the exact modeled law. A response diagnosis checks
whether the remaining exposure moves. No arena, training or adaptive arms.
"""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from time import monotonic

from scripts.qualify_river_continuation import SHA, write, stable, solve_request, sha
from scripts.qualify_river_exact import inputs, original_identity, PREFIX, PANEL_SHA
from scripts.river_search_panel import Worker
from scripts.river_search_round2_compare import describe
from scripts.river_search_stage2 import Pool
from scripts.summarize_river_exact import compact, arm, paired

MENUS = ('pot-jam-cap3-root-check-min-v1', 'pot-jam-cap3-root-min-responses-v1')
PROJECTED = 'projected-product-v1'
PHASES = ('projected', 'exact', 'strict')
CALIBRATION_CASES = (0, 53, 79, 113)
LAW = 'exact_modeled'


def ask(worker, request):
    tick = monotonic()
    response = worker.ask(request)
    response['roundtrip_seconds'] = monotonic() - tick
    if response['status'] != 'ok':
        raise RuntimeError('valid development request refused: ' + str(response)[:400])
    return response


def request_for(case, phase, menu):
    request = solve_request(case, 'strict' if phase == 'strict' else 'deployment', menu)
    # Quality is judged by the exact full-menu audit, not the projected omitted evaluation.
    request['omitted'] = False
    if phase == 'exact':
        request['belief_backend'] = PREFIX
    return request


def session(worker, case, phase, menu, old=None, diagnose=False):
    begin = ask(worker, {'mode': 'retained-begin', 'hand_id': f"{case['panel']}/{case['hand']}",
                         'observation': request_for(case, phase, menu)})
    if old is not None:
        # The baseline arm must reproduce PR380's original deployment output exactly.
        original_identity(begin, old)
    s = begin['result']['session']
    context = {'hand_id': s['hand_id'], 'handle': s['handle']}
    row = {'menu': menu, 'backend': PREFIX if phase == 'exact' else PROJECTED,
           'original_projected_identity': old is not None, 'begin': begin}
    if diagnose:
        row['diagnosis'] = ask(worker, {'mode': 'retained-harm-diagnosis', **context})
        if row['diagnosis']['result']['solver_advances'] != 0:
            raise RuntimeError('diagnosis advanced the solver')
    else:
        row['continuation'] = ask(worker, {'mode': 'retained-audit', **context})
        row['audit'] = ask(worker, {'mode': 'retained-full-menu-audit', **context})
        if (row['audit']['result']['profile_sha256'] != s['binding']['profile_sha256']
                or row['audit']['result']['solver_advances'] != 0
                or row['continuation']['result']['solver_advances'] != 0):
            raise RuntimeError('audit profile identity or zero-advance proof differs')
    row['release'] = ask(worker, {'mode': 'retained-release', **context})
    return row


def jobs(phase, indices):
    # Alternate arm order by case so neither arm always runs first on a worker.
    return [(i, m) for i in indices for m in (MENUS if i % 2 == 0 else MENUS[::-1])]


def run_phase(args, cases, old, phase, work, out, workers):
    out.mkdir(parents=True, exist_ok=False)
    pool = Pool(workers, args)
    write(out / 'startup.json', [w.ready for w in list(pool.workers.queue)])

    def one(job):
        i, menu = job
        worker = pool.workers.get()
        try:
            baseline = old.get((i, menu)) if phase == 'projected' and menu == MENUS[0] else None
            row = session(worker, cases[i], 'projected' if phase == 'diagnosis' else phase, menu,
                          baseline, diagnose=phase == 'diagnosis')
            return {'case_index': i, 'phase': phase, **row}
        finally:
            pool.workers.put(worker)

    try:
        with (out / 'records.jsonl').open('x') as stream, ThreadPoolExecutor(pool.size) as executor:
            for count, row in enumerate(executor.map(one, work), 1):
                stream.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')
                stream.flush()
                write(out / 'progress.json', {'phase': phase, 'completed': count, 'total': len(work)})
    finally:
        pool.close()


def rows(path):
    return [json.loads(s) for s in Path(path).read_text().splitlines()]


def harm_cases(projected_records):
    """Frozen diagnosis rule: every root that is worse than the blueprint in either arm."""
    harmed = set()
    for row in projected_records:
        actual = compact(row)['laws'][LAW]['actual']
        if actual['hero_worst_case_change_bb'] < -1e-8:
            harmed.add(row['case_index'])
    return sorted(harmed)


def measure(args):
    cases, _, old = inputs(args.inputs)
    calibration = args.command == 'calibrate'
    indices = CALIBRATION_CASES if calibration else range(200)
    workers = 1 if calibration else 5
    if args.phase == 'diagnosis':
        source = args.out.parent / 'projected' / 'records.jsonl'
        selected = harm_cases(rows(source))
        if calibration:
            selected = list(CALIBRATION_CASES)
        work = jobs('diagnosis', selected)
    else:
        work = jobs(args.phase, indices)
    run_phase(args, cases, old, args.phase, work, args.out, workers)


def verify(args):
    args.out.mkdir(parents=True, exist_ok=False)
    proof = {}
    for phase in (*PHASES, 'diagnosis'):
        a = args.inputs / 'initial' / phase / 'records.jsonl'
        b = args.inputs / 'repeat' / phase / 'records.jsonl'
        first, second = rows(a), rows(b)
        if len(first) != len(second) or stable(first) != stable(second):
            raise RuntimeError('strategic reproduction differs: ' + phase)
        if phase != 'diagnosis' and [(r['case_index'], r['menu']) for r in first] != jobs(phase, range(200)):
            raise RuntimeError('panel work identities differ: ' + phase)
        proof[phase] = {'records': len(first), 'initial_sha256': sha(a), 'repeat_sha256': sha(b)}
    write(args.out / 'verified.json', {'status': 'passed', 'counts': proof,
          'excluded': 'timing counters and opaque process-local handles only; no strategic fields'})


def quote(args):
    """From calibration records: two complete passes at five workers, plus loads and reserve."""
    args.out.mkdir(parents=True, exist_ok=False)
    per_job, startup = {}, []
    for phase in (*PHASES, 'diagnosis'):
        records = rows(args.inputs / phase / 'records.jsonl')
        keys = ('begin', 'diagnosis', 'release') if phase == 'diagnosis' else ('begin', 'continuation', 'audit', 'release')
        per_job[phase] = [sum(r[k]['roundtrip_seconds'] for k in keys) for r in records]
        startup += [s['model_and_k50_load_seconds'] for s in json.loads((args.inputs / phase / 'startup.json').read_text())]
    mean = lambda v: sum(v) / len(v)
    # Diagnosis count is unknown before the main run; quote the union of harms at
    # its PR382 level (about 60 roots, both arms) and say so.
    work = 2 * (sum(400 * mean(per_job[p]) for p in PHASES) + 120 * mean(per_job['diagnosis'])) / 5
    loads = 2 * 4 * max(startup)
    lower, upper = work + loads, 1.5 * work + 2 * loads
    write(args.out / 'quote.json', {'status': 'quoted', 'panel_sha256': PANEL_SHA, 'per_job_seconds': per_job,
          'observed_startup_seconds': startup, 'lower_seconds': lower, 'upper_seconds': upper,
          'auto_launch_limit_seconds': AUTO_LAUNCH_LIMIT, 'auto_launch': upper <= AUTO_LAUNCH_LIMIT,
          'scope': 'two passes; five workers per phase; diagnosis assumed about 120 jobs; builds/tests separate',
          'no_science_started': True})
    print(json.dumps({'lower_minutes': lower / 60, 'upper_minutes': upper / 60, 'auto_launch': upper <= AUTO_LAUNCH_LIMIT}))


# Owner approval: the main run starts automatically only within the stated
# estimate (1.5-2 h, with reserve).
AUTO_LAUNCH_LIMIT = 2.5 * 3600


def response_type(r):
    depth = len(r['path'])
    first = r['path'][0][0] if r['path'] else 'root'
    kind = {3: 'minimum', 4: 'pot', 5: 'all-in'}.get(r['label'], f"label-{r['label']}")
    return f"depth {depth} after {first}, {kind} {r['action'][0]}{' facing a bet' if r['facing_bet'] else ''}"


def diagnosis_summary(records):
    out = {}
    for menu in MENUS:
        by_type = defaultdict(lambda: {'leave_one_out_wc_improvement_bb': 0.0, 'cases': 0})
        top = []
        for row in [r for r in records if r['menu'] == menu]:
            actual = row['diagnosis']['result']['actual']
            omitted = [r for r in actual['responses'] if r['omitted']]
            if not omitted:
                continue
            best = max(omitted, key=lambda r: r['leave_one_out_wc_improvement_bb'])
            top.append({'case_index': row['case_index'], 'type': response_type(best),
                        'path': best['path'], 'action': best['action'],
                        'leave_one_out_wc_improvement_bb': best['leave_one_out_wc_improvement_bb']})
            for r in omitted:
                t = by_type[response_type(r)]
                t['leave_one_out_wc_improvement_bb'] += max(r['leave_one_out_wc_improvement_bb'], 0.0)
            for kind in {response_type(r) for r in omitted}:
                by_type[kind]['cases'] += 1
        ranking = sorted(({'type': k, **v} for k, v in by_type.items()),
                         key=lambda v: -v['leave_one_out_wc_improvement_bb'])
        counts = defaultdict(int)
        for t in top:
            counts[t['type']] += 1
        out[menu] = {'cases': len(top), 'top_response_type_counts': dict(counts), 'ranking': ranking[:10],
                     'per_case_top': top,
                     'scope': 'overlapping leave-one-out restrictions of fixed profiles; not additive'}
    return out


def readout(args):
    root = args.inputs
    if json.loads((root / 'verification/verified.json').read_text())['status'] != 'passed':
        raise ValueError('verified reproduction required')
    data = {phase: [compact(r) for r in rows(root / 'initial' / phase / 'records.jsonl')] for phase in PHASES}
    split = lambda rs, menu: sorted((r for r in rs if r['menu'] == menu), key=lambda r: r['case_index'])
    arms = {f'{phase}/{menu}': arm(split(data[phase], menu)) for phase in PHASES for menu in MENUS}
    comparisons = {}
    for phase in PHASES:
        base, new = split(data[phase], MENUS[0]), split(data[phase], MENUS[1])
        if phase == 'strict':
            # Matched accuracy: only pairs both arms solved to the strict target.
            keep = {r['case_index'] for r in base if r['installed']} & {r['case_index'] for r in new if r['installed']}
            comparisons['strict/inconclusive_pairs'] = 200 - len(keep)
            base = [r for r in base if r['case_index'] in keep]
            new = [r for r in new if r['case_index'] in keep]
        comparisons[f'{phase}/new_vs_baseline'] = paired(base, new, LAW)
    for menu in MENUS:
        comparisons[f'exact_vs_projected/{menu}'] = paired(split(data['projected'], menu), split(data['exact'], menu), LAW)
    key = f'projected/{MENUS[1]}'
    base_harms = arms[f'projected/{MENUS[0]}']['laws'][LAW]['worse_than_blueprint']
    new_harms = arms[key]['laws'][LAW]['worse_than_blueprint']
    median_change = comparisons['projected/new_vs_baseline']['hero_worst_case_change_bb']['median']
    rule = {'fewer_harms_than_baseline': new_harms < base_harms,
            'positive_median_paired_worst_case_change': median_change > 0,
            'latency_gate': arms[key]['latency_gate']}
    decision = 'retain' if all(rule.values()) else 'revise-or-reject'
    summary = {'format': 'river-root-min-responses-v1', 'panel_sha256': PANEL_SHA, 'menus': MENUS, 'law': LAW,
               'arms': arms, 'comparisons': comparisons,
               'diagnosis': diagnosis_summary(rows(root / 'initial' / 'diagnosis' / 'records.jsonl')),
               'decision_rule': rule, 'decision': decision}
    args.out.mkdir(parents=True, exist_ok=False)
    write(args.out / 'summary.json', summary)
    print(json.dumps({'decision': decision, 'rule': rule, 'harms': [base_harms, new_harms],
                      'median_worst_case_change_bb': median_change}, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['calibrate', 'measure', 'verify', 'quote', 'readout'])
    for name in ('inputs', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    for name in ('binary', 'k50', 'model'):
        p.add_argument('--' + name, type=Path)
    p.add_argument('--phase', choices=[*PHASES, 'diagnosis'])
    args = p.parse_args()
    args.sha256 = SHA
    if args.out.exists():
        p.error('fresh output required; no automatic retry')
    try:
        if args.command in ('calibrate', 'measure'):
            measure(args)
        else:
            globals()[args.command](args)
    except BaseException as error:
        if args.out.exists():
            write(args.out / 'failure.json', {'error': str(error)})
        raise


if __name__ == '__main__':
    main()
