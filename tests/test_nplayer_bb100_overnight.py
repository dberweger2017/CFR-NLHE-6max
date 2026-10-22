import unittest
import tempfile
import copy
import json
from pathlib import Path
from scripts import nplayer_bb100_overnight as study


class CampaignTests(unittest.TestCase):
    def test_matrix_is_paired_and_disjoint_from_smoke_and_monitors(self):
        rows, smoke = study.cases(), study.cases(True)
        self.assertEqual(len(rows), 36)
        self.assertEqual(sum(r['blocks']*6 for r in rows), 1769472)
        self.assertEqual(len({r['name'] for r in rows}), 36)
        self.assertFalse({r['root'] for r in rows} & {r['root'] for r in smoke})
        for a, b in zip(rows[::2], rows[1::2]):
            self.assertEqual(a['root'], b['root'])
            if a['group'] != 'bot':
                self.assertEqual((a['singleton'], a['pair']), (b['pair'], b['singleton']))
            else:
                self.assertEqual(a['pair'], b['pair'])
        self.assertEqual(sorted(r['name'] for r in rows), sorted(r['name'] for r in study.execution_order(rows)))

    def test_execution_order_keeps_same_seed_models_resident(self):
        order = study.execution_order(study.cases())
        self.assertEqual([r['group'] for r in order[-6:]], ['cross']*6)
        for i, seed in enumerate(study.SEEDS):
            self.assertTrue(all(r['seed'] == seed for r in order[i*10:(i+1)*10]))

    def test_quote_includes_serialization_audits_and_measured_parallel_replay(self):
        with tempfile.TemporaryDirectory() as d:
            export=Path(d)/'average.gz';export.write_bytes(b'x'*100)
            calibration = dict(wall_seconds=1000, sampled_peak_rss_by_phase={'all':20*study.guard.GIB}, events=[
                dict(event='frozen', nodes=1500000000, active_seconds=300),
                dict(event='complete', nodes=2000000000, active_seconds=400, monitor_seconds=1),
                dict(event='checkpoint', save_seconds=100, bytes=200), dict(event='exported', export_seconds=50, path=str(export))])
            performance=dict(blocks=128,cases=36,policy_loads=12,native_load_seconds=100,
                native_wall_seconds=150,native_play_seconds=20,replay_wall_seconds=10,
                input_verification_seconds=2,trace_bytes=1000,json_scan_seconds=3)
            quote=study.cost_quote(calibration,{'wall_seconds':200},{'wall_seconds':300},performance,
                dict(sampled_peak_rss_by_phase={'all':40*study.guard.GIB}))
            self.assertEqual(quote['saving_seconds'],1200)
            self.assertEqual(quote['audit_seconds'],1500)
            self.assertEqual(quote['post_freeze_nodes_per_second'],5000000)
            self.assertEqual(quote['play_seconds'],50*64)  # includes post-play trace hashes.
            self.assertEqual(quote['replay_seconds'],10*64)  # measured8-worker wall, no assumed8x.
            self.assertGreater(quote['main_output_bytes_with_allowance'],1000*64)
            self.assertGreater(quote['total_seconds_with_allowance'],quote['training_seconds'])

    def test_matrix_smoke_uses_six_distinct_cache_identities(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=root/'average.gz';path.write_bytes(b'fixture')
            m=dict(path=str(path),sha256='fixture')
            aliases=study.aliased_models(root,m,m)
            self.assertEqual(len({v['path'] for v in aliases.values()}),6)
            self.assertTrue(all(Path(v['path']).samefile(path) for v in aliases.values()))
            self.assertFalse({r['root'] for r in study.cases(calibration=True)} &
                             {r['root'] for r in study.cases()})

    def test_missing_completion_refuses(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            study.validate_trajectory({'events':[]}, study.CAP, 2000000000)


class ContinuationTests(unittest.TestCase):
    def test_prefix_cost_offsets_preserve_post_freeze_rate_and_raw_results(self):
        before=dict(returncode=0,wall_seconds=1000,cpu_seconds=5000,
            sampled_peak_rss_by_phase={'train':20},events=[
                dict(event='probe'),dict(event='probe'),
                dict(event='complete',nodes=2000003197,active_seconds=400.,monitor_seconds=2.)])
        after=dict(returncode=0,wall_seconds=800,cpu_seconds=3000,
            sampled_peak_rss_by_phase={'train':30},events=[
                dict(event='frozen',nodes=2100000000,active_seconds=20.,monitor_seconds=0.),
                dict(event='probe'),
                dict(event='complete',nodes=3000000001,active_seconds=220.,monitor_seconds=1.)])
        original=copy.deepcopy((before,after))
        basis=study.continuation_cost_basis(before,after)
        frozen=study.events(basis,'frozen')[0];done=study.events(basis,'complete')[0]
        self.assertEqual(frozen['active_seconds'],420.)
        self.assertEqual(done['active_seconds'],620.)
        self.assertEqual(done['monitor_seconds'],3.)
        self.assertEqual(basis['monitor_probe_count'],3)
        self.assertEqual(basis['wall_seconds'],1800)
        self.assertEqual(done['active_seconds']-frozen['active_seconds'],200.)
        self.assertEqual((before,after),original)
        bad=copy.deepcopy(after);bad['events'][0]['nodes']=1999999999
        with self.assertRaisesRegex(ValueError,'incomplete'):
            study.continuation_cost_basis(before,bad)

    def fixture(self,folder):
        previous=folder/'previous';previous.mkdir()
        root=folder/'next';root.mkdir()
        config={k+'_sha256':k for k in ('train','legacy_train','policy','arena','legacy_arena')}
        config.update(python='pinned-python',tables='pinned-tables',source_files={'scripts/audit_nplayer_policy_parallel.py':'audit-pin'})
        def write(name,value):
            path=previous/name;path.parent.mkdir(parents=True,exist_ok=True);study.guard.write(path,value)
        write('config.json',config)
        write('small-qualification.json',dict(status='passed',probe_hands=3072,smoke_hands=432))
        write('smoke/evaluation-manifest.json',dict(smoke=True,cases=study.cases(True)))
        manifest_sha=study.guard.sha(previous/'smoke/evaluation-manifest.json')
        write('smoke/evaluation-verified.json',dict(status='passed',manifest_sha256=manifest_sha,cases=36,hands=432))
        write('smoke/evaluation-cost.json',dict(policy_loads=12))
        checkpoint=str(previous/'calibration/2000000000.gz');digest='a'*64
        write('measurements/calibration/result.json',dict(returncode=0,events=[
            dict(event='checkpoint',label='2000000000',nodes=2000003197,entries=244485627,
                 frozen_at=None,path=checkpoint,sha256=digest),
            dict(event='exported',label='2000000000',checkpoint=checkpoint,checkpoint_sha256=digest,
                 path=str(previous/'calibration/2000000000-average.gz'),sha256='b'*64)]))
        write('validations/calibration/failure.json',dict(error="ValueError('capacity was not reached at the fixed qualification endpoint')"))
        write('source-receipt.json',dict(source_commit='fixture'))
        write('status.json',dict(status='validate-calibration'))
        write('failure.json',dict(error="RuntimeError('validate-calibration failed with exit 1')",at=1))
        files={str(p.relative_to(previous)):study.guard.sha(p) for p in previous.rglob('*.json')}
        config['continuation_parent']=dict(root=str(previous),files=files,checkpoint=checkpoint,checkpoint_sha256=digest)
        study.guard.write(root/'config.json',config)
        return root,previous

    def test_pinned_completed_parent_is_reused_and_changes_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root,previous=self.fixture(Path(d))
            study.parent(root)
            self.assertEqual(study.load(root/'inherited-qualification.json')['status'],'passed')
            path=previous/'small-qualification.json';path.write_text(path.read_text()+' ')
            with self.assertRaisesRegex(ValueError,'changed'):
                study.parent(root)

    def test_changed_binary_and_wrong_parent_stop_are_refused(self):
        for error_kind in ('binary','stop','dependency','root-failure'):
            with self.subTest(error_kind=error_kind),tempfile.TemporaryDirectory() as d:
                root,previous=self.fixture(Path(d));config=study.load(root/'config.json')
                if error_kind=='binary':config['train_sha256']='changed'
                elif error_kind=='dependency':config['source_files']['scripts/audit_nplayer_policy_parallel.py']='changed'
                elif error_kind=='root-failure':
                    path=previous/'failure.json'
                    study.guard.write(path,dict(error="RuntimeError('validate-calibration failed with exit 1')",resource_sample={'rss_bytes':99}))
                    config['continuation_parent']['files']['failure.json']=study.guard.sha(path)
                else:
                    path=previous/'validations/calibration/failure.json'
                    study.guard.write(path,dict(error='unexpected numerical failure'))
                    config['continuation_parent']['files']['validations/calibration/failure.json']=study.guard.sha(path)
                study.guard.write(root/'config.json',config)
                with self.assertRaises(ValueError):study.parent(root)
