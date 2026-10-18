import json
from pathlib import Path
import tempfile
import unittest

from scripts.analyze_nplayer_arena import PERMUTATIONS
from scripts.read_nplayer_fast_study import global_gate, paired_blocks
from scripts.run_nplayer_fast_study import cases
from scripts.run_nplayer_storage_benchmark import enforce,GIB


class StudyTests(unittest.TestCase):
    def fixture(self,root):
        for role in ['fast','production']:
            with (root/(role+'.jsonl')).open('w') as f:
                f.write(json.dumps(dict(seed=123,blocks=3,identity=dict(big_blind=100)))+'\n')
                for block in range(3):
                    for p,identities in enumerate(PERMUTATIONS):
                        value=6+2*block if role=='fast' else -2
                        rewards=[value if i==0 else -value//2 for i in identities]
                        f.write(json.dumps(dict(block=block,permutation=p,identities=identities,rewards=rewards,deck=list(range(52))))+'\n')

    def test_pairs_roles_and_retains_independent_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root)
            rows=list(paired_blocks(root/'fast.jsonl',root/'production.jsonl',123))
            self.assertEqual([r['advantage'] for r in rows],[4,5,6])

    def test_different_deals_and_partial_pairs_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root);p=root/'production.jsonl';lines=p.read_text().splitlines()
            row=json.loads(lines[1]);row['deck']=list(reversed(row['deck']));lines[1]=json.dumps(row);p.write_text('\n'.join(lines)+'\n')
            with self.assertRaisesRegex(ValueError,'deals'):list(paired_blocks(root/'fast.jsonl',p,123))
            self.fixture(root);p.write_text('\n'.join(p.read_text().splitlines()[:-1])+'\n')
            with self.assertRaisesRegex(ValueError,'length'):list(paired_blocks(root/'fast.jsonl',p,123))

    def test_global_failure_prevents_any_trace_readout(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'failure.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'failed'):global_gate(root)

    def test_fixed_matrix_and_configured_resource_limits(self):
        matrix=cases();self.assertEqual(len(matrix),12);self.assertEqual(sum(c['blocks']*6 for c in matrix),589824)
        for i in range(0,12,2):
            a,b=matrix[i:i+2];self.assertEqual(a['root'],b['root']);self.assertEqual((a['singleton'],a['pair']),(b['pair'],b['singleton']))
        row=dict(temperatures_c={'Package id 0':60,'Thermistor 15':65},available_ram_bytes=20*GIB,
            rss_bytes=60*GIB,swap_growth_bytes=0,free_disk_bytes=90_000_000_000)
        enforce(row,35_000_000_000,15000,max_seconds=25200,rss_limit=80*GIB)
        with self.assertRaises(RuntimeError):enforce(row,35_000_000_000,25200,max_seconds=25200,rss_limit=80*GIB)
        with self.assertRaises(RuntimeError):enforce(row,35_000_000_000,0)
