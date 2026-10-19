"""Summarize all nine verified storage benchmark milestones."""
import argparse
import csv
import json
from pathlib import Path

from scripts.run_nplayer_storage_benchmark import TARGETS, compare


def summarize(root):
    rows, totals = [], []
    baseline = None
    baseline_rows = {}
    for arm in ('baseline', 'compact', 'parallel'):
        result = json.loads((root / 'measurements' / ('arm-' + arm) / 'result.json').read_text())
        if result['returncode'] != 0:
            raise ValueError('cannot summarize a failed arm as complete')
        if baseline is None:
            baseline = result
            compare(baseline, baseline)
        else:
            compare(baseline, result)
        events = result['events']
        if not any(e.get('event') == 'complete' for e in events):
            raise ValueError('missing completion marker')
        peaks = result['sampled_peak_rss_by_phase']
        load = next(e['seconds'] for e in events if e.get('event') == 'loaded')
        for target in TARGETS:
            by_kind = {e['event']:e for e in events if e.get('target') == target}
            train, save, verified = [by_kind[k] for k in ('trained', 'saved', 'verified')]
            row = dict(arm=arm, target=target, actual_nodes=train['nodes'],
                entries=train['entries'], iteration=train['iteration'],
                training_seconds=train['seconds'], nodes_per_second=train['nodes_per_second'],
                sampled_training_rss_bytes=peaks.get(f'train/{target}', 0),
                save_seconds=save['seconds'], sampled_saving_rss_bytes=peaks.get(f'save/{target}', 0),
                checkpoint_bytes=save['bytes'], checkpoint_sha256=verified['sha256'],
                compressed_save_mb_per_second=save['bytes']/1_000_000/save['seconds'],
                verification_seconds=verified['seconds'])
            if not row['sampled_training_rss_bytes'] or not row['sampled_saving_rss_bytes']:
                raise ValueError('missing phase memory samples')
            if arm == 'baseline':
                baseline_rows[target] = row
            original = baseline_rows[target]
            row.update(training_speed_ratio=row['nodes_per_second']/original['nodes_per_second'],
                save_speed_ratio=original['save_seconds']/row['save_seconds'],
                training_rss_ratio=row['sampled_training_rss_bytes']/original['sampled_training_rss_bytes'],
                saving_rss_ratio=row['sampled_saving_rss_bytes']/original['sampled_saving_rss_bytes'],
                checkpoint_identical=row['checkpoint_sha256']==original['checkpoint_sha256'])
            rows.append(row)
        totals.append(dict(arm=arm, load_seconds=load, wall_seconds=result['wall_seconds'],
            cpu_seconds=result['cpu_seconds'], sampled_peak_rss_bytes=max(peaks.values()),
            training_seconds=sum(r['training_seconds'] for r in rows if r['arm']==arm),
            saving_seconds=sum(r['save_seconds'] for r in rows if r['arm']==arm)))
    return dict(status='complete-identical', rows=rows, totals=totals,
        limitations=['One fixed seed, fixed baseline→compact→parallel order; no repetition-based uncertainty.',
                     'RSS sampled every 0.5 seconds; transient peaks may be missed.',
                     'Compressed checkpoint bytes/s is not uncompressed formatting throughput.',
                     'No playing-strength or release conclusion; no automatic merge.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.root)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    with (args.out/'comparison.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(result['rows'][0]))
        writer.writeheader(); writer.writerows(result['rows'])
    print(json.dumps(result['totals'], indent=2))


if __name__ == '__main__':
    main()
