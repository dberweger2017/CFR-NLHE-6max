import gzip
import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_nplayer_policy import audit as serial, sha
from scripts.audit_nplayer_policy_parallel import audit


class ParallelAuditTests(unittest.TestCase):
    def fixture(self, root, corrupt=None):
        cp, policy = root / 'checkpoint.gz', root / 'policy.gz'
        rows = [[f'{i:032x}', i % 3, i % 4, 6, i, [-1., 2.], [float(i), 2.]] for i in range(6)]
        if corrupt == 'duplicate':
            rows[2][0] = rows[1][0]
        header = dict(format='nplayer-cfr-v1', game=dict(players=3), players=3,
                      entries=6, last_average_street=3, counts=dict(decisions=[20]*4, missing=[1]*4))
        with gzip.open(cp, 'wt') as f:
            f.write(json.dumps(header)+'\n')
            for row in rows: f.write(json.dumps(row)+'\n')
        ph = dict(format='nplayer-policy-v1', identity=header['game'], players=3, entries=6,
                  last_average_street=3, strategy='average', continuation='none', source_checkpoint_sha256=sha(cp))
        if corrupt == 'parent': ph['source_checkpoint_sha256']='0'*64
        with gzip.open(policy, 'wt') as f:
            f.write(json.dumps(ph)+'\n')
            for row in rows[:-1] if corrupt == 'missing' else rows:
                p=[x/sum(row[6]) for x in row[6]]
                if corrupt == 'probability': p=[.7,.3]
                f.write(json.dumps(row[:4]+[p])+'\n')
        return cp, policy

    def test_parallel_chunks_equal_independent_serial_audit(self):
        with tempfile.TemporaryDirectory() as d:
            cp, policy=self.fixture(Path(d))
            self.assertEqual(audit(cp,policy,workers=2,chunk_rows=2),serial(cp,policy))

    def test_rejects_wrong_probabilities_parent_missing_rows_and_cross_chunk_duplicate(self):
        for kind in ['probability','parent','missing','duplicate']:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
                cp,policy=self.fixture(Path(d),kind)
                with self.assertRaises(ValueError):audit(cp,policy,workers=2,chunk_rows=2)
