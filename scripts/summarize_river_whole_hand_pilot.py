"""Derive operational tables from an already settled PR388 pilot; never play hands."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import statistics

from scripts.river_whole_hand_pilot import read, sha, stats, write


def summarize(root, out):
    out.mkdir(parents=True, exist_ok=False)
    assert read(root/'status.json')['status'] == 'complete'
    assert not (root/'failure.json').exists()
    stages = read(root/'stage-costs.json')
    assert all(x['returncode'] == 0 for x in stages)
    settled = read(root/'readout/results.json')
    assert settled['status'] == 'settled'
    proof = read(root/'measure/verified.json')
    assert proof['status'] == 'passed'
    assert len(proof['records']) == 12
    manifest = read(root/'measure/initial/manifest.json')
    rows = []
    latencies = []
    continuations = []
    all_components = Counter()
    all_counts = Counter()
    first_river = Counter()
    seat_rows = []
    failures = []
    byte_totals = Counter()
    for c in manifest['cases']:
        expected = next(x for x in proof['records'] if x['case'] == c['name'])
        assert sha(c['trace']) == expected['sha256']
        assert expected['independent_replay']['status'] == 'passed'
        if not c['search']:
            continue
        name = c['name'].removesuffix('-on')
        prior = next(x for x in settled['lineups'] if x['lineup'] == name)
        counts = Counter()
        composition = Counter()
        by_seat = {i: Counter() for i in range(3)}
        with Path(c['trace']).open() as f:
            next(f)
            for line in f:
                h = json.loads(line)
                seat = h['identities'].index(0)
                by_seat[seat]['hands'] += 1
                river = [i for i, s in enumerate(h['states'][:-1]) if s['street'] == 'river']
                if river:
                    i = river[0]
                    state = h['states'][i]
                    live = [p for p in state['players'] if not p[3]]
                    composition['river_hands'] += 1
                    composition['two_live' if len(live) == 2 else 'three_live'] += 1
                    composition['focal_already_folded'] += int(state['players'][seat][3])
                    all_in = any(p[0] == 0 for p in live)
                    composition['any_live_all_in'] += int(all_in)
                    focal = h['actors'][i] == seat
                    composition['focal_first_actor'] += int(focal)
                    composition['two_live_not_all_in'] += int(len(live) == 2 and not all_in)
                    composition['two_live_not_all_in_focal_first'] += int(len(live) == 2 and not all_in and focal)
                for ledger in h['search_ledgers']:
                    if ledger is None:
                        continue
                    counts['focal_decisions'] += 1
                    counts['blueprint_found'] += int(ledger['blueprint_found'])
                    counts['same_draw_changes'] += int(ledger['changed_same_draw'])
                    mode = ledger['mode']
                    counts[mode+'_decisions'] += 1
                    by_seat[seat][mode+'_decisions'] += 1
                    s = ledger['search']
                    if s is None:
                        continue
                    counts[mode+'_installed'] += int(s['installed'])
                    by_seat[seat][mode+'_installed'] += int(s['installed'])
                    if mode == 'root' and not s['installed']:
                        failures.append({'lineup':name,'hand':h['hand'], 'seat':seat,
                            'reason':s['fallback_reason'],'sweeps':s['sweeps'],'nodes':s['nodes'],'quality':s['quality']})
                    if s.get('first_off_tree'):
                        counts['off_tree_hands'] += 1
                        counts['off_tree_all_in'] += int(s['off_tree_entry']['all_in'])
                        counts['off_tree_cap_reached'] += int(s['off_tree_entry']['cap_reached'])
        assert counts['root_decisions'] == prior['counts'].get('root_decisions', 0)
        assert counts['root_installed'] == prior['counts'].get('root_installed', 0)
        assert composition['two_live_not_all_in_focal_first'] == counts['root_decisions']
        components = Counter()
        with Path(c['metrics']).open() as f:
            for line in f:
                m = json.loads(line)
                if m['mode'] == 'root':
                    latencies.append(m['seconds'])
                    for key, value in m['components'].items():
                        components[key] += value
                elif m['mode'] == 'continuation':
                    continuations.append(m['seconds'])
        row = {'lineup':name,'hands':768,'calls_per_hand':counts['root_decisions']/768,
            'installed_per_hand':counts['root_installed']/768,'counts':dict(counts),
            'first_river':dict(composition),'root_components_sum_seconds':dict(components)}
        rows.append(row)
        all_counts.update(counts);first_river.update(composition);all_components.update(components)
        for seat, values in by_seat.items():
            seat_rows.append({'lineup':name,'seat':seat,**dict(values)})
    costs = {part:read(root/f'measure/{part}/costs.json') for part in ('initial','repeat')}
    case_costs = {part:{c['name']:read(c['summary'])['play_and_write_seconds'] for c in
        read(root/f'measure/{part}/manifest.json')['cases']} for part in ('initial','repeat')}
    for part in ('initial', 'repeat'):
        for c in read(root/f'measure/{part}/manifest.json')['cases']:
            for key in ('trace','metrics','summary'):
                byte_totals[key] += Path(c[key]).stat().st_size
    data = {'status':'settled-derived','scope':'operational analysis of original verified hands; no new play',
        'source_results_sha256':sha(root/'readout/results.json'),'summary_script_sha256':sha(Path(__file__)),
        'lineups':rows,'counts':dict(all_counts),'first_river':dict(first_river),
        'root_latency_seconds':stats(latencies),'continuation_latency_seconds':stats(continuations),
        'root_components_sum_seconds':dict(all_components),'root_fallbacks':failures,
        'costs':costs,'case_costs_seconds':case_costs,'artifact_bytes':dict(byte_totals),
        'independent_verify_including_pairing_seconds':proof['independent_replay_seconds'],
        'stage_costs':stages,'seat_counts':seat_rows}
    write(out/'operational.json',data)
    with (out/'seat-coverage.csv').open('x') as f:
        fields=['lineup','seat','hands','blueprint_decisions','root_decisions','root_installed',
                'continuation_decisions','continuation_installed']
        writer=csv.DictWriter(f,fieldnames=fields,restval=0);writer.writeheader();writer.writerows(seat_rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('root',type=Path)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();summarize(args.root,args.out)


if __name__=='__main__':main()
