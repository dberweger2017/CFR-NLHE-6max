"""Reproduce cost-only pilot intervals and local scenarios from the compact receipt."""
import argparse
import json
from pathlib import Path


def summarize(receipt):
    if receipt['status']['status'] != 'complete-cost-only' or receipt['failures']:
        raise ValueError('pilot did not complete cleanly')
    if receipt['qualification']['status'] != 'passed':
        raise ValueError('thread/resume qualification missing')
    expected = {'fixture-one', 'fixture-sixteen', 'fixture-resume', 'fixture-fresh',
                'pilot-100000000', 'pilot-200000000', 'pilot-500000000'}
    if set(receipt['measurements']) != expected or any(
            value['result'] is None or value['result']['returncode'] != 0
            or value['resources']['peak_rss_bytes'] <= 0
            for value in receipt['measurements'].values()):
        raise ValueError('missing successful stages or meaningful RSS')
    fixtures = receipt['measurements']
    if (fixtures['fixture-one']['summary']['sha256'] != fixtures['fixture-sixteen']['summary']['sha256']
            or fixtures['fixture-resume']['summary']['sha256'] != fixtures['fixture-fresh']['summary']['sha256']):
        raise ValueError('thread/resume fixture checkpoints differ')
    result = receipt['results']
    rows = result['rows']
    if result['status'] != 'complete-cost-only' or len(rows) != 3:
        raise ValueError('wrong endpoint count')
    records = []
    previous_nodes = previous_entries = 0
    for row, target in zip(rows, (100_000_000, 200_000_000, 500_000_000)):
        counts = row['counts']
        identity = row['identity']
        measurement = receipt['measurements'][row['stage']]
        if (counts['nodes'] < target or counts['nodes'] <= previous_nodes
                or row['entries'] <= previous_entries or row['entries'] >= 150_000_000
                or row['stop_reason'] != 'nodes' or row['frozen_at'] is not None
                or counts['discarded_keys'] or counts['discarded_visits']
                or measurement['result']['returncode'] != 0
                or identity['players'] != 3 or identity['stacks'] != [10000] * 3
                or identity['small_blind'] != 50 or identity['big_blind'] != 100):
            raise ValueError('invalid target, game, capacity or completion evidence')
        seconds = row['training_seconds']
        if seconds <= 0 or abs(seconds - (row['elapsed_seconds'] - row['save_seconds'])) > 1e-6:
            raise ValueError('invalid active training accounting')
        records.append(dict(target=target, nodes=counts['nodes'], iteration=row['iteration'],
            entries=row['entries'], added_nodes=counts['nodes'] - previous_nodes,
            keys_per_node=(row['entries'] - previous_entries) / (counts['nodes'] - previous_nodes),
            training_seconds=seconds, nodes_per_second=(counts['nodes'] - previous_nodes) / seconds,
            save_seconds=row['save_seconds'], wall_seconds=row['wall_seconds'],
            other_wall_seconds=row['wall_seconds'] - row['elapsed_seconds'],
            child_cpu_seconds=row['child_cpu_seconds'],
            sampled_peak_rss_bytes=row['sampled_peak_rss_bytes'],
            checkpoint_bytes=row['checkpoint_bytes'], checkpoint=row['checkpoint'], sha256=row['sha256']))
        previous_nodes, previous_entries = counts['nodes'], row['entries']
    last = records[-1]
    scenarios = {}
    for target in (3_000_000_000, 10_000_000_000):
        scenarios[str(target)] = last['entries'] + last['keys_per_node'] * (target - last['nodes'])
    if any(abs(scenarios[str(target)] - result[key]) > 1e-5 for target, key in
           [(3_000_000_000, 'linear_entries_at_3b'), (10_000_000_000, 'linear_entries_at_10b')]):
        raise ValueError('local scenario does not reproduce')
    return dict(rows=records, linear_entries=scenarios,
        linear_150m_crossing_nodes=last['nodes'] + (150_000_000 - last['entries']) / last['keys_per_node'],
        pilot_elapsed_seconds=result['elapsed_seconds'],
        active_training_seconds=sum(r['training_seconds'] for r in records),
        save_seconds=sum(r['save_seconds'] for r in records),
        measured_stage_wall_seconds=sum(r['wall_seconds'] for r in records),
        measured_child_cpu_seconds=sum(r['child_cpu_seconds'] for r in records),
        retained_checkpoint_bytes=sum(r['checkpoint_bytes'] for r in records),
        full_campaign_admitted=False,
        scenario_scope='one early trajectory; last-interval linear scenarios, not bounds or saturation forecasts')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(json.loads(args.receipt.read_text())), indent=2))
