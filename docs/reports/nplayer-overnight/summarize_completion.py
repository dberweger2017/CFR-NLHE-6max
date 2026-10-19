"""Validate compact PR346 receipts and derive tables, without playing new hands."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

from scipy.stats import t

SEEDS = (2026101541, 2026101542, 2026101543)


def write_csv(out, name, rows):
    with (out / name).open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def summarize(receipt, source_results, out):
    d = json.loads(receipt.read_text())
    result = d['results']
    assert hashlib.sha256(source_results.read_bytes()).hexdigest() == d['results_sha256']
    assert json.loads(source_results.read_text()) == result
    final_root = d['roots'][Path(d['root']).name]
    assert final_root['metadata']['status.json']['status'] == 'complete'
    assert 'failure.json' not in final_root['metadata']
    assert 'preservation-failure.json' not in final_root['metadata']
    assert result['status'] == 'settled'
    assert result['final_hands'] == result['reproduction_hands'] == 1769472
    assert d['verified']['status'] == 'passed' and d['verified']['cases'] == 36
    assert d['verified']['hands'] == 1769472
    assert len(d['cases']) == len(d['manifest']['cases']) == 36
    assert len(result['rows']) == 18
    for stage in ('final-evaluation', 'readout'):
        assert final_root['stages'][stage]['returncode'] == 0
    for case in d['manifest']['cases']:
        pair = d['cases'][case['name']]
        a, b = pair['result'], pair['replay']
        assert a['case'] == case and a['status'] == b['status'] == 'passed'
        assert a['hands'] == b['hands'] == case['blocks'] * 6 == 49152
        assert a['trace_sha256'] == b['trace_sha256']
    assert result['consistent_gain'] == all(
        row['score']['lower95_bb100'] > 0 for row in result['rows'] if row['group'] == 'same')
    assert result['cross_noninferiority'] == all(
        row['score']['lower95_bb100'] > -5 for row in result['rows'] if row['group'] == 'cross')

    strengths, seats, coverage, stages, models = [], [], [], [], []
    for row in result['rows']:
        score = row['score']
        left = statistics.mean(x['mean_bb100'] for x in row['fast_by_position'])
        right = statistics.mean(x['mean_bb100'] for x in row['production_by_position'])
        scale = 1 if row['group'] == 'bot' else 2
        assert math.isclose((left - right) / scale, score['mean_bb100'], abs_tol=1e-10)
        for tail, sign in [('lower95_bb100', -1), ('upper95_bb100', 1)]:
            expected = score['mean_bb100'] + sign * t.ppf(.975, 8191) * score['standard_error_bb100']
            assert math.isclose(score[tail], expected, abs_tol=1e-9)
        if row['group'] == 'bot':
            for tail, sign in [('lower_family95', -1), ('upper_family95', 1)]:
                expected = score['mean_bb100'] + sign * t.ppf(1 - .05 / 24, 8191) * score['standard_error_bb100']
                assert math.isclose(score[tail], expected, abs_tol=1e-9)
        strengths.append(dict(group=row['group'], seed=row['seed'], bot=row['bot'], root=row['root'],
            blocks=8192, final_singleton_mean_bb100=left, anchor_singleton_mean_bb100=right, **score))
        for role, prefix in [('final', 'fast'), ('anchor', 'production')]:
            for dimension in ('seat', 'position'):
                for i, values in enumerate(row[f'{prefix}_by_{dimension}']):
                    seats.append(dict(group=row['group'], seed=row['seed'], bot=row['bot'],
                        role=role, dimension=dimension, index=i, **values))
    for case in d['manifest']['cases']:
        native = d['cases'][case['name']]['result']['coverage'][0]
        assert native['hands'] == 49152 and native['blocks'] == 8192
        for i, model in enumerate([case['singleton'], case['pair'], case['pair']]):
            if model.startswith('bot='):
                continue
            for street, (decisions, missing) in enumerate(zip(native['decisions_by_identity_street'][i],
                    native['misses_by_identity_street'][i])):
                assert 0 <= missing <= decisions
                coverage.append(dict(case=case['name'], model=model, street=street,
                    decisions=decisions, missing=missing))
    for root_name, root in d['roots'].items():
        for name, stage in root['stages'].items():
            stages.append(dict(root=root_name, stage=name, returncode=stage.get('returncode'),
                wall_seconds=stage.get('wall_seconds'), child_cpu_seconds=stage.get('cpu_seconds'),
                **stage['resource_aggregate']))
    for seed in SEEDS:
        model = result['models'][f'final-{seed}']
        root = d['roots'][Path(model['path']).parent.name]
        name = f'training-{seed}' + ('-thermal100' if seed == SEEDS[0] else '-noswap' if seed == SEEDS[2] else '')
        stage = root['stages'][name]
        trained = [e for e in stage['events'] if e.get('event') == 'trained'][-1]
        checkpoints = [e for e in stage['events'] if e.get('event') == 'checkpoint']
        audit = root['stages'][f'audit-{seed}']['native_output']
        assert stage['returncode'] == root['stages'][f'export-{seed}']['returncode'] == root['stages'][f'audit-{seed}']['returncode'] == 0
        assert trained['nodes'] >= 30000000000 and trained['entries'] < 150000000
        assert trained['counts']['discarded_keys'] == trained['counts']['discarded_visits'] == 0
        assert audit['status'] == 'passed' and audit['rows'] == trained['entries']
        assert model['sha256'] == audit['policy_sha256']
        assert model['checkpoint_sha256'] == audit['checkpoint_sha256'] == checkpoints[-1]['sha256']
        prefix = d['failed_training'][f'training-{seed}']['events'][0] if seed != SEEDS[1] else None
        active = trained['active_seconds'] + (prefix['active_seconds'] if prefix else 0)
        start = [2949726632, 3003671483, 2910499919][SEEDS.index(seed)]
        train_peak = max(v for k, v in stage['sampled_peak_rss_by_phase'].items() if k.startswith('train/'))
        save_peak = max(v for k, v in stage['sampled_peak_rss_by_phase'].items() if k.startswith('save/'))
        models.append(dict(seed=seed, nodes=trained['nodes'], iteration=trained['iteration'], entries=trained['entries'],
            lineage_active_seconds=active, lineage_nodes_per_second=(trained['nodes'] - start) / active,
            training_peak_rss_bytes=train_peak, save_peak_rss_bytes=save_peak,
            final_save_seconds=checkpoints[-1]['save_seconds'], **model))
    out.mkdir(parents=True, exist_ok=False)
    # Optional family-adjusted bounds are empty for the direct/cross contrasts.
    fields = list(dict.fromkeys(k for row in strengths for k in row))
    write_csv(out, 'strength.csv', [{k: row.get(k) for k in fields} for row in strengths])
    for name, rows in [('seats-and-positions.csv', seats), ('coverage.csv', coverage),
                       ('stage-costs.csv', stages), ('models-and-training.csv', models)]:
        write_csv(out, name, rows)
    return models


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    parser.add_argument('source_results', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(summarize(args.receipt, args.source_results, args.out), indent=2))
