import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import nplayer_pruning_strength as study


class ProtocolTests(unittest.TestCase):
    def test_two_disjoint_paired_matrices_with_fixed_sample_counts(self):
        roots=[]
        for phase in ('nodes','clock'):
            rows=study.cases(phase)
            self.assertEqual(len(rows),10)
            self.assertEqual(sum(r['blocks']*6 for r in rows),491520)
            self.assertEqual(len({r['name'] for r in rows}),10)
            roots.append({r['root'] for r in rows})
            for a,b in zip(rows[::2],rows[1::2]):
                self.assertEqual(a['root'],b['root'])
                if a['group']=='direct':
                    self.assertEqual((a['singleton'],a['pair']),(b['pair'],b['singleton']))
                else:
                    self.assertEqual(a['pair'],b['pair'])
                    self.assertEqual((a['singleton'],b['singleton']),('candidate','baseline'))
        self.assertFalse(roots[0]&roots[1])
        for smoke,calibration in ((False,False),(True,False),(False,True)):
            previous={r['root'] for r in study.bounded.cases(smoke,calibration)}
            self.assertFalse(set.union(*roots)&previous)

    def test_continuation_depends_only_on_training_time_not_strength(self):
        node=dict(active_seconds=400.)
        self.assertEqual(study.next_clock_action({'nodes':node}),'continue')
        for score in (-1000.,0.,1000.):
            self.assertEqual(study.next_clock_action({'nodes':node,'score':score}),'continue')
        self.assertEqual(study.next_clock_action({'nodes':dict(active_seconds=700.),'clock':{}}),'reuse')
        with self.assertRaisesRegex(ValueError,'missed'):
            study.next_clock_action({'nodes':dict(active_seconds=700.)})

    def test_resume_uses_exact_node_checkpoint_and_accumulated_clock(self):
        endpoint=dict(model=dict(checkpoint='node.gz',checkpoint_sha256='a'*64),clock_path='clock.json',clock_sha256='b'*64)
        c=study.training_config({'tables':'tables'},Path('/new'),'continue-clock',endpoint)
        self.assertEqual(c['input'],'node.gz')
        self.assertEqual(c['input_clock_sha256'],'b'*64)
        self.assertEqual(c['active_seconds_target'],630.740595090997)
        self.assertEqual(c['pruning'],dict(bb=.05,after=200))
        self.assertNotIn('input',study.training_config({'tables':'tables'},Path('/new'),'nodes'))


class ReceiptTests(unittest.TestCase):
    def result(self,root,label='nodes',seconds=400.):
        cp=root/(label+'.gz');cp.write_bytes(b'checkpoint')
        export=root/(label+'-average.gz');export.write_bytes(b'average')
        cp_sha=study.guard.sha(cp)
        endpoint=dict(event='endpoint',label=label,nodes=study.NODE_TARGET+10,iteration=250000,
                      active_seconds=seconds,segment_active_seconds=seconds,pruned_actions=123,last_iteration_seconds=.001)
        proof=dict(endpoint,checkpoint=str(cp),checkpoint_sha256=cp_sha,target_seconds=study.ACTIVE_TARGET)
        clock=root/(label+'-clock.json');study.guard.write(clock,proof)
        endpoint.update(clock_path=str(clock),clock_sha256=study.guard.sha(clock))
        result=dict(returncode=0,events=[
            dict(event='checkpoint',label=label,path=str(cp),sha256=cp_sha,nodes=endpoint['nodes'],iteration=endpoint['iteration']),
            dict(event='exported',label=label,path=str(export),sha256=study.guard.sha(export),
                 checkpoint=str(cp),checkpoint_sha256=cp_sha),endpoint,dict(event='complete')])
        return result,clock

    def test_endpoint_identity_clock_hash_and_duration_are_checked(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);result,path=self.result(root)
            v=study.endpoint_models(result,root)
            self.assertEqual(v['nodes']['active_seconds'],400.)
            path.write_text(path.read_text()+' ')
            with self.assertRaisesRegex(ValueError,'receipt differs'):study.endpoint_models(result,root)

    def test_incomplete_or_duplicated_endpoints_and_failed_commands_refuse(self):
        for fault in ('failed','missing-complete','duplicate','clock-too-early','wrong-clock-lineage'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as d:
                root=Path(d);result,path=self.result(root,'clock' if fault=='clock-too-early' else 'nodes')
                if fault=='failed':result['returncode']=1
                elif fault=='missing-complete':result['events'].pop()
                elif fault=='duplicate':result['events'].append(copy.deepcopy(result['events'][2]))
                elif fault=='wrong-clock-lineage':
                    v=study.load(path);v['checkpoint_sha256']='wrong';study.guard.write(path,v)
                    result['events'][2]['clock_sha256']=study.guard.sha(path)
                with self.assertRaises(ValueError):study.endpoint_models(result,root)

    def model(self,root):
        header=dict(players=3,game=dict(stacks=[10000]*3),seed=study.SEED,sampling='path-v1',roots_per_seat=8,
                    last_average_street=3,max_entries=250000000,freeze_at_cap=True,iteration=study.BASELINE_ITERATION,
                    counts=dict(nodes=study.BASELINE_NODES))
        cp=root/'model.gz'
        with gzip.open(cp,'wt') as f:json.dump(header,f);f.write('\n')
        policy=root/'average.gz';policy.write_bytes(b'policy')
        return dict(checkpoint=str(cp),checkpoint_sha256=study.guard.sha(cp),path=str(policy),
                    sha256=study.guard.sha(policy),strategy='average',scope=3),header

    def test_baseline_recipe_pruning_flags_and_checkpoint_clock_accounting(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);model,h=self.model(root)
            study.verify_model(model,None)
            with self.assertRaisesRegex(ValueError,'recipe'):study.verify_model(model,study.PRUNING)
            h['pruning']=dict(study.PRUNING,pruned_actions=123)
            with gzip.open(model['checkpoint'],'wt') as f:json.dump(h,f);f.write('\n')
            model['checkpoint_sha256']=study.guard.sha(model['checkpoint'])
            endpoint=dict(nodes=study.BASELINE_NODES,iteration=study.BASELINE_ITERATION,pruned_actions=123)
            study.verify_model(model,study.PRUNING,endpoint)
            endpoint['pruned_actions']=124
            with self.assertRaisesRegex(ValueError,'accounting'):study.verify_model(model,study.PRUNING,endpoint)

    def test_unverified_readout_refuses_before_reading_payoffs(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);study.guard.write(root/'evaluation-manifest.json',dict(phase='nodes'))
            study.guard.write(root/'evaluation-verified.json',{})
            study.guard.write(root/'status.json',dict(status='running'))
            with self.assertRaisesRegex(ValueError,'barrier'):study.read(root)

    def test_batch_reuses_bounded_replay_with_two_resident_models(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);study.guard.write(root/'evaluation-manifest.json',dict(phase='clock'))
            with patch.object(study.bounded,'batch') as batch:
                study.batch(root)
            batch.assert_called_once_with(root,matrix=study.cases('clock'),expected_loads=2)


class StageOrderTests(unittest.TestCase):
    def exercise(self, root, early_clock):
        events=[]
        node=dict(model=dict(path='node-average.gz',sha256='node-policy',checkpoint='node.gz',checkpoint_sha256='node-cp'),
                  active_seconds=400.,nodes=study.NODE_TARGET+10,iteration=220000,pruned_actions=123,
                  clock_path='node-clock.json',clock_sha256='clock-pin')
        clock=dict(model=dict(path='clock-average.gz',sha256='clock-policy',checkpoint='clock.gz',checkpoint_sha256='clock-cp'),
                   active_seconds=study.ACTIVE_TARGET,segment_active_seconds=study.ACTIVE_TARGET-400.,
                   nodes=study.NODE_TARGET+1000,iteration=230000,pruned_actions=140)
        if early_clock:
            node.update(active_seconds=700.,nodes=study.NODE_TARGET+2000,iteration=240000,pruned_actions=150)
        c=dict(python='python',train='trainer',tables='tables',arena='arena',arena_sha256='arena-pin',baseline=study.baseline())
        def stage(name,command):
            events.append(name)
            if name=='train-nodes':return dict(endpoints=dict(nodes=node,**({'clock':clock} if early_clock else {})))
            if name=='train-continue-clock':
                config=study.load(root/'continue-clock-training-config.json')
                self.assertEqual(config['input'],'node.gz')
                return dict(endpoints=dict(clock=clock))
            if name.startswith('audit-'):
                model=node['model'] if name=='audit-nodes' else clock['model']
                path=root/'measurements'/name/'stdout.log';path.parent.mkdir(parents=True)
                study.guard.write(path,dict(status='passed',policy_sha256=model['sha256'],checkpoint_sha256=model['checkpoint_sha256']))
            if name.startswith('read-'):
                # Adverse/inconclusive poker output cannot select or cancel the
                # continuation. Only the precommitted training clock decides it.
                phase=name.removeprefix('read-')
                study.guard.write(root/('comparison-'+phase)/'results.json',dict(status='settled',score=-1000))
            return dict(returncode=0)
        with patch.object(study,'endpoint_models',side_effect=lambda value,folder:value['endpoints']):
            study.execute_study(c,root,stage)
        return events

    def test_equal_node_readout_precedes_resume_even_for_adverse_result(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);events=self.exercise(root,False)
            self.assertLess(events.index('read-nodes'),events.index('train-continue-clock'))
            self.assertLess(events.index('train-continue-clock'),events.index('evaluate-clock'))
            self.assertEqual(study.load(root/'status.json')['status'],'complete')
            self.assertEqual(study.load(root/'results.json')['status'],'settled')

    def test_slower_pruned_training_reuses_the_saved_time_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);events=self.exercise(root,True)
            self.assertNotIn('train-continue-clock',events)
            self.assertLess(events.index('read-nodes'),events.index('evaluate-clock'))


class ReadoutTests(unittest.TestCase):
    def test_verified_synthetic_payoff_fixture_has_the_expected_sign_and_scale(self):
        # Payoff-only fixture: no actual poker or replay is performed by this test.
        # It exercises the reader after its independently tested replay barrier.
        try:
            import scipy
        except ImportError:
            self.skipTest('SciPy is required for statistical readout')
        from scripts.analyze_nplayer_arena import PERMUTATIONS
        with tempfile.TemporaryDirectory() as d,patch.object(study,'BLOCKS',2):
            root=Path(d);matrix=study.cases('nodes')
            study.guard.write(root/'evaluation-manifest.json',dict(phase='nodes',cases=matrix,models={}))
            for case in matrix:
                folder=root/'evaluation'/case['name'];folder.mkdir(parents=True)
                rows=[dict(seed=case['root'],blocks=2,identity=dict(big_blind=100))]
                for block in range(2):
                    for permutation,ids in enumerate(PERMUTATIONS):
                        seat=ids.index(0);reward=(10+block if case['name']=='direct-0' else -8-block) if case['group']=='direct' else (20+block if case['singleton']=='candidate' else 15+block)
                        others=[i for i in range(3) if i!=seat];rewards=[0]*3
                        rewards[seat]=reward;rewards[others[0]]=-reward//2;rewards[others[1]]=-reward-rewards[others[0]]
                        rows.append(dict(block=block,permutation=permutation,identities=ids,rewards=rewards,deck=list(range(52))))
                text=''.join(json.dumps(row)+'\n' for row in rows)
                for name in ('play-0.jsonl','play-1.jsonl'):(folder/name).write_text(text)
                digest=study.guard.sha(folder/'play-0.jsonl')
                study.guard.write(folder/'result.json',dict(status='passed',case=case,hands=12,trace_sha256=digest))
                study.guard.write(folder/'replay.json',dict(status='passed',hands=12,trace_sha256=digest))
            study.guard.write(root/'evaluation-verified.json',dict(status='passed',cases=10,hands=120,
                manifest_sha256=study.guard.sha(root/'evaluation-manifest.json')))
            study.guard.write(root/'status.json',dict(status='verified-readout-ready'))
            study.read(root);result=study.load(root/'results.json')
            self.assertEqual(result['rows'][0]['score']['mean_bb100'],9.5)
            self.assertEqual([r['score']['mean_bb100'] for r in result['rows'][1:]],[5.]*4)
            self.assertEqual(len(result['rows'][0]['fast_by_seat']),3)
            self.assertTrue(result['no_automatic_adoption'])
            # A corrupt reproduction prevents another payoff readout.
            (root/'evaluation/direct-1/play-1.jsonl').write_text('changed')
            with self.assertRaisesRegex(ValueError,'trace verification'):study.read(root)


class ResourcePolicyTests(unittest.TestCase):
    def test_only_temperature_is_enforced_without_disk_swap_or_time_checks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);supervisor=study.Supervisor(root,1,2);supervisor.started-=10**9
            with patch.object(study.guard,'sensors',return_value={'Package id 0':89.,'Thermistor 15':99.9}), \
                 patch.object(study.guard,'memory',side_effect=AssertionError('no swap/memory polling')), \
                 patch.object(study.os,'statvfs',side_effect=AssertionError('no disk polling')), \
                 patch.object(study.guard,'group_metrics',return_value={'rss_bytes':2**50}):
                value=supervisor.sample(type('Child',(),{'pid':1})(),'train',3000000000)
                self.assertEqual(value['rss_bytes'],2**50)
                self.assertGreater(value['elapsed_seconds'],10**8)
                self.assertNotIn('swap_used_bytes',value)
                self.assertNotIn('free_disk_bytes',value)
                self.assertIsNone(supervisor.address_limit)
                (root/'STOP').write_text('owner stop')
                with self.assertRaisesRegex(RuntimeError,'owner stop'):supervisor.sample(None,'train',0)

    def test_temperature_crossing_and_missing_sensor_stop(self):
        for cpu,thermistor in ((90.,60.),(50.,100.),(float('nan'),50.)):
            row=dict(temperatures_c={'Package id 0':cpu,'Thermistor 15':thermistor})
            with self.assertRaisesRegex(RuntimeError,'thermal stop') as error:study.enforce_temperatures(row)
            self.assertIs(error.exception.resource_sample,row)
        with self.assertRaisesRegex(RuntimeError,'sensors missing'):
            study.enforce_temperatures(dict(temperatures_c={'Package id 0':50.}))

    @unittest.skipUnless(__import__('sys').platform=='linux','Linux process-group wrapper')
    def test_temperature_only_supervisor_starts_a_child_without_address_limit(self):
        import os,sys
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with (root/'own.lock').open('w') as own,(root/'normal.lock').open('w') as normal:
                supervisor=study.Supervisor(root,own.fileno(),normal.fileno())
                supervisor.cpus=set(os.sched_getaffinity(0))
                with patch.object(study.guard,'sensors',return_value={'Package id 0':50.,'Thermistor 15':50.}):
                    result=supervisor.execute('hello',[sys.executable,'-c','print("ok")'],study.SOURCE,
                        dict(os.environ,RAYON_NUM_THREADS='16'))
                self.assertEqual(result['returncode'],0)
