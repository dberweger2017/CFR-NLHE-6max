"""Six-player loss diagnosis: where the chips go, all-in luck and the fallback replay.

`scan` streams saved paired-arena traces, verifies each file's recorded SHA256,
and writes one compact record per hand plus every showdown for the exact
all-in tool. `equity` runs `nplayer_allin_equity` on those showdowns.
`fallback-manifest` builds the part B replay. `report` reproduces every
published mean, then writes the partitions, luck, style and fallback tables.
See docs/nplayer-six-player-loss-diagnosis.md.
"""
import argparse
import csv
import hashlib
import json
import math
import statistics
import subprocess
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

from scripts import nplayer_paired_evidence as evidence

STREETS = ('preflop', 'flop', 'turn', 'river')
POSITIONS = {4: ('BTN', 'SB', 'BB', 'UTG'), 5: ('BTN', 'SB', 'BB', 'UTG', 'CO'),
             6: ('BTN', 'SB', 'BB', 'UTG', 'HJ', 'CO')}
UNTRAINED = ('missing', 'zero_mass')
HAND_COLUMNS = ('hand', 'block', 'seat', 'position', 'preflop_line', 'ending', 'showdown_result',
                'untrained_first', 'untrained_decisions', 'replaced', 'reward', 'showdown', 'locked')
DIMENSIONS = ('position', 'preflop_line', 'ending', 'showdown_result', 'untrained_first')


def create(path, text):
    """Write a new file; never overwrite evidence."""
    with Path(path).open('x') as f:
        f.write(text)


def t_quantile(p, df):
    """Student-t quantile by bisection on the regularized incomplete beta."""
    def betacf(a, b, x):
        qab, qap, qam = a + b, a + 1, a - 1
        c, d = 1.0, 1 - qab * x / qap
        d = 1 / d
        h = d
        for m in range(1, 400):
            m2 = 2 * m
            aa = m * (b - m) * x / ((qam + m2) * (a + m2))
            d, c = 1 / (1 + aa * d), 1 + aa / c
            h *= d * c
            aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
            d, c = 1 / (1 + aa * d), 1 + aa / c
            h *= d * c
            if abs(d * c - 1) < 1e-16:
                break
        return h

    def upper_tail(t):
        x = df / (df + t * t)
        a, b = df / 2, 0.5
        front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
        if x < (a + 1) / (a + b + 2):
            return 0.5 * front * betacf(a, b, x) / a
        return 0.5 * (1 - front * betacf(b, a, 1 - x) / b)

    lo, hi = 0.0, 100.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if 1 - upper_tail(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def interval(values):
    mean = statistics.fmean(values)
    error = statistics.stdev(values) / math.sqrt(len(values))
    width = t_quantile(0.975, len(values) - 1) * error
    return {'mean_bb100': mean, 'standard_error_bb100': error, 'lower95_bb100': mean - width, 'upper95_bb100': mean + width}


def cochran(estimates):
    """Cochran's Q for three independent estimates; the chi-square tail with df = 2 is exp(-Q/2)."""
    weights = [1 / e['standard_error_bb100'] ** 2 for e in estimates]
    pooled = sum(w * e['mean_bb100'] for w, e in zip(weights, estimates)) / sum(weights)
    q = sum(w * (e['mean_bb100'] - pooled) ** 2 for w, e in zip(weights, estimates))
    if len(estimates) != 3:
        raise ValueError('three banks expected')
    return {'q': q, 'df': 2, 'p': math.exp(-q / 2), 'i2': max(0.0, (q - 2) / q) if q > 0 else 0.0}


def action_class(action, state):
    kind, raise_to = action
    if kind != 'raise':
        return kind
    stack, street_bet = state['players'][state['actor']][:2]
    if raise_to == stack + street_bet:
        return 'all-in'
    return 'min-raise' if raise_to == state['legal']['raise_to'][0] else 'raise'


def style_counts(row, seat, showdown, counts):
    """Standard frequencies for one seat in one hand; opportunities and events are separate keys."""
    counts['hands'] += 1
    raises = vpip = pfr = opened = 0
    threebet_seen = fold3_seen = folded_pre = False
    for actor, action, state in zip(row['actors'], row['actions'], row['states']):
        kind = action[0]
        if state['street'] == 'preflop':
            if actor == seat:
                if raises == 1 and not pfr and not threebet_seen:
                    threebet_seen = True
                    counts['threebet_opportunities'] += 1
                    counts['threebets'] += kind == 'raise'
                if opened and raises >= 2 and not fold3_seen:
                    fold3_seen = True
                    counts['fold_to_threebet_opportunities'] += 1
                    counts['folds_to_threebet'] += kind == 'fold'
                if kind in ('call', 'raise'):
                    vpip = 1
                if kind == 'raise':
                    opened = opened or raises == 0
                    pfr = 1
                folded_pre = folded_pre or kind == 'fold'
            raises += kind == 'raise'
        elif actor == seat:
            street = state['street']
            cls = action_class(action, state)
            counts[f'{street}_decisions'] += 1
            counts[f'{street}_aggressive'] += kind == 'raise'
            if state['legal']['call'] > 0:
                counts[f'{street}_facing_bet'] += 1
                counts[f'{street}_fold_to_bet'] += kind == 'fold'
            counts['postflop_all_in'] += cls == 'all-in'
        if actor == seat:
            counts['decisions'] += 1
            counts['all_in'] += action_class(action, state) == 'all-in'
    counts['vpip'] += vpip
    counts['pfr'] += pfr
    final = row['states'][-1]
    if not folded_pre and len(final['board']) >= 3:
        counts['saw_flop'] += 1
        if showdown and not final['players'][seat][3]:
            counts['went_to_showdown'] += 1
            counts['won_at_showdown'] += row['rewards'][seat] > 0


def classify(row, n):
    """One focal hand: categories, untrained exposure, decision counters and showdown request."""
    seat = row['identities'].index(0)
    actions, states, lookups = row['actions'], row['states'], row['lookups']
    final = states[-1]
    live = [i for i in range(n) if not final['players'][i][3]]
    last = len(actions) - 1
    showdown = len(live) > 1
    locked = showdown and len(states[last]['board']) < 5
    raises = invested = 0
    focal_raises = []
    folded_on = fold_raises = fold_invested = None
    untrained_first, untrained, replaced = 'none', 0, 0
    decisions = []
    paid = [e[4] for e in row['history'] if e[1] != 'board']
    if len(paid) != len(actions):
        raise ValueError('history/action alignment')
    for i, (actor, action, state, lookup) in enumerate(zip(row['actors'], actions, states, lookups)):
        kind = action[0]
        if actor == seat:
            status = lookup['status']
            if status in UNTRAINED:
                untrained += 1
                if untrained_first == 'none':
                    untrained_first = state['street']
            replaced += 'fallback_replaced' in lookup
            facing = 'facing' if state['legal']['call'] > 0 else 'unopened'
            decisions.append((state['street'], status, action_class(action, state), facing, paid[i]))
            if state['street'] == 'preflop':
                if kind == 'fold':
                    folded_on, fold_raises, fold_invested = 'preflop', raises, invested
                elif kind in ('call', 'raise'):
                    invested = 1
                if kind == 'raise':
                    focal_raises.append(raises)
            elif kind == 'fold':
                folded_on = state['street']
        if state['street'] == 'preflop' and kind == 'raise':
            raises += 1
    if folded_on == 'preflop':
        line = 'fold after investing' if fold_invested else ('fold unopened' if fold_raises == 0 else 'fold to a raise')
    elif raises == 0:
        line = 'limped or checked pot'
    else:
        size = 'single-raised' if raises == 1 else '3-bet+'
        last_raiser = max((i for i, (a, act, s) in enumerate(zip(row['actors'], actions, states))
                           if s['street'] == 'preflop' and act[0] == 'raise'))
        line = f"{size}, {'raiser' if row['actors'][last_raiser] == seat else 'caller'}"
    if folded_on:
        ending = f'folded {folded_on}'
    elif not showdown:
        ending = f"won uncontested {states[last]['street']}"
    else:
        ending = 'all-in showdown before river' if locked else 'river showdown'
    reward = row['rewards'][seat]
    result = 'none' if folded_on or not showdown else ('won' if reward > 0 else 'lost' if reward < 0 else 'split')
    record = {'hand': row['hand'], 'block': row['block'], 'seat': seat, 'position': POSITIONS[n][(seat - row['button']) % n],
              'preflop_line': line, 'ending': ending, 'showdown_result': result, 'untrained_first': untrained_first,
              'untrained_decisions': untrained, 'replaced': replaced, 'reward': reward, 'showdown': int(showdown),
              'locked': int(locked)}
    request = None
    if showdown:
        realized = row['deck'][2 * n:2 * n + 5]
        if final['board'] != realized:
            raise ValueError('showdown board differs from the deck')
        s = row['settlement']
        request = {'id': row['hand'], 'button': row['button'], 'holes': states[0]['holes'], 'board': states[last]['board'],
                   'realized': realized, 'pots': s['pots'], 'refunds': s['refunds'], 'contributions': s['contributions'],
                   'rewards': row['rewards']}
    return seat, record, decisions, request, showdown


def fallback_violations(row, seat, mode):
    """Decisions that break the declared fallback: check-fold plays only check, else fold, at untrained rows."""
    bad = 0
    for actor, action, state, lookup in zip(row['actors'], row['actions'], row['states'], row['lookups']):
        replaced = 'fallback_replaced' in lookup
        if actor != seat or mode == 'uniform' or lookup['status'] not in UNTRAINED:
            bad += replaced
        else:
            bad += action != (['check', 0] if state['legal']['check'] else ['fold', 0])
    return bad


def expected_sha(spec, field, path):
    if 'cost' in spec:
        return json.loads(Path(spec['cost'].format(field=field)).read_text())['trace_sha256'][spec['arm']]
    files = json.loads(Path(spec['archive']).read_text())['files']
    matches = [f['sha256'] for f in files if f['destination'] == str(path)]
    if len(matches) != 1:
        raise ValueError(f'{path}: not in the archive manifest')
    return matches[0]


def compared(row, reference):
    keys = ('hand', 'block', 'identities', 'deck', 'button', 'actors', 'actions', 'states', 'history', 'settlement', 'rewards')
    return all(row[k] == reference[k] for k in keys)


def scan_file(job):
    """Stream one trace; write hands CSV, showdown requests and counters. Returns a receipt."""
    path, out, label, field, sha, focal_sha, reference = job
    digest = hashlib.sha256()
    out = Path(out)
    hands_path = out / 'hands' / label / f'{field}.csv'
    showdown_path = out / 'showdowns' / label / f'{field}.jsonl'
    for p in (hands_path, showdown_path):
        p.parent.mkdir(parents=True, exist_ok=True)
    decisions = defaultdict(lambda: [0, 0])
    style = {0: defaultdict(int), 1: defaultdict(int)}
    total = count = matched = violations = 0
    ref = None
    if reference:
        ref = open(reference, 'rb')
        next(ref)
    with open(path, 'rb') as f, hands_path.open('x', newline='') as h, showdown_path.open('x') as s:
        writer = csv.DictWriter(h, HAND_COLUMNS)
        writer.writeheader()
        line = next(f)
        digest.update(line)
        header = json.loads(line)
        n, schedule = evidence.header_check(header)
        if header['policies'][0].get('sha256') != focal_sha:
            raise ValueError(f'{path}: focal model differs')
        mode = header.get('focal_untrained_fallback', 'uniform')
        for index, line in enumerate(f):
            digest.update(line)
            row = json.loads(line)
            evidence.validate_row(row, index, header, n, schedule)
            seat, record, decided, request, showdown = classify(row, n)
            writer.writerow(record)
            violations += fallback_violations(row, seat, mode)
            if request:
                s.write(json.dumps(request, separators=(',', ':')) + '\n')
            for street, status, cls, facing, paid in decided:
                d = decisions[f'{street}|{status}|{cls}|{facing}']
                d[0] += 1
                d[1] += paid
            style_counts(row, seat, showdown, style[0])
            style_counts(row, row['identities'].index(1), showdown, style[1])
            total += row['rewards'][seat]
            count += 1
            if ref is not None:
                matched += compared(row, json.loads(next(ref)))
    if ref is not None:
        ref.close()
    if count != header['hands']:
        raise ValueError(f'{path}: hand count')
    receipt = {'label': label, 'field': field, 'path': str(path), 'sha256': digest.hexdigest(), 'expected_sha256': sha,
               'hash_matches': sha is None or digest.hexdigest() == sha, 'players': n, 'blocks': header['blocks'],
               'seatings': len(schedule), 'hands': count, 'mean_bb100': total * 100 / header['identity']['big_blind'] / count,
               'fallback': mode, 'fallback_violations': violations,
               'decisions': {k: v for k, v in sorted(decisions.items())},
               'style': {'focal': dict(style[0]), 'opponent_identity1': dict(style[1])}}
    if reference:
        receipt['reference'] = {'path': str(reference), 'matched_hands': matched, 'all_matched': matched == count}
    (out / 'receipts').mkdir(exist_ok=True)
    create(out / 'receipts' / f'{label}--{field}.json', json.dumps(receipt, indent=1) + '\n')
    return receipt


def jobs(config, out):
    work = []
    for spec in config['inputs']:
        for field in config['fields']:
            path = Path(spec['trace'].format(field=field))
            work.append((str(path), str(out), spec['label'], field, expected_sha(spec['hash'], field, path), spec['focal_sha256'], None))
    fallback = Path(out) / 'fallback'
    if fallback.exists():
        by_label = {s['label']: s for s in config['inputs']}
        for bank in config['fallback']['banks']:
            spec = by_label[bank]
            for field in config['fields']:
                for mode in config['fallback']['modes']:
                    trace = fallback / bank / f'{field}-{mode}.jsonl'
                    reference = spec['trace'].format(field=field) if mode == 'uniform' else None
                    work.append((str(trace), str(out), f'B{bank}-{mode}', field, None, spec['focal_sha256'], reference))
    return work


def scan(args):
    config = json.loads(args.config.read_text())
    work = [j for j in jobs(config, args.out) if not (args.out / 'receipts' / f'{j[2]}--{j[3]}.json').exists()]
    if args.only:
        work = [j for j in work if j[2].startswith(args.only)]
    with Pool(args.workers) as pool:
        for receipt in pool.imap_unordered(scan_file, work):
            print(json.dumps({k: receipt[k] for k in ('label', 'field', 'hands', 'hash_matches', 'mean_bb100')}), flush=True)


def equity(args):
    for requests in sorted((args.out / 'showdowns').glob('*/*.jsonl')):
        target = args.out / 'equity' / requests.parent.name / requests.name
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with requests.open('rb') as src, open(str(target) + '.partial', 'xb') as dst:
            subprocess.run([str(args.binary)], stdin=src, stdout=dst, check=True)
        Path(str(target) + '.partial').rename(target)
        print(json.dumps({'equity': str(target)}), flush=True)


def fallback_manifest(args):
    config = json.loads(args.config.read_text())
    by_label = {s['label']: s for s in config['inputs']}
    catalog, cases, tables, late = {}, [], None, []
    for bank in config['fallback']['banks']:
        spec = by_label[bank]
        manifest = json.loads(Path(spec['manifest']).read_text())
        tables = tables or manifest['tables']
        if manifest['tables'] != tables:
            raise ValueError('K50 tables differ between banks')
        # Only the pinned focal and the opponents of the selected fields are carried over.
        used = {o for c in manifest['cases'] if c['name'] in config['fields'] for o in c['opponents'] if not o.startswith('bot=')}
        alias = {}
        for name in used | {spec['focal_alias']}:
            model = {k: manifest['models'][name][k] for k in ('path', 'sha256', 'mass', 'mass_sha256')}
            short = 'ten' if model['sha256'] == spec['focal_sha256'] else 'three'
            if catalog.setdefault(short, model) != model:
                raise ValueError(f'{short} differs between banks')
            alias[name] = short
        if alias[spec['focal_alias']] != 'ten':
            raise ValueError('focal alias is not the pinned 10B')
        for case in manifest['cases']:
            if case['name'] not in config['fields']:
                continue
            opponents = [o if o.startswith('bot=') else alias[o] for o in case['opponents']]
            folder = args.out / 'fallback' / bank
            row = {k: case[k] for k in ('players', 'stack_bb', 'blocks', 'root', 'schedule')}
            row.update(name=f"{bank}-{case['name']}", focals=['ten', 'ten'], opponents=opponents,
                       focal_untrained_fallback=config['fallback']['modes'],
                       traces=[str(folder / f"{case['name']}-{m}.jsonl") for m in config['fallback']['modes']],
                       summary=str(folder / f"{case['name']}-cost.json"))
            (late if 'three' in opponents else cases).append(row)
    for bank in config['fallback']['banks']:
        (args.out / 'fallback' / bank).mkdir(parents=True, exist_ok=True)
    # 10B-only cases first so the 3B table loads once, for the trained fields at the end.
    manifest = {'format': 'nplayer-paired-manifest-v1', 'tables': tables, 'threads': config['fallback']['threads'],
                'models': catalog, 'cases': cases + late}
    target = args.out / 'fallback-manifest.json'
    create(target, json.dumps(manifest, indent=1) + '\n')
    print(json.dumps({'manifest': str(target), 'cases': len(manifest['cases'])}))


def published(spec, field, repo):
    with (repo / spec['csv']).open() as f:
        rows = list(csv.DictReader(f))
    hits = [r for r in rows if r['field'] == field and all(r[k] == v for k, v in spec['where'].items())]
    if len(hits) != 1:
        raise ValueError(f"{spec['csv']}: {field} not unique")
    return float(hits[0][spec['column']])


def block_means(rows, key, seatings, bb):
    sums = defaultdict(float)
    for r in rows:
        sums[r['block']] += r[key]
    return [sums[b] * 100 / bb / seatings for b in sorted(sums)]


def report(args):
    config = json.loads(args.config.read_text())
    out = args.out
    receipts = {(r['label'], r['field']): r for r in (json.loads(p.read_text()) for p in (out / 'receipts').glob('*.json'))}
    failures = [list(k) for k, r in receipts.items() if not r['hash_matches'] or r['fallback_violations']
                or not r.get('reference', {}).get('all_matched', True)]
    summary = {'format': 'nplayer-loss-diagnosis-results-v1', 'inputs': {}, 'fallback': {}, 'failures': failures}
    partitions, luck = [], []
    blocks_by = {}
    for (label, field), receipt in sorted(receipts.items()):
        bb, seatings = 100, receipt['seatings']
        rows = hand_rows(out, label, field)
        realized = block_means(rows, 'reward', seatings, bb)
        adjusted = block_means(rows, 'adjusted', seatings, bb)
        blocks_by[label, field] = (realized, adjusted, rows)
        entry = {'hands': len(rows), 'blocks': len(realized), 'realized': interval(realized), 'adjusted': interval(adjusted),
                 'locked_hands': sum(r['locked'] for r in rows), 'showdown_hands': sum(r['showdown'] for r in rows),
                 'trace_sha256': receipt['sha256'], 'fallback': receipt['fallback']}
        entry['luck_bb100'] = entry['realized']['mean_bb100'] - entry['adjusted']['mean_bb100']
        spec = next((s for s in config['inputs'] if s['label'] == label), None)
        if spec:
            entry['published_bb100'] = published(spec['published'], field, args.repo)
            entry['reproduced'] = abs(entry['published_bb100'] - entry['realized']['mean_bb100']) < 1e-9
            if not entry['reproduced']:
                failures.append([label, field, 'published mean not reproduced'])
        summary['inputs'].setdefault(label, {})[field] = entry
        luck.append({'input': label, 'field': field, 'realized_bb100': entry['realized']['mean_bb100'],
                     'realized_se': entry['realized']['standard_error_bb100'], 'adjusted_bb100': entry['adjusted']['mean_bb100'],
                     'adjusted_se': entry['adjusted']['standard_error_bb100'], 'luck_bb100': entry['luck_bb100'],
                     'locked_hands': entry['locked_hands'], 'hands': len(rows)})
        for dimension in DIMENSIONS:
            groups = defaultdict(lambda: [0, 0, 0])
            for r in rows:
                g = groups[r[dimension]]
                g[0] += 1
                g[1] += r['reward']
                g[2] += r['adjusted']
            for category, (hands, real, adj) in sorted(groups.items()):
                partitions.append({'input': label, 'field': field, 'dimension': dimension, 'category': category,
                                   'hands': hands, 'share': hands / len(rows),
                                   'realized_bb100': real * 100 / bb / len(rows), 'adjusted_bb100': adj * 100 / bb / len(rows)})
    six = [s['label'] for s in config['inputs'] if s['players'] == 6]
    for field in config['fields']:
        estimates = [summary['inputs'][label][field] for label in six if label in summary['inputs']]
        if len(estimates) == len(six):
            summary.setdefault('heterogeneity', {})[field] = {
                'realized': cochran([e['realized'] for e in estimates]), 'adjusted': cochran([e['adjusted'] for e in estimates])}
    for bank in config['fallback']['banks']:
        for field in config['fields']:
            a, b = (f'B{bank}-{m}' for m in config['fallback']['modes'])
            if (a, field) not in blocks_by or (b, field) not in blocks_by:
                continue
            (ra, aa, rows_a), (rb, ab, rows_b) = blocks_by[a, field], blocks_by[b, field]
            changed = sum(x['reward'] != y['reward'] or x['ending'] != y['ending'] for x, y in zip(rows_a, rows_b))
            summary['fallback'].setdefault(bank, {})[field] = {
                'realized': interval([y - x for x, y in zip(ra, rb)]), 'adjusted': interval([y - x for x, y in zip(aa, ab)]),
                'replaced_decisions': sum(r['replaced'] for r in rows_b), 'hands_with_replacement': sum(r['replaced'] > 0 for r in rows_b),
                'hands_with_different_result': changed, 'hands': len(rows_b),
                'uniform_reproduces_history': receipts[a, field]['reference']['all_matched']}
            summary['fallback'][bank][field]['_blocks'] = ([y - x for x, y in zip(ra, rb)], [y - x for x, y in zip(aa, ab)])
    pooled = {}
    for field in config['fields']:
        parts = [summary['fallback'][bank][field].pop('_blocks') for bank in config['fallback']['banks']
                 if field in summary['fallback'].get(bank, {})]
        if len(parts) == len(config['fallback']['banks']):
            pooled[field] = {'realized': interval(sum((p[0] for p in parts), [])), 'adjusted': interval(sum((p[1] for p in parts), []))}
    summary['fallback']['pooled'] = pooled
    summary['failures'] = failures
    args.results.mkdir(parents=True, exist_ok=True)
    (args.results / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    tables = (('partitions', partitions), ('luck', luck), ('untrained', untrained_rows(receipts)), ('style', style_rows(receipts)),
              ('banks', bank_rows(partitions, six, config['fields'])), ('table-size', size_rows(partitions, config)))
    for name, rows in tables:
        with (args.results / f'{name}.csv').open('w', newline='') as f:
            w = csv.DictWriter(f, list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(json.dumps({'failures': failures, 'inputs': len(receipts)}))


def bank_rows(partitions, six, fields):
    """Each category's contribution in every six-player bank, and the last bank minus the first."""
    if not six:
        return []
    cells = {(p['input'], p['field'], p['dimension'], p['category']): p for p in partitions}
    rows = []
    for field in fields:
        for dimension in DIMENSIONS:
            categories = sorted({c for (i, f, d, c) in cells if f == field and d == dimension and i in six})
            for category in categories:
                row = {'field': field, 'dimension': dimension, 'category': category}
                for label in six:
                    cell = cells.get((label, field, dimension, category), {'realized_bb100': 0.0, 'adjusted_bb100': 0.0, 'share': 0.0})
                    row[f'{label}_share'] = cell['share']
                    row[f'{label}_realized_bb100'] = cell['realized_bb100']
                    row[f'{label}_adjusted_bb100'] = cell['adjusted_bb100']
                row['last_minus_first_realized_bb100'] = row[f'{six[-1]}_realized_bb100'] - row[f'{six[0]}_realized_bb100']
                row['last_minus_first_adjusted_bb100'] = row[f'{six[-1]}_adjusted_bb100'] - row[f'{six[0]}_adjusted_bb100']
                rows.append(row)
    return rows


def size_rows(partitions, config):
    """Contributions by table size; six players is the equal-weight mean of its banks (equal hands per bank)."""
    groups = defaultdict(list)
    for s in config['inputs']:
        groups[s['players']].append(s['label'])
    cells = {(p['input'], p['field'], p['dimension'], p['category']): p for p in partitions}
    rows = []
    for field in config['fields']:
        for dimension in DIMENSIONS:
            categories = sorted({c for (i, f, d, c) in cells if f == field and d == dimension and not i.startswith('B')})
            for category in categories:
                row = {'field': field, 'dimension': dimension, 'category': category}
                for players, labels in sorted(groups.items()):
                    got = [cells.get((label, field, dimension, category)) for label in labels]
                    for key in ('share', 'realized_bb100', 'adjusted_bb100'):
                        row[f'{players}p_{key}'] = statistics.fmean(g[key] if g else 0.0 for g in got)
                rows.append(row)
    return rows


def hand_rows(out, label, field):
    expected = {}
    with (out / 'showdowns' / label / f'{field}.jsonl').open() as requests, \
            (out / 'equity' / label / f'{field}.jsonl').open() as results:
        for line, request in zip(results, requests, strict=True):
            result, request = json.loads(line), json.loads(request)
            if result['id'] != request['id'] or not result['realized_ok']:
                raise ValueError(f"{label}/{field}: showdown {request['id']} not reproduced")
            expected[result['id']] = result['expected']
    rows = []
    with (out / 'hands' / label / f'{field}.csv').open() as f:
        for r in csv.DictReader(f):
            for k in ('hand', 'block', 'seat', 'untrained_decisions', 'replaced', 'reward', 'showdown', 'locked'):
                r[k] = int(r[k])
            # Only the all-in-before-river showdowns carry luck; the others keep their result.
            r['adjusted'] = expected[r['hand']][r['seat']] if r['locked'] else r['reward']
            rows.append(r)
    return rows


def untrained_rows(receipts):
    rows = []
    for (label, field), receipt in sorted(receipts.items()):
        for key, (count, paid) in receipt['decisions'].items():
            street, status, cls, facing = key.split('|')
            rows.append({'input': label, 'field': field, 'street': street, 'status': status, 'action': cls,
                         'situation': facing, 'decisions': count, 'chips_paid': paid})
    return rows


def style_rows(receipts):
    rows = []
    for (label, field), receipt in sorted(receipts.items()):
        for who, c in receipt['style'].items():
            c = defaultdict(int, c)
            rate = lambda a, b: c[a] / c[b] if c[b] else None
            row = {'input': label, 'field': field, 'player': who, 'hands': c['hands'], 'vpip': rate('vpip', 'hands'),
                   'pfr': rate('pfr', 'hands'), 'threebet': rate('threebets', 'threebet_opportunities'),
                   'fold_to_threebet': rate('folds_to_threebet', 'fold_to_threebet_opportunities'),
                   'wtsd': rate('went_to_showdown', 'saw_flop'), 'wsd': rate('won_at_showdown', 'went_to_showdown'),
                   'all_in_share': rate('all_in', 'decisions')}
            for street in STREETS[1:]:
                row[f'{street}_fold_to_bet'] = rate(f'{street}_fold_to_bet', f'{street}_facing_bet')
                row[f'{street}_aggression'] = rate(f'{street}_aggressive', f'{street}_decisions')
            rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('scan', 'equity', 'fallback-manifest', 'report'):
        p = sub.add_parser(name)
        p.add_argument('--config', type=Path, required=True)
        p.add_argument('--out', type=Path, required=True)
        if name == 'scan':
            p.add_argument('--workers', type=int, default=8)
            p.add_argument('--only', default='')
        if name == 'equity':
            p.add_argument('--binary', type=Path, required=True)
        if name == 'report':
            p.add_argument('--repo', type=Path, default=Path('.'))
            p.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    {'scan': scan, 'equity': equity, 'fallback-manifest': fallback_manifest, 'report': report}[args.command](args)


if __name__ == '__main__':
    main()
