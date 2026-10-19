"""Derive compact PR355 tables from the verified readout; never replay or train."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

STREETS = ('preflop', 'flop', 'turn', 'river')
LABELS = ('positive_mass', 'zero_mass', 'missing')
MODELS = ('baseline', 'candidate')
POSITIONS = ('button', 'small_blind', 'big_blind')
KEYSET = 'a83858109eed965e73acd76787761d9353f2a66cccb482c0271173e3ff731425'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(out, name, rows):
    with (out / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def summarize(source, out):
    metadata = read(source / 'metadata.json')
    for name, receipt in metadata['source_files'].items():
        path = source / name
        if path.stat().st_size != receipt['bytes'] or sha(path) != receipt['sha256']:
            raise ValueError('compact source changed: ' + name)
    raw = read(source / 'results.json')
    results = raw['results']
    proof = read(source / 'comparison/evaluation-verified.json')
    manifest = read(source / 'comparison/evaluation-manifest.json')
    if (raw['status'] != 'settled' or results['status'] != 'settled'
            or metadata['completion']['status'] != 'complete'
            or set(metadata['stages']) != {'baseline-audit', 'continue-10b', 'candidate-audit', 'evaluation', 'readout'}
            or any(x['returncode'] != 0 for x in metadata['stages'].values())
            or proof != dict(status='passed', cases=18, hands=884736,
                             manifest_sha256=sha(source / 'comparison/evaluation-manifest.json'))
            or results['final_hands'] != 884736 or results['reproduction_hands'] != 884736):
        raise ValueError('global completion proof differs')
    for audit in results['mass_audits'].values():
        if audit['status'] != 'passed' or audit['rows'] != 250000475 or audit['keyset_sha256'] != KEYSET:
            raise ValueError('frozen membership audit differs')
    out.mkdir(parents=True, exist_ok=False)
    strength = []
    seats = []
    for row in results['rows']:
        name = row['opponent'] or 'direct'
        strength.append(dict(configuration=name, group=row['group'],
            baseline_bb100=row['baseline_absolute']['mean_bb100'], candidate_bb100=row['candidate_absolute']['mean_bb100'],
            **row['score']))
        for orientation, values in (('seat', row['by_seat']), ('position', row['by_position'])):
            for model, scores in values.items():
                for index, score in enumerate(scores):
                    seats.append(dict(configuration=name, model=model, orientation=orientation,
                                      index=index, label=POSITIONS[index] if orientation == 'position' else str(index), **score))
    # The primary reciprocal three-player statistic differs from a script difference.
    direct = results['rows'][0]
    assert abs(direct['score']['mean_bb100'] - (direct['candidate_absolute']['mean_bb100'] - direct['baseline_absolute']['mean_bb100']) / 2) < 1e-10
    for row in results['rows'][1:]:
        assert abs(row['score']['mean_bb100'] - (row['candidate_absolute']['mean_bb100'] - row['baseline_absolute']['mean_bb100'])) < 1e-10
    for row in strength:
        row.setdefault('lower_family95', '')
        row.setdefault('upper_family95', '')
    write_csv(out, 'strength.csv', strength)
    write_csv(out, 'seats-and-positions.csv', seats)
    coverage, positional, transitions, river, paths, strata = [], [], [], [], [], []
    totals = {model: Counter() for model in MODELS}
    pooled_lookup = {model: {street: Counter() for street in STREETS} for model in MODELS}
    for case in manifest['cases']:
        name = case['name']
        folder = source / 'comparison/evaluation' / name
        caseproof, replay = read(folder / 'result.json'), read(folder / 'replay.json')
        plays = [read(folder / ('play-' + str(i) + '.json')) for i in (0, 1)]
        hands = case['blocks'] * 6
        assert caseproof['status'] == replay['status'] == 'passed' and caseproof['case'] == case
        assert caseproof['hands'] == replay['hands'] == hands
        assert all(p['status'] == 'passed' and p['hands'] == hands and p['trace_sha256'] == replay['trace_sha256'] == caseproof['trace_sha256'] for p in plays)
        d = results['diagnostics'][name]
        assert d['source_trace_sha256'] == caseproof['trace_sha256']
        own = case['players'][0]
        assert own in MODELS
        assert set(d['matched_status_transitions']) <= {'positive_mass/positive_mass', 'zero_mass/zero_mass', 'zero_mass/positive_mass', 'missing/missing'}
        denominator = sum(d['matched_status_transitions'].values())
        assert denominator == sum(sum(s[0]) for s in d['lookup_counts'][0])
        for key, count in d['matched_status_transitions'].items():
            transitions.append(dict(case=name, acting_model=own, transition=key, decisions=count,
                                    total_decisions=denominator, percent=100*count/denominator))
            totals[own][key] += count
        for identity, player in enumerate(case['players']):
            if player.startswith('bot='):
                continue
            for street_index, street in enumerate(STREETS):
                for probe_index, probe in enumerate(MODELS):
                    counts = d['lookup_counts'][identity][street_index][probe_index]
                    total = sum(counts)
                    assert total == plays[0]['decisions_by_identity_street'][identity][street_index]
                    coverage.append(dict(case=name, identity=identity, acting_model=player, street=street, probe_model=probe,
                        total_decisions=total, **dict(zip(LABELS, counts)),
                        **{key+'_percent': 100*v/total if total else 0 for key,v in zip(LABELS, counts)}))
                    if identity == 0 and player == probe:
                        pooled_lookup[own][street].update(dict(zip(LABELS, counts)))
        for position_index, position in enumerate(POSITIONS):
            for street_index, street in enumerate(STREETS):
                for probe_index, probe in enumerate(MODELS):
                    counts = d['singleton_lookup_by_position_street'][position_index][street_index][probe_index]
                    assert all(v >= 0 for v in counts)
                    positional.append(dict(case=name, acting_model=own, position=position, street=street,
                                           probe_model=probe, total_decisions=sum(counts), **dict(zip(LABELS, counts))))
        for street_index in range(4):
            for probe_index in range(2):
                assert [sum(d['singleton_lookup_by_position_street'][p][street_index][probe_index][s] for p in range(3)) for s in range(3)] == d['lookup_counts'][0][street_index][probe_index]
        river.append(dict(case=name, acting_model=own, hands=hands, river_decision_hands=d['river_hands'][0],
                          two_live_river_decision_hands=d['river_hands'][1], percent=100*d['river_hands'][1]/hands))
        assert sum(v['hands'] for v in d['singleton_paths'].values()) == hands
        assert sum(v[0] for v in d['singleton_pot_bands'].values()) == hands
        for label, values in d['singleton_paths'].items():
            paths.append(dict(case=name, acting_model=own, path=label, hands=values['hands'],
                mean_bb100=values['sum_bb100']/values['hands'], contribution_bb100=values['sum_bb100']/hands,
                **values['example'], trace_sha256=d['source_trace_sha256']))
        for kind, values in [('reached_street', d['singleton_reached_street']), ('pot_band', d['singleton_pot_bands'])]:
            for label, (count, payoff) in values.items():
                strata.append(dict(case=name, acting_model=own, kind=kind, label=label, hands=count,
                    mean_bb100=payoff/count if count else 0, contribution_bb100=payoff/hands))
        # Every path and pot-band partition reproduces the singleton's absolute mean.
        singleton_mean = sum(v['sum_bb100'] for v in d['singleton_paths'].values())/hands
        row = next(x for x in results['rows'] if (x['opponent'] or 'direct') == (case.get('opponent') or 'direct'))
        assert abs(singleton_mean - row[own + '_absolute']['mean_bb100']) < 1e-8
    write_csv(out, 'lookup.csv', coverage)
    write_csv(out, 'lookup-by-position.csv', positional)
    write_csv(out, 'matched-transitions.csv', transitions)
    write_csv(out, 'river-frequency.csv', river)
    write_csv(out, 'paths.csv', paths)
    write_csv(out, 'strata.csv', strata)
    endpoint = read(source / 'endpoint.json')
    wall = metadata['completion']['at'] - metadata['launch']['at']
    summary = dict(status='verified', source_result_sha256=sha(source / 'results.json'),
        source_result_bytes=(source / 'results.json').stat().st_size, rows=results['rows'], models=results['models'],
        mass_audits=results['mass_audits'], final_hands=results['final_hands'], reproduction_hands=results['reproduction_hands'],
        direct_statistic=results['direct_statistic'], improvement_evidence=results['improvement_evidence'],
        no_automatic_adoption=True, endpoint=endpoint, costs=raw['costs'], evaluation_cost=raw['evaluation_cost'],
        root_wall_seconds=wall, measured_child_cpu_seconds=sum(v['cpu_seconds'] for v in metadata['stages'].values()),
        maximum_sampled_RSS_bytes=max(v['peak_RSS_bytes'] for v in metadata['resources'].values()),
        maximum_sampled_temperatures_c={k:max(v['max_temperatures_c'][k] for v in metadata['resources'].values()) for k in ['Package id 0','Thermistor 15']},
        pooled_singleton_matched_counts=totals, pooled_singleton_own_lookup=pooled_lookup,
        scope='One fixed training seed and host; pooled coverage is descriptive, not another strength test.',
        archive_status=metadata['archive_status'])
    (out / 'results.json').write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
    (out / 'completion.json').write_text(json.dumps(metadata, indent=2, sort_keys=True)+'\n')
    print(json.dumps({k:summary[k] for k in ['root_wall_seconds','measured_child_cpu_seconds','maximum_sampled_RSS_bytes','maximum_sampled_temperatures_c','pooled_singleton_matched_counts','pooled_singleton_own_lookup']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    summarize(args.source, args.out)
