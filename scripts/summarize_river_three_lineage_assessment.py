"""Validate compact PR398 receipts and publish existing readout; no poker execution."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    parser.add_argument('--supplement', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text())
    for name, body in receipt['files'].items():
        if hashlib.sha256(body.encode()).hexdigest() != receipt['sha256'][name]:
            raise ValueError('changed receipt: ' + name)
    def read(name):
        return json.loads(receipt['files'][name])
    result = read('main-v1/readout/results.json')
    stages = read('main-v1/stage-costs.json')
    seeds = [2026101935003, 202610200601, 202610200602]
    assert read('main-v1/status.json')['status'] == 'complete'
    assert len(stages) == 9 and all(x['returncode'] == 0 for x in stages)
    assert not any(name.endswith('failure.json') for name in receipt['files'])
    assert result['status'] == 'settled' and len(result['lineups']) == 6
    assert result['initial_hands'] == result['reproduction_hands'] == 221184
    proofs = {}
    components = {}
    for seed in seeds:
        for phase in ('qualification', 'measurement'):
            name = f'main-v1/{phase}/{seed}/verified.json'
            proof = read(name)
            assert proof['status'] == 'passed' and proof['no_exclusions']
            assert proof['all_value_profile_work_reproduced']
            assert proof['solver_advances'] == proof['profile_reconstructions'] == 0
            hands = 73728 if phase == 'measurement' else 96
            assert proof['initial_hands'] == proof['reproduction_hands'] == hands
            assert sum(r['independent_replay']['hands'] for r in proof['records']) == hands
            assert all(r['independent_replay']['status'] == 'passed' for r in proof['records'])
            proofs[name] = {'sha256': receipt['sha256'][name], 'proof': proof}
            if phase == 'measurement':
                assert receipt['sha256'][name] in result['proof_sha256s'].values()
                components[str(seed)] = read(f'main-v1/{phase}/{seed}/costs.json')
    assert read('budget-bridge/status.json')['status'] == 'not-needed-original-complete'
    assert sum(x['gate_passed'] for x in result['lineups']) == 1
    assert not any(x['material_harm_established'] for x in result['lineups'])
    assert result['decision']['project_decision'] == 'defer-frozen-candidate-resume-blueprint-progress'
    supplement = json.loads(args.supplement.read_text())
    assert sum(x['roots'] for x in supplement['expectation_costs'].values()) == 2 * sum(
        x['counts']['mode/root'] for x in result['lineups'])
    args.out.mkdir(parents=True, exist_ok=False)
    def write(name, value):
        (args.out/name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    (args.out/'results.json').write_text(receipt['files']['main-v1/readout/results.json'])
    preparation = read('preparation/stage-costs.json')
    measurement = [x for x in stages if x['phase'].startswith('measure-') or x['phase'] == 'readout']
    batches = [b for c in components.values() for b in c['batches'].values()]
    costs = {
        'preparation': read('preparation/status.json'), 'preparation_stages': preparation,
        'main_stages': stages, 'measurement_components': components,
        'resources': receipt['resources'],
        'main_supervised_stage_wall_seconds': sum(x['wall_seconds'] for x in stages),
        'preparation_and_main_child_cpu_seconds': sum(x['user_cpu_seconds']+x['system_cpu_seconds'] for x in preparation+stages),
        'measurement_and_readout_wall_seconds': sum(x['wall_seconds'] for x in measurement),
        'measurement_and_readout_child_cpu_seconds': sum(x['user_cpu_seconds']+x['system_cpu_seconds'] for x in measurement),
        'measurement_load_seconds': sum(x['startup']['model_and_k50_load_seconds'] for x in batches),
        'measurement_play_write_seconds': sum(x['play_and_write_seconds'] for x in batches),
        'measurement_verification_seconds': sum(x['verification_seconds'] for x in components.values()),
        'expectation_evaluation_seconds_included_in_play': sum(x['total_evaluation_seconds'] for x in supplement['expectation_costs'].values()),
        'expectation_cost_receipt': supplement['expectation_costs'],
        'excludes_archive_and_publication_cost': True,
        'main_admission': read('main-v1/main-admission.json')}
    write('costs.json', costs)
    write('provenance.json', {'source': receipt['source'], 'receipt_sha256': hashlib.sha256(args.receipt.read_bytes()).hexdigest(),
        'source_manifest_sha256': receipt['source_manifest_sha256'], 'file_sha256s': receipt['sha256'],
        'launch': read('main-v1/launch.json'), 'model_pins': read('main-v1/model-pins.json'),
        'native_identity': read('main-v1/native-identity.json'), 'proofs': proofs,
        'controller_completion': read('preparation/controller-completion.json'),
        'budget_bridge': read('budget-bridge/status.json'), 'originals_retained': True})
    write('archive.json', {'status': 'pending-blocked', 'error': supplement['archive-closeout-v1/failure.json'],
        'status_receipt': supplement['archive-closeout-v1/status.json'], 'original_root': receipt['root'],
        'planned_cache': '/research/PR-398-river-three-lineage-assessment/',
        'planned_drive': 'gdrive:PR-398-river-three-lineage-assessment/',
        'copy_upload_or_drive_acceptance_claimed': False, 'originals_retained': True})
    def csvfile(name, header, rows):
        with (args.out/name).open('w') as f:
            writer = csv.writer(f, lineterminator='\n'); writer.writerow(header); writer.writerows(rows)
    rows=[]; tails=[]; seats=[]
    for panel in result['lineups']:
        s=panel['integrated']; c=panel['counts']; seed=panel['focal_seed']; lineup=panel['lineup']
        assert s['blocks'] == (2048 if lineup == 'trained' else 4096)
        rows.append([seed, panel['trained_peer_seed'], lineup, s['blocks'], s['mean_bb100'], *s['pointwise95_bb100'],
            s['family_one_sided95_lower_bb100'], s['family_one_sided95_upper_bb100'], panel['gate_margin_bb100'],
            panel['gate_passed'], panel['material_harm_established'], panel['sampled']['mean_bb100'], panel['variance_ratio'],
            c['mode/root'], c['root_installed'], c.get('off_tree_hands',0), panel['root_latency_seconds']['median']])
        for tail in panel['tails']:
            example=tail['examples'][0] if tail['examples'] else {}
            tails.append([seed,lineup,tail['block'],tail['contrast_bb100'],tail['centered_square_share'],tail['uncentered_square_share'],
                example.get('root_id'),example.get('expected_on_minus_off_bb')])
        for seat, value in panel['per_seat'].items():
            seats.append([seed,lineup,seat,value['integrated_descriptive']['mean_bb100'],value['sampled_descriptive']['mean_bb100'],False])
    csvfile('lineups.csv',['focal_seed','peer_seed','lineup','blocks','expected_mean_bb100','pointwise95_low','pointwise95_high',
        'family_one_sided95_lower','family_one_sided95_upper','gate_margin_bb100','gate_passed','material_harm_established',
        'sampled_mean_bb100','variance_ratio','root_attempts','installed','off_tree_hands','root_latency_median_seconds'],rows)
    assert len(tails)==36 and len(seats)==18
    csvfile('tails.csv',['focal_seed','lineup','block','contrast_bb100','centered_square_share','uncentered_square_share','largest_root_id','largest_root_contrast_bb'],tails)
    csvfile('per-seat.csv',['focal_seed','lineup','physical_seat','expected_mean_bb100','sampled_mean_bb100','confirmatory'],seats)
    print(json.dumps({k:v for k,v in costs.items() if isinstance(v,(float,int))},indent=2))


if __name__ == '__main__':
    main()
