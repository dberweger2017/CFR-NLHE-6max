"""Agreement between the network and the table at run 1's focal decisions (arm 1 traces)."""
import glob, gzip, json, sys
from multiprocessing import Pool
STREETS = ['preflop', 'flop', 'turn', 'river']

def one(path):
    table, field = path.split('/')[-2], path.split('/')[-1].split('-a1.')[0]
    c = {s: [0, 0, 0.0] for s in STREETS}  # focal decisions, positive-mass, sum TV
    with gzip.open(path, 'rt') as f:
        next(f)
        for line in f:
            h = json.loads(line)
            focal = [i for i, x in enumerate(h['identities']) if x == 0]
            for lk in h['lookups']:
                if lk.get('identity') != 0 or 'network' not in lk:
                    continue
                s = STREETS[lk['street']]
                c[s][0] += 1
                if lk['status'] == 'positive_mass':
                    c[s][1] += 1
                    c[s][2] += 0.5 * sum(abs(a - b) for a, b in zip(lk['network']['p'], lk['row']))
    return table, field, c

if __name__ == '__main__':
    files = sorted(glob.glob(sys.argv[1] + '/arena/b*/*/*-a1.jsonl.gz'))
    out = {}
    with Pool(16) as p:
        for table, field, c in p.imap_unordered(one, files):
            t = out.setdefault(table, {}).setdefault(field, {s: [0, 0, 0.0] for s in STREETS})
            for s in STREETS:
                for k in range(3):
                    t[s][k] += c[s][k]
    res = {}
    for table, fields in sorted(out.items()):
        for field, st in sorted(fields.items()):
            row = {}
            for s in STREETS + ['all']:
                n, m, tv = [sum(st[x][k] for x in STREETS) for k in range(3)] if s == 'all' else st[s]
                row[s] = {'focal_decisions': n, 'differ_share': m / n if n else None, 'mean_tv_where_differ': tv / m if m else None}
            res.setdefault(table, {})[field] = row
    json.dump({'format': 'neural-policy-everywhere-agreement-v1', 'run': 1, 'source': 'arm 1 traces, all banks',
               'differ_share': 'share of focal decisions where arm 0 plays a positive-mass row (arm 1 plays the network)',
               'tv': 'total variation between the network and the row at those decisions', 'tables': res}, sys.stdout, indent=1)
