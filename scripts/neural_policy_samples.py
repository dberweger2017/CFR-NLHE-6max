"""Read `nplayer_features` sample files (docs/neural-policy-data.md) as NumPy arrays.

A file is the magic `NPFEAT01`, a little-endian u64 header length, a JSON header and then
fixed-size records. `load` checks the header and memory-maps the records, so a multi-gigabyte file
costs no reading until it's used:

    samples = load(path)
    x = samples.features()          # float32, (n, feature_count), each in [0, 1]
    p, status = samples.teacher(0)  # float32 (n, 6) strategy and uint8 (n,) status per sample

Status 0 is a positive-mass (trained) row, 1 a zero-mass row and 2 no row; only status 0 carries
a strategy.
"""
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

MAGIC = b'NPFEAT01'
FORMAT = 'nplayer-feature-samples-v1'
ACTIONS = 6
POSITIVE, ZERO_MASS, MISSING = 0, 1, 2


def dtype(teachers, features):
    fields = [('hand', '<u4'), ('decision', '<u2'), ('players', 'u1'), ('street', 'u1'), ('actor_slot', 'u1'),
              ('seat_kind', 'u1'), ('legal_mask', 'u1'), ('chosen', 'u1')]
    for t in range(teachers):
        fields += [(f't{t}_status', 'u1'), (f't{t}_p', '<u2', (ACTIONS,))]
    fields.append(('features', 'u1', (features,)))
    return np.dtype(fields)


@dataclass
class Samples:
    header: dict
    records: np.ndarray

    def __len__(self):
        return len(self.records)

    def features(self, rows=slice(None)):
        return self.records['features'][rows].astype(np.float32) / 255.0

    def teacher(self, index, rows=slice(None)):
        r = self.records[rows]
        return r[f't{index}_p'].astype(np.float32) / 65535.0, r[f't{index}_status']

    def legal(self, rows=slice(None)):
        """(n, 6) bool: which menu labels are legal."""
        mask = self.records['legal_mask'][rows]
        return (mask[:, None] >> np.arange(ACTIONS)) & 1 == 1


def load(path, layout_sha256=None):
    with open(path, 'rb') as f:
        if f.read(8) != MAGIC:
            raise ValueError(f'{path}: not a feature sample file')
        size = int.from_bytes(f.read(8), 'little')
        header = json.loads(f.read(size))
    if header['format'] != FORMAT:
        raise ValueError(f'{path}: format {header["format"]}')
    if layout_sha256 is not None and header['layout_sha256'] != layout_sha256:
        raise ValueError(f'{path}: feature layout differs')
    d = dtype(len(header['teachers']), header['feature_count'])
    if d.itemsize != header['record_bytes']:
        raise ValueError(f'{path}: record size {header["record_bytes"]} != {d.itemsize}')
    offset = 16 + size
    count, extra = divmod(Path(path).stat().st_size - offset, d.itemsize)
    if extra:
        raise ValueError(f'{path}: truncated record')
    records = np.memmap(path, dtype=d, mode='r', offset=offset, shape=(count,)) if count else np.zeros(0, d)
    return Samples(header, records)


def main():
    for path in sys.argv[1:]:
        s = load(path)
        status = [np.bincount(s.teacher(t)[1], minlength=3).tolist() for t in range(len(s.header['teachers']))]
        print(json.dumps({'path': path, 'samples': len(s), 'features': s.header['feature_count'],
                          'teacher_status': status}))


if __name__ == '__main__':
    main()
