"""Checks that the decision service's network fallback is the paired arena's (docs/openpoker-client.md).

Replays every focal decision of the given arena traces (`nplayer_paired_arena`, network fallback
arm) through `nplayer_serve`. Each decision is sent with its deck, button, stacks and the action
record up to it. The service must report the same row status (positive mass, zero mass or
missing) and, where the network played, the same label probabilities bit for bit. The random
draw differs, since the service seeds each decision, so the chosen action isn't compared. Writes a
new JSON receipt and exits 1 on any difference.
"""
import argparse
import gzip
import json
from collections import Counter
from pathlib import Path

from src.play_api.native_decisions import NativeDecisions


def lines(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt') as f:
        for line in f:
            yield json.loads(line)


def check(native, path, policy, network, limit=None):
    trace = lines(path)
    header = next(trace)
    if header.get('focal_untrained_fallback') != f"network:{header['focal_network']['alias']}":
        raise ValueError(f'{path}: not a network fallback trace')
    if header['focal_network']['sha256'] != native.networks[network]['sha256']:
        raise ValueError(f'{path}: trace network differs from the service network')
    if header['policies'][0]['sha256'] != native.policies[policy]['sha256']:
        raise ValueError(f'{path}: trace policy differs from the service policy')
    counts, mismatches = Counter(), []
    for hand in trace:
        for k, lookup in enumerate(hand['lookups']):
            if lookup.get('identity') != 0:
                continue
            request = {'stacks': hand['stacks'], 'sb': hand['sb'], 'bb': hand['bb'], 'button': hand['button'],
                       'deck': hand['deck'], 'actions': hand['actions'][:k]}
            response = native.decide(request, hand['actors'][k], f'policy:{policy}', seed=0,
                                     view=lookup.get('view', 'native'), fallback=f'network:{network}')
            counts[lookup['status']] += 1
            same = response['status'] == lookup['status']
            if 'network' in lookup:
                same = same and 'network' in response and response['network']['p'] == lookup['network']['p']
                counts['network'] += 1
            else:
                same = same and 'network' not in response
            if not same:
                mismatches.append({'hand': hand['hand'], 'decision': k, 'arena': lookup,
                                   'service': {key: response.get(key) for key in ('status', 'network')}})
            if limit and sum(counts[s] for s in ('positive_mass', 'zero_mass', 'missing')) >= limit:
                return counts, mismatches
    return counts, mismatches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('traces', type=Path, nargs='+')
    parser.add_argument('--policy', nargs=3, required=True, metavar=('NAME', 'PATH', 'SHA256'))
    parser.add_argument('--mass', nargs=2, required=True, metavar=('DIR', 'SHA256'))
    parser.add_argument('--network', nargs=3, required=True, metavar=('NAME', 'PATH', 'SHA256'))
    parser.add_argument('--card-buckets', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='new JSON receipt; never overwritten')
    args = parser.parse_args()
    name, path, sha = args.policy
    net, net_path, net_sha = args.network
    native = NativeDecisions(card_buckets=args.card_buckets, policies={name: (Path(path), sha)},
                             masses={name: (Path(args.mass[0]), args.mass[1])}, networks={net: (Path(net_path), net_sha)})
    files, total, failures = [], Counter(), []
    try:
        for trace in args.traces:
            counts, mismatches = check(native, trace, name, net)
            files.append({'trace': str(trace), 'decisions': dict(counts), 'mismatches': len(mismatches)})
            total.update(counts)
            failures += mismatches[:20]
    finally:
        native.close()
    receipt = {'format': 'openpoker-fallback-parity-v1', 'policy': native.policies[name], 'network': native.networks[net],
               'traces': files, 'decisions': dict(total), 'mismatches': sum(f['mismatches'] for f in files),
               'first_mismatches': failures}
    receipt['passed'] = receipt['mismatches'] == 0 and total['network'] > 0
    with args.out.open('x') as f:
        f.write(json.dumps(receipt, indent=1) + '\n')
    print(json.dumps({k: receipt[k] for k in ('decisions', 'mismatches', 'passed')}))
    raise SystemExit(0 if receipt['passed'] else 1)


if __name__ == '__main__':
    main()
