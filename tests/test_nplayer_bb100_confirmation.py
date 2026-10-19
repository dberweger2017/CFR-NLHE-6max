import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import nplayer_bb100_confirmation as study
from scripts import run_nplayer_storage_benchmark as guard


class ConfirmationTests(unittest.TestCase):
    def test_matrix_is_fixed_disjoint_and_paired(self):
        roots=[]
        for index in range(2):
            rows=study.matrix(index)
            self.assertEqual(len(rows),18)
            for a,b in zip(rows[::2],rows[1::2]):
                self.assertEqual(a['root'],b['root'])
                self.assertEqual(a['blocks'],8192)
                roots.append(a['root'])
        cross=study.cross_cases()
        self.assertEqual(len(cross),6)
        for a,b in zip(cross[::2],cross[1::2]):
            self.assertEqual((a['root'],a['pair']),(b['root'],b['pair']))
            self.assertNotEqual(a['seed'],a['opponent_seed'])
            roots.append(a['root'])
        self.assertEqual(len(set(roots)),21)
        self.assertEqual(sum(x['blocks']*6 for r in [study.matrix(0),study.matrix(1),cross] for x in r),2064384)
        self.assertTrue(set(roots).isdisjoint(x['root'] for x in study.old.cases()))
        self.assertTrue(set(roots).isdisjoint(x['root'] for r in [study.matrix(0,True),study.matrix(1,True),study.cross_cases(True)] for x in r))
        self.assertEqual(study.expected_loads(cross),9)

    def test_family_intervals_are_not_pointwise(self):
        x=study.adjusted([5.,10.,15.,20.],16)
        self.assertLess(x['lower_family95'],x['lower95_bb100'])
        self.assertGreater(x['upper_family95'],x['upper95_bb100'])
        with self.assertRaises(ValueError):study.adjusted([float('nan'),1],2)

    def test_staging_preserves_bytes_and_records_restoration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'live';root.mkdir();cache=Path(tmp)/'cache'
            file=root/'seed'/'model.gz';file.parent.mkdir();file.write_bytes(b'checkpoint bytes')
            digest=guard.sha(file)
            study.stage_files(root,cache,[file])
            self.assertTrue(file.is_symlink())
            self.assertEqual(guard.sha(file),digest)
            row=json.loads((root/'relocations.jsonl').read_text())
            self.assertEqual(row['sha256'],digest)
            self.assertFalse(row['drive_accepted'])
            self.assertEqual(row['destination'],str(cache/'seed/model.gz'))
            study.stage_files(root,cache,[file])
            self.assertEqual(len((root/'relocations.jsonl').read_text().splitlines()),1)

    def test_staging_rejects_external_paths_and_existing_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'live';root.mkdir();cache=Path(tmp)/'cache';cache.mkdir()
            external=Path(tmp)/'external';external.write_text('protected')
            for file in (external,root/'..'/'external'):
                with self.assertRaises(ValueError):study.stage_files(root,cache,[file])
            own=root/'own';own.write_text('new');(cache/'own').write_text('partial')
            with self.assertRaises(ValueError):study.stage_files(root,cache,[own])
            self.assertFalse(own.is_symlink())
            link=root/'other';link.symlink_to(external)
            with self.assertRaises(ValueError):study.stage_files(root,cache,[link])
            self.assertEqual(external.read_text(),'protected')

    def test_failed_copy_verification_retains_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'live';root.mkdir();cache=Path(tmp)/'cache';file=root/'data';file.write_text('evidence')
            real=guard.sha
            with patch.object(guard,'sha',side_effect=lambda p:'bad' if Path(p).is_relative_to(cache) else real(p)):
                with self.assertRaises(ValueError):study.stage_files(root,cache,[file])
            self.assertFalse(file.is_symlink())
            self.assertEqual(file.read_text(),'evidence')
            self.assertEqual((cache/'data').read_text(),'evidence')
            self.assertFalse((root/'relocations.jsonl').exists())

    def test_supervised_readout_phase_requires_complete_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            c=dict(smoke=True,matrices=[study.matrix(0,True),study.matrix(1,True)],cross=study.cross_cases(True))
            guard.write(root/'config.json',c)
            guard.write(root/'status.json',dict(status='global-readout'))
            manifests={}
            for seed in study.SEEDS:
                path=root/f'lineage-{seed}'/'comparison'/'evaluation-manifest.json'
                path.parent.mkdir(parents=True);guard.write(path,{})
                manifests[str(path.relative_to(root))]=guard.sha(path)
            cross=root/'cross'/'evaluation-manifest.json';cross.parent.mkdir();guard.write(cross,{})
            guard.write(root/'evaluation-verified.json',dict(status='passed',initial_hands=504,reproduction_hands=504,
                manifests=manifests,cross_manifest_sha256=guard.sha(cross)))
            with patch.object(study,'validate_config'),patch.object(study.old,'read',side_effect=RuntimeError('barrier passed')) as reader:
                with self.assertRaisesRegex(RuntimeError,'barrier passed'):study.read(root)
                self.assertEqual(reader.call_count,1)
                guard.write(root/'failure.json',dict(error='failed'))
                with self.assertRaisesRegex(ValueError,'global confirmation barrier'):study.read(root)
                self.assertEqual(reader.call_count,1)

    def test_changed_science_rejected_before_build_access(self):
        c=dict(smoke=False,seeds=list(study.SEEDS),targets=list(study.TARGETS),cap=250000000,
            matrices=[study.matrix(0),study.matrix(1)],cross=study.cross_cases(),
            source_files={},resource_policy=study.prior.RESOURCE_POLICY)
        c['matrices'][0][0]['root']+=1
        with self.assertRaisesRegex(ValueError,'frozen confirmation'):study.validate_config(c)


if __name__=='__main__':unittest.main()
