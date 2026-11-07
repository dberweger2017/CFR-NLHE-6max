import json

import numpy as np
import pytest

from scripts import neural_policy_samples as nps


def write(path, teachers=2, features=5, records=3, record_bytes=None):
    d = nps.dtype(teachers, features)
    header = {'format': nps.FORMAT, 'layout_sha256': 'ab' * 32, 'feature_count': features,
              'record_bytes': record_bytes or d.itemsize, 'teachers': [{'alias': f't{i}'} for i in range(teachers)]}
    h = json.dumps(header).encode()
    r = np.zeros(records, d)
    r['hand'] = np.arange(records)
    r['legal_mask'] = 0b011010  # check, min raise, pot raise
    r['features'] = np.array([[0, 51, 102, 204, 255]] * records, dtype=np.uint8)
    r['t0_status'] = [0, 2, 0]
    r['t0_p'][0] = [0, 65535, 0, 0, 0, 0]
    with open(path, 'wb') as f:
        f.write(nps.MAGIC + len(h).to_bytes(8, 'little') + h + r.tobytes())
    return d


def test_records_round_trip_through_the_memory_map(tmp_path):
    path = tmp_path / 's.bin'
    d = write(path)
    s = nps.load(path, layout_sha256='ab' * 32)
    assert len(s) == 3 and d.itemsize == 12 + 2 * 13 + 5
    assert np.allclose(s.features()[0], [0, 0.2, 0.4, 0.8, 1.0])
    p, status = s.teacher(0)
    assert status.tolist() == [0, 2, 0] and p[0].tolist() == [0, 1, 0, 0, 0, 0]
    assert s.legal()[0].tolist() == [False, True, False, True, True, False]


def test_layout_and_size_mismatches_are_refused(tmp_path):
    path = tmp_path / 's.bin'
    write(path)
    with pytest.raises(ValueError, match='layout'):
        nps.load(path, layout_sha256='cd' * 32)
    write(tmp_path / 'bad.bin', record_bytes=99)
    with pytest.raises(ValueError, match='record size'):
        nps.load(tmp_path / 'bad.bin')
    with open(path, 'ab') as f:
        f.write(b'\0')
    with pytest.raises(ValueError, match='truncated'):
        nps.load(path)
