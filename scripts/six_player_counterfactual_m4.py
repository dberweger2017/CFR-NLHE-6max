"""Outcome-blind legal observation extraction and cost-only planning for PR438.

This module never trains, starts an arena, copies artifacts or launches the main.
Raw privileged traces remain on the evaluator side of the privacy boundary.
"""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path

MODEL = 'f894a59f8a92424d735438726d16834901a7dcaf6d560c98b950fb72a143c9ea'
CHECKPOINT = '75245fbb0a00617ae67281e25cd7184b4a27fbf72e5aa2b175ba5a37c93771d8'
FIELDS = {'id', 'hero', 'button', 'hole', 'board', 'actions', 'opponents',
          'street', 'expected_key', 'stratum', 'split'}
STREETS = {'preflop': 0, 'flop': 1, 'turn': 2, 'river': 3}

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def dump(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def score(hole):
    hi, lo = sorted((c//4 + 2 for c in hole), reverse=True)
    if hi == lo:
        return .55 + hi/35
    return min(.95, (hi+lo-4)/40 + (.08 if hole[0]%4 == hole[1]%4 else 0)
               + (.06 if hi-lo <= 2 else 0))


def candidates(bank, row):
    """Only this host extractor may access privileged records; outputs are public."""
    hero = row['identities'].index(0)
    seen = set()
    for ordinal, actor in enumerate(row['actors']):
        if actor != hero:
            continue
        state = row['states'][ordinal]
        street = STREETS[state['street']]
        if street in seen:
            continue
        seen.add(street)
        own = state['holes'][hero]
        action = row['actions'][ordinal]
        tier = score(own)
        category = ('weak-raise' if tier < .30 and action[0] == 'raise' else
                    'good-fold' if .45 <= tier < .60 and action[0] == 'fold' else 'other')
        stratum = f'seat{hero}/' + (f'preflop/{category}' if street == 0 else state['street'])
        identity = f'{bank}|{row["block"]}|{row["permutation"]}|{ordinal}'
        priority = hashlib.sha256(('six-player-conditional-panel-v1|'+identity).encode()).hexdigest()
        legal = dict(id=identity, hero=hero, button=row['button'], hole=list(own),
                     board=state['board'], actions=[[a, *x] for a, x in zip(row['actors'][:ordinal], row['actions'][:ordinal])],
                     opponents=['hero' if s == hero else 'check-call' for s in range(6)],
                     street=street, expected_key=row['lookups'][ordinal]['key'],
                     stratum=stratum, split='fixed-panel')
        assert set(legal) == FIELDS
        yield priority, (bank, row['block']), legal


def select(all_candidates):
    grouped = defaultdict(list)
    for priority, block, legal in all_candidates:
        grouped[legal['stratum']].append((priority, block, legal))
    selected, used, counts = [], set(), {}
    for seat in range(6):
        for name in ['flop', 'preflop/good-fold', 'preflop/other', 'preflop/weak-raise', 'river', 'turn']:
            stratum = f'seat{seat}/{name}'
            counts[stratum] = len(grouped[stratum])
            for _, block, legal in sorted(grouped[stratum], key=lambda x: x[0]):
                if block not in used:
                    used.add(block)
                    selected.append(legal)
                    break
    return selected, counts


def validate_header(header):
    pins = header['policies']
    g = header['identity']
    if (header['harness'] != 'nplayer-paired-v1' or header['blocks'] != 4096
            or header['hands'] != 4096*12 or len(header['schedule']) != 12
            # Historical header names the common game through the control identity;
            # bind the focal model separately and check its schema in native code.
            or g['schema'] != 'nplayer-button-live-actor-history-equity-k50-v1'
            or g['players'] != 6 or g['stacks'] != [10000]*6
            or g['small_blind'] != 50 or g['big_blind'] != 100
            or len(pins) != 6 or pins[0]['sha256'] != MODEL
            or pins[0]['source_checkpoint_sha256'] != CHECKPOINT
            or pins[0]['average_scope'] != 3 or pins[0]['strategy'] != 'average'
            or any(p.get('script') != 'check-call' for p in pins[1:])):
        raise ValueError('not a pinned PR431 live-order check-call bank')


def extract(inventory, output):
    """Bind trace bytes and the original verification receipt (not a new replay)."""
    if len(inventory['banks']) != 4 or {b['bank'] for b in inventory['banks']} != set(range(4)):
        raise ValueError('exactly four original banks required')
    output = Path(output)
    output.mkdir(exist_ok=False)
    grouped, counts, provenance = defaultdict(dict), defaultdict(int), []
    for entry in sorted(inventory['banks'], key=lambda b: b['bank']):
        path, proof = Path(entry['trace']), Path(entry['proof'])
        if sha(proof) != entry['proof_sha256'] or sha(path) != entry['file_sha256']:
            raise ValueError('historical input/proof changed')
        receipt = json.loads(proof.read_text())
        replay = (receipt.get('status') == 'passed' and receipt.get('trace_sha256') == entry['sha256'])
        legacy = (receipt.get('sha256') == entry['sha256'] and receipt.get('hash_matches') is True
                  and receipt.get('label') == f'live-b{entry["bank"]}' and receipt.get('field') == 'check-call'
                  and receipt.get('hands') == 4096*12 and receipt.get('fallback_violations') == 0)
        if not (replay or legacy):
            raise ValueError('original verification receipt does not bind trace')
        count, seen = 0, set()
        content_hash = hashlib.sha256()
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'rb') as f:
            first = next(f);content_hash.update(first)
            header = json.loads(first)
            validate_header(header)
            if header['seed'] != 20261025900002 + entry['bank']*100:
                raise ValueError('original bank root differs')
            for line in f:
                content_hash.update(line)
                row = json.loads(line)
                key = (row['block'], row['permutation'])
                if key in seen or not (0 <= key[0] < 4096 and 0 <= key[1] < 12):
                    raise ValueError('duplicate/invalid original block/seating')
                seen.add(key)
                for priority, block, legal in candidates(entry['bank'], row):
                    stratum = legal['stratum'];counts[stratum] += 1
                    pool = grouped[stratum]
                    if block not in pool or priority < pool[block][0]:
                        pool[block] = (priority, block, legal)
                    # At most35 other strata can consume blocks;37 distinct
                    # candidates per stratum exactly preserve the greedy choice.
                    if len(pool) > 37:
                        del pool[max(pool, key=lambda k: pool[k][0])]

                count += 1
        if content_hash.hexdigest() != entry['sha256']:
            raise ValueError('uncompressed historical trace changed')
        if count != 4096*12:
            raise ValueError('incomplete historical bank')
        provenance.append(dict(bank=entry['bank'], trace_sha256=entry['sha256'], proof_sha256=entry['proof_sha256'], hands=count))
    chosen, slots = select(v for pool in grouped.values() for v in pool.values())
    counts = {k: counts[k] for k in slots}
    path = output/'states.jsonl'
    with path.open('x') as f:
        for legal in chosen:
            f.write(json.dumps(legal, sort_keys=True, allow_nan=False)+'\n')
    dump(output/'inventory.json', dict(format='six-player-conditional-panel-v1', model_sha256=MODEL,
         checkpoint_sha256=CHECKPOINT, roots=len(chosen), candidate_counts=counts,
         missing_strata=[k for k, n in counts.items() if not n], states_sha256=sha(path), banks=provenance,
         no_rewards_or_hidden_cards_selected=True, no_counterfactual_values_used=True))


def quote(receipt):
    if receipt['status'] != 'passed' or not receipt['calibration_only'] or not receipt['float64_and_work_reproduced']:
        raise ValueError('successful mature calibration required')
    costs = receipt['costs']
    if len(costs) != receipt['roots'] or any(x['worlds_per_pass'] != 8 for x in costs):
        raise ValueError('calibration counts differ')
    # Every measured root is retained; main and repeat reuse one resident model.
    continuation = sum(x['seconds_including_repeat'] for x in costs) * (64+2048)/8
    central = receipt['load_and_k50_seconds'] + continuation + 120
    reserve = 2*receipt['load_and_k50_seconds'] + 3*continuation + 600
    return dict(format='six-player-conditional-quote-v1', roots=receipt['roots'],
                discovery_worlds=64, heldout_worlds=2048, repetitions=2,
                model_and_k50_seconds=receipt['load_and_k50_seconds'], continuation_seconds=continuation,
                central_seconds=central, reserved_seconds=reserve,
                no_outcomes_used_for_work_selection=True, main_started=False,
                independent_review_required=True, explicit_main_budget_required=True,
                assumptions='Fixed same roots/menu; linear worlds extrapolation; 3x continuation/2x load reserve +600s proof allowance. Not a completion guarantee.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('extract', 'quote'):
        a = sub.add_parser(name)
        a.add_argument('input', type=Path)
        a.add_argument('output', type=Path)
    a = p.parse_args()
    data = json.loads(a.input.read_text())
    if a.command == 'extract':
        extract(data, a.output)
    else:
        dump(a.output, quote(data))

if __name__ == '__main__':
    main()
