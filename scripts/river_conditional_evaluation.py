"""Saved PR388 roots only: freeze inventory, calibrate exact continuation cost.

Never starts training, new deals or an automatic full-inventory/strength run.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import subprocess
from time import monotonic

from scripts.river_whole_hand_pilot import FOCAL_SHA, PEER_SHA, LINEUPS, read, sha, write


def calibration_roots(roots):
    selected = set()
    for name, _ in LINEUPS:
        selected.update(r['id'] for r in [x for x in roots if x['lineup'] == name][:2])
    selected.update(r['id'] for r in roots if not r['expected']['installed'])
    return [r for r in roots if r['id'] in selected]


def block_contrasts(inventory, evaluated):
    """All original blocks, including noneligible hands; never root-only means."""
    expected = {r['id'] for r in inventory}
    if len(expected) != len(inventory) or set(evaluated) != expected:
        raise ValueError('complete unique root coverage required')
    values = {name: [0.] * 128 for name, _ in LINEUPS}
    hands = set()
    for root in inventory:
        result = evaluated[root['id']]
        if not result['identity_verified'] or not result['complete_contrast']:
            raise ValueError('incomplete root cannot enter variance assessment')
        hand = root['lineup'], root['hand']
        if hand in hands or not 0 <= root['block'] < 128:
            raise ValueError('duplicate hand or invalid block')
        hands.add(hand)
        if root['hand'] != root['block'] * 6 + root['permutation']:
            raise ValueError('six-permutation hand identity differs')
        values[root['lineup']][root['block']] += result['contrast_chips'] / 6
    return values


def freeze(args):
    pilot = args.pilot
    if read(pilot/'status.json')['status'] != 'complete' or (pilot/'failure.json').exists():
        raise ValueError('complete successful original pilot required')
    pinned = read(Path(__file__).resolve().parents[1]/'docs/reports/river-whole-hand-pilot/provenance.json')
    if sha(pilot/'readout/results.json') != pinned['result_sha256']:
        raise ValueError('original settled readout differs')
    proof = read(pilot/'measure/verified.json')
    manifest = read(pilot/'measure/initial/manifest.json')
    repeated = read(pilot/'measure/repeat/manifest.json')
    roots = []
    trace_pins = []
    for c in manifest['cases']:
        old = next(x for x in proof['records'] if x['case'] == c['name'])
        repeat = next(x for x in repeated['cases'] if x['name'] == c['name'])
        if (old['independent_replay']['status'] != 'passed' or old['independent_replay']['hands'] != 768
                or sha(c['trace']) != old['sha256'] or sha(repeat['trace']) != old['sha256']):
            raise ValueError('original replay/reproduction/trace identity differs')
        trace_pins.append({'case':c['name'],'sha256':old['sha256']})
        if not c['search']:
            continue
        lineup = c['name'].removesuffix('-on')
        with Path(c['trace']).open() as f:
            header = json.loads(next(f))
            if header['blocks'] != 128 or header['hands'] != 768:
                raise ValueError('original fixed count differs')
            for line in f:
                hand = json.loads(line)
                for decision, ledger in enumerate(hand['search_ledgers']):
                    if ledger is None or ledger['mode'] != 'root':
                        continue
                    search = ledger['search']
                    roots.append({'id':f"{lineup}/{hand['hand']:04d}/{decision:04d}",
                        'ordinal':len(roots),'lineup':lineup,'hand':hand['hand'],'block':hand['block'],
                        'permutation':hand['permutation'],'decision':decision,'deck':hand['deck'],
                        'button':hand['button'],'identities':hand['identities'],
                        'prefix_actions':hand['actions'][:decision],'opponents':c['opponents'],
                        'expected':{**{key:search[key] for key in ('profile_sha256','installed','fallback_reason','sweeps','nodes')},
                            'actions':ledger['actions'],'probabilities':ledger['probabilities']}})
    roots.sort(key=lambda x:(next(i for i,(name,_) in enumerate(LINEUPS) if name==x['lineup']),x['hand'],x['decision']))
    for i,r in enumerate(roots):r['ordinal']=i
    if len(roots) != 384 or sum(r['expected']['installed'] for r in roots) != 381:
        raise ValueError('complete 384-root inventory with three fallbacks required')
    counts = dict(Counter(r['lineup'] for r in roots))
    if counts != {'trained':74,'trained-pressure':56,'pressure':26,'call-pressure':195,'random-tag':33}:
        raise ValueError('lineup root counts differ')
    if manifest['models']['focal']['sha256'] != FOCAL_SHA or manifest['models']['peer']['sha256'] != PEER_SHA:
        raise ValueError('model pins differ')
    value = {'format':'river-conditional-evaluation-v1','max_nodes_per_arm':200000,
        'models':manifest['models'],'k50':manifest['tables'],'pilot_root':str(pilot),
        'pilot_result_sha256':pinned['result_sha256'],'trace_pins':trace_pins,'roots':roots}
    write(args.out/'inventory.json',value)
    write(args.out/'inventory-proof.json',{'status':'frozen','roots':384,'installed':381,'quality_fallbacks':3,
        'root_counts':counts,'calibration_ids':[r['id'] for r in calibration_roots(roots)],
        'inventory_sha256':sha(args.out/'inventory.json'),'no_new_deals':True})


def calibrate(args):
    inventory = read(args.inventory)
    value = {**inventory,'roots':calibration_roots(inventory['roots']),
             'output':str(args.out/'records.jsonl'),'startup':str(args.out/'startup.json')}
    write(args.out/'manifest.json',value)
    tick = monotonic()
    with (args.out/'stdout').open('x') as o, (args.out/'stderr').open('x') as e:
        subprocess.run([str(args.binary),str(args.out/'manifest.json')],stdout=o,stderr=e,check=True)
    wall = monotonic()-tick
    rows = [json.loads(s) for s in (args.out/'records.jsonl').read_text().splitlines()]
    if [r['id'] for r in rows] != [r['id'] for r in value['roots']] or not all(r['identity_verified'] for r in rows):
        raise ValueError('calibration coverage/profile identity differs')
    startup = read(args.out/'startup.json')
    incomplete = [r['id'] for r in rows if not r['complete_contrast']]
    active = [r for r in rows if r['method'] == 'full-positive-support-enumeration']
    visits = sum(r[arm]['visited'] for r in active for arm in ('on','off'))
    enumeration = sum(r[arm]['seconds'] for r in active for arm in ('on','off'))
    # Fixed-work upper forecast: all 381 installed roots visit both arm limits.
    # This bounds visited work, not elapsed tails or coverage/completion.
    worst_per_node = max((r[arm]['seconds']/r[arm]['visited'] for r in active for arm in ('on','off')), default=0.)
    profiles = max((r['prepare_seconds'] for r in rows),default=0.)*384
    upper = 2*(2*startup['model_and_k50_seconds']+3*(profiles+worst_per_node*200000*2*381)+600)
    mean = statistics.mean(r['total_seconds'] for r in rows)*384
    quote = {'status':'calibrated','calibration_roots':len(rows),'profile_identities_passed':True,
        'complete_roots':len(rows)-len(incomplete),'incomplete_ids':incomplete,
        'visited_states':visits,'enumeration_seconds':enumeration,'wall_seconds':wall,'startup':startup,
        'all384_two_pass_mean_extrapolation_seconds':2*(startup['model_and_k50_seconds']+mean),
        'all384_two_pass_reserved_upper_seconds':upper,
        'method_qualified_at_fixed_limit':not incomplete,'full_inventory_started':False,
        'scope':'Fixed200K states/arm/root; worst measured seconds/node and max profile work, two cold passes,3x work/2x load reserves plus600s each pass. Not a completion guarantee or admitted budget.',
        'no_outcomes_used_for_selection':True,'next_action':'Owner budget decision before larger saved-data work; no strength run.'}
    write(args.out/'quote.json',quote)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['freeze','calibrate'])
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--pilot',type=Path);p.add_argument('--inventory',type=Path);p.add_argument('--binary',type=Path)
    args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    try:globals()[args.command](args)
    except BaseException as error:
        write(args.out/'failure.json',{'error':str(error)});raise


if __name__=='__main__':main()
