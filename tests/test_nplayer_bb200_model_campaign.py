from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import nplayer_bb200_model_campaign as study
from scripts import nplayer_inference_validation as io


class CampaignTests(unittest.TestCase):
    def test_fixed_matrix_fresh_roots_and_correct_cycles(self):
        rows=study.matrix();self.assertEqual(len(rows),36)
        self.assertEqual(sum(r['blocks']*6 for r in rows),10543104)
        self.assertEqual(len({r['root'] for r in rows}),30)
        self.assertEqual(len({r['name'] for r in rows}),36)
        self.assertEqual(len(study.phases()),9)
        for i,seed in enumerate(study.SEEDS):
            own=[r for r in rows if r['seed']==seed and r['gate']=='direct']
            cross=[r for r in rows if r['seed']==seed and r['gate']=='cross']
            self.assertEqual((own[0]['blocks'],own[0]['root']),(own[1]['blocks'],own[1]['root']))
            self.assertEqual((cross[0]['blocks'],cross[0]['root']),(cross[1]['blocks'],cross[1]['root']))
            self.assertEqual(cross[0]['pair'],f'baseline-{study.SEEDS[(i+1)%3]}')
            self.assertEqual(cross[0]['singleton'],f'candidate-{seed}')
            self.assertEqual(cross[1]['singleton'],f'baseline-{seed}')
        smoke=study.matrix(True)
        self.assertEqual(sum(r['blocks']*6 for r in smoke),432)
        self.assertFalse({r['root'] for r in smoke}&{r['root'] for r in rows})
        self.assertEqual({r['seed'] for r in smoke},set(study.FIXTURE_SEEDS))
        for r in rows:
            if r.get('opponent','').startswith('trained-'):self.assertEqual(r['players'][1],'baseline')

    def test_200bb_job_and_legacy_manifest_are_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);seed=study.SEEDS[0]
            rows=[r for r in study.matrix(True) if r['phase'].startswith('own-')][:1]
            rows=[dict(rows[0],seed=seed,phase=f'own-{seed}')]
            models={f'{a}-{seed}':dict(path='/policy',sha256='a'*64,mass='/mass') for a in ('baseline','candidate')}
            c=dict(tables='/tables',catalog={str(seed):{'baseline':{'mass':{'keyset_sha256':'keys'}}}})
            job,_=study.acceptance.make_job(root,c,f'own-{seed}',rows,models,stack_bb=200)
            self.assertEqual(io.load(job/'native.json')['stack_bb'],200)
            self.assertEqual(io.load(job/'evaluation-manifest.json')['stack_bb'],200)
            old,_=study.acceptance.make_job(root,c,f'own-{seed}-old',rows,models)
            self.assertEqual(io.load(old/'native.json')['stack_bb'],100)
            self.assertNotIn('stack_bb',io.load(old/'evaluation-manifest.json'))

    def test_wrong_trace_depth_cannot_reach_replay_or_readout(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);trace=root/'trace';trace.write_text(json.dumps({'identity':{'stacks':[10000]*3}})+'\n')
            io.write(root/'native.json',dict(stack_bb=200,cases=[dict(trace=str(trace))]))
            with patch.object(study.acceptance,'verify_job') as verifier:
                with self.assertRaisesRegex(ValueError,'trace depth'):study.verify_job(root)
                verifier.assert_not_called()

    def test_catalog_mutation_is_refused_and_cannot_be_refrozen(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);models={str(i):{'sha256':str(i)} for i in range(6)}
            study.freeze_models(root,models);self.assertEqual(study.verify_freeze(root),models)
            with self.assertRaises(FileExistsError):study.freeze_models(root,models)
            io.write(root/'models.json',{})
            with self.assertRaisesRegex(ValueError,'catalog mutated'):study.verify_freeze(root)

    def test_missing_global_proof_or_failure_prevents_readout(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(FileNotFoundError):study.acceptance.verify_barrier(root,dict(smoke=True),phase_rows=study.phases(True))
            io.write(root/'failure.json',{'error':'terminal'})
            with self.assertRaisesRegex(ValueError,'terminal failure'):
                study.acceptance.verify_barrier(root,dict(smoke=True),phase_rows=study.phases(True))

    def test_configuration_refuses_recipe_counts_and_resource_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);binary=root/'binary';binary.write_text('binary')
            tables=root/'tables';tables.mkdir();(tables/'k50').write_text('table')
            build=root/'build.json';binaries={n:str(binary) for n in study.NAMES}
            io.write(build,dict(source='source',native_tests_passed=True,binaries=binaries,
                sha256s={n:io.sha(binary) for n in study.NAMES}))
            c=dict(format='nplayer-bb200-model-campaign-v1',accepted_seconds=64800,smoke=True,
                proposal_sha256=io.sha(study.SOURCE/study.PROPOSAL),cases=study.matrix(True),seeds=list(study.FIXTURE_SEEDS),
                targets=[100000,200000],max_entries=10000,resource_policy=study.acceptance.thermal.RESOURCE_POLICY,
                source_files={'pin':'same'},source='source',stack_bb=200,threads=16,roots_per_seat=8,
                last_average_street=3,freeze_at_cap=True,fast_gzip=True,pruning=False,
                cleanup_staging_uploads='owner-vacuum-cleaner-only',build_receipt=str(build),build_receipt_sha256=io.sha(build),
                binaries=binaries,python=str(binary),python_sha256=io.sha(binary),environment={'engine':'same'},
                tables=str(tables),table_sha256s={'k50':io.sha(tables/'k50')})
            with patch.object(study,'source_pins',return_value={'pin':'same'}),patch.object(study,'committed',return_value='source'),patch.object(study.acceptance.thermal,'python_environment',return_value=(binary,{'engine':'same'})):
                study.validate_config(c)
                for key,value in [('accepted_seconds',43200),('targets',[3000000000]),('stack_bb',100),('threads',8),
                        ('roots_per_seat',4),('last_average_street',2),('pruning',True),('freeze_at_cap',False),
                        ('cases',[]),('max_entries',10001),('cleanup_staging_uploads','automatic'),('source_files',{})]:
                    bad=deepcopy(c);bad[key]=value
                    with self.subTest(key=key),self.assertRaises(ValueError):study.validate_config(bad)
                binary.write_text('mutated')
                with self.assertRaisesRegex(ValueError,'binary changed'):study.validate_config(c)

    def test_duplicate_attempt_never_invokes_science(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);io.write(root/'config.json',{});io.write(root/'status.json',{})
            with patch.object(study,'validate_config'),patch.object(study,'execute') as execute:
                with self.assertRaisesRegex(ValueError,'attempt exists'):study.run(root)
                execute.assert_not_called()

    def test_wrong_allocation_cannot_even_create_preparation_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'not-created'
            with self.assertRaisesRegex(ValueError,'18h allocation'):study.configure(root,None,False,None,43200)
            self.assertFalse(root.exists())


if __name__=='__main__':unittest.main()
