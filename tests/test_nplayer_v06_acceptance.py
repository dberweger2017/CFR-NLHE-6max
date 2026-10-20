"""Prospective counts, block statistics and safe copy/restore refusal cases."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import nplayer_v06_acceptance as study
from scripts import nplayer_inference_validation as io


class AcceptanceTest(unittest.TestCase):
    def test_fixed_matrix_and_pairing(self):
        rows=study.matrix();self.assertEqual(len(rows),36)
        self.assertEqual(sum(r['blocks']*6 for r in rows),2635776)
        self.assertEqual(len({r['root'] for r in rows}),30)
        self.assertEqual(len({r['name'] for r in rows}),36)
        self.assertEqual(len(study.phases()),9)
        for gate in ('direct','cross'):
            for seed in study.SEEDS:
                a,b=[r for r in rows if r['gate']==gate and r['seed']==seed]
                self.assertEqual((a['root'],a['blocks']),(b['root'],b['blocks']))
        for r in rows:
            if r['gate']=='script-profit' and r['opponent'].startswith('trained-'):
                self.assertEqual(r['players'][1],'baseline')
        self.assertEqual(sum(r['blocks']*6 for r in study.matrix(True)),432)
        self.assertFalse({r['root'] for r in rows}&{r['root'] for r in study.matrix(True)})

    def test_cyclic_semantics(self):
        rows=[r for r in study.matrix() if r['gate']=='cross']
        for i,seed in enumerate(study.SEEDS):
            a,b=rows[i*2:i*2+2];other=study.SEEDS[(i+1)%3]
            self.assertEqual(a['singleton'],f'candidate-{seed}')
            self.assertEqual(b['singleton'],f'baseline-{seed}')
            self.assertEqual(a['pair'],f'baseline-{other}')
            self.assertEqual(b['pair'],a['pair'])

    def test_frozen_configuration_source_and_binary_refusals(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);binary=d/'binary';binary.write_bytes(b'qualified')
            pins={name:dict(path=str(binary),sha256=io.sha(binary)) for name in study.BINARY_NAMES}
            c=dict(authorization='owner-20261020-fresh-v06-acceptance',cases=study.matrix(True),smoke=True,
                threads=8,family=30,cross_margin_bb100=-5,resource_policy=study.thermal.RESOURCE_POLICY,
                source_files={'script':'abc'},binaries=pins,python='/python',environment={'engine':'pinned'})
            with patch.object(study,'source_pins',return_value={'script':'abc'}),patch.object(study.thermal,'python_environment',return_value=('/python',{'engine':'pinned'})):
                study.validate_config(c)
                for field,value in [('threads',16),('family',3),('cross_margin_bb100',-50),('source_files',{}),('cases',[])]:
                    bad=deepcopy(c);bad[field]=value
                    with self.assertRaises(ValueError):study.validate_config(bad)
                binary.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'binary changed'):study.validate_config(c)

    def test_one_sided_family_bound(self):
        from scipy.stats import t
        values=[0.,10.,20.,30.]
        r=study.lower_bound(values,-5)
        self.assertAlmostEqual(r['lower_simultaneous95_bb100'],15.-float(t.ppf(1-.05/30,3))*r['standard_error_bb100'])
        self.assertLess(r['lower_simultaneous95_bb100'],r['lower95_bb100'])
        self.assertFalse(r['passed'])
        self.assertTrue(study.lower_bound([10.,10.,10.],0)['passed'])
        self.assertFalse(study.lower_bound([-5.,-5.,-5.],-5)['passed'])
        with self.assertRaises(ValueError):study.lower_bound([float('nan'),1.],0)

    def test_copy_stage_restore_and_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);root=d/'root';root.mkdir();cache=d/'cache';original=d/'protected';original.write_bytes(b'abc')
            target=root/'inputs'/'model.bin';io.copy_pinned(original,target,io.sha(original))
            io.write(root/'config.json',dict(cache=str(cache)))
            model={'x':dict(path=str(target),sha256=io.sha(original))}
            study.owned_stage(root,cache,[target]);self.assertTrue(target.is_symlink())
            study.restore_owned(root,['x'],model);self.assertFalse(target.is_symlink())
            study.owned_stage(root,cache,[target]);self.assertTrue(target.is_symlink())
            self.assertEqual(original.read_bytes(),b'abc')
            study.restore_owned(root,['x'],model);target.write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'cache/partial differs'):study.owned_stage(root,cache,[target])
            self.assertEqual(target.read_bytes(),b'bad');self.assertEqual((cache/'inputs/model.bin').read_bytes(),b'abc')
            with self.assertRaises(ValueError):study.owned_stage(root,cache,[original])

    def test_wrong_copy_and_foreign_link_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);root=d/'root';root.mkdir();p=d/'source';p.write_bytes(b'123')
            bad=root/'partial'
            with self.assertRaises(ValueError):io.copy_pinned(p,bad,'0'*64)
            self.assertEqual(bad.read_bytes(),b'123')
            with self.assertRaises(FileExistsError):io.copy_pinned(p,bad,io.sha(p))
            link=root/'link';link.symlink_to(p)
            with self.assertRaises(ValueError):study.owned_stage(root,d/'cache',[link])
            self.assertEqual(p.read_bytes(),b'123')

    def test_readout_refuses_missing_barrier_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(FileNotFoundError):study.verify_barrier(root,dict(smoke=True))
            io.write(root/'failure.json',dict(error='terminal'))
            with self.assertRaisesRegex(ValueError,'terminal failure'):study.verify_barrier(root,dict(smoke=True))


if __name__=='__main__':unittest.main()
