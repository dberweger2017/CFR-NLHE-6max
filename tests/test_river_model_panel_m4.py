import copy
from pathlib import Path
import sys
import tempfile
import unittest

from scripts.river_model_panel_protocol import PREFLIGHT, first_actor, quote, reentry_matches, signature, verify_batch_pair
from scripts.river_model_panel_m4 import Worker, validate_fixture
from scripts.river_model_panel_protocol import SEED


class RiverModelPanelTests(unittest.TestCase):
    def test_fixture_cannot_silently_change_seed_scope_or_stop_early(self):
        game=dict(stacks=[10000]*3,small_blind=50,big_blind=100,
                  schema='nplayer-button-live-actor-history-equity-k50-v1')
        h=dict(format='nplayer-cfr-v1',players=3,game=game,seed=SEED,max_entries=1000000,
               freeze_at_cap=True,roots_per_seat=8,last_average_street=3,sampling='path-v1',
               average_rule='opponent-sampled',entries=1000234,counts=dict(nodes=25001234))
        s=dict(identity=game,stop_reason='nodes',entries=h['entries'],counts=h['counts'])
        validate_fixture(h,s)  # Whole-iteration membership overshoot is legitimate.
        for key,value in [('seed',SEED+1),('last_average_street',2),('max_entries',2000000)]:
            wrong=copy.deepcopy(h);wrong[key]=value
            with self.assertRaises(ValueError):validate_fixture(wrong,s)
        wrong=copy.deepcopy(s);wrong['stop_reason']='time'
        with self.assertRaises(ValueError):validate_fixture(h,wrong)

    def response(self):
        return dict(status='ok',worker_seconds_before_serialization=.2,result=dict(
            actions=[['check',0]],probabilities=[1.],produced_root_strategy=dict(probabilities=[1.]),
            quality=dict(best_response_gains_bb=[.01,.02]),sweeps=16,target_bb=.02,
            checkpoints=[dict(sweeps=16,elapsed_seconds=.1,target_met=True)],
            timings=dict(solve_seconds=.1),solver_timing=dict(sweeps=16,traversal_seconds=.01),
            session=dict(handle='opaque',hand_id='public/0',installed_search=True,fallback_reason=None,
                         binding=dict(profile_sha256='profile',root_sha256='root'))))

    def test_only_declared_measurements_and_handle_are_ignored(self):
        a=self.response();b=copy.deepcopy(a)
        b['worker_seconds_before_serialization']=90.;b['result']['timings']['solve_seconds']=70.
        b['result']['checkpoints'][0]['elapsed_seconds']=20.
        b['result']['solver_timing']['traversal_seconds']=3.
        b['result']['session']['handle']='other'
        self.assertEqual(signature(a),signature(b))
        for key,value in [('sweeps',32),('probabilities',[-0.]),('quality',dict(best_response_gains_bb=[.01,.03]))]:
            c=copy.deepcopy(b);c['result'][key]=value
            self.assertNotEqual(signature(a),signature(c))
        b['result']['unexpected_seconds']=1.
        self.assertNotEqual(signature(a),signature(b))

    def test_float_bits_profile_and_signed_zero_are_preserved(self):
        a=self.response();b=copy.deepcopy(a)
        a['result']['probabilities']=[0.];b['result']['probabilities']=[-0.]
        self.assertNotEqual(signature(a),signature(b))
        b=copy.deepcopy(a);b['result']['session']['binding']['profile_sha256']='different'
        self.assertNotEqual(first_actor(a),first_actor(b))
        b=copy.deepcopy(a);b['result']['probabilities']=[float('nan')]
        with self.assertRaises(ValueError):signature(b)

    def test_reentry_cannot_advance_solver_or_change_fallback_or_bits(self):
        a=self.response()
        b=dict(status='ok',result=dict(actions=a['result']['actions'],probabilities=[1.],
               installed_search=True,fallback_reason=None,profile_sha256='profile',solver_advances=0,off_tree_entry=None))
        reentry_matches(a,b)
        for field,value in [('solver_advances',1),('solver_advances',False),('installed_search',False),
                            ('probabilities',[.999]),('profile_sha256','changed')]:
            c=copy.deepcopy(b);c['result'][field]=value
            with self.assertRaises(ValueError):reentry_matches(a,c)

    def test_reproduction_requires_every_root_and_adverse_status(self):
        rows=[dict(id=i,begin=self.response(),reentry=None,release=None) for i in (0,4)]
        a=dict(roots=rows);b=copy.deepcopy(a)
        self.assertEqual(verify_batch_pair(a,b,[0,4])['roots'],2)
        b['roots'].pop()
        with self.assertRaises(ValueError):verify_batch_pair(a,b,[0,4])
        b=copy.deepcopy(a);b['roots'][1]['begin']=dict(status='unsupported',reason='zero reach')
        with self.assertRaises(ValueError):verify_batch_pair(a,b,[0,4])

    def test_quote_uses_frozen_counts_and_total_cost_not_outcomes(self):
        batches=[]
        for v,ids in PREFLIGHT.items():
            for i in (0,1):
                batches.append(dict(version=v,startup_wall_seconds=1.,shutdown_seconds=.1,
                    roots=[dict(id=n,begin_seconds=.1,reentry_seconds=.01,release_seconds=.001) for n in ids]))
        q=quote(batches,200.,6*2**30,4*2**30)
        self.assertTrue(q['main_admitted']);self.assertGreater(q['reserved_seconds'],800.)
        other=copy.deepcopy(batches);other[0]['roots'][0]['ignored_outcome']=-999.
        self.assertEqual(q,quote(other,200.,6*2**30,4*2**30))
        self.assertFalse(quote(batches,3600.,6*2**30,4*2**30)['main_admitted'])
        self.assertFalse(quote(batches,200.,4*2**30,4*2**30)['main_admitted'])

    def test_transport_reuses_one_worker_and_retains_wire(self):
        code='import json,sys;print(json.dumps({"status":"ready"}),flush=True)\nfor line in sys.stdin: print(json.dumps({"status":"ok","echo":json.loads(line)}),flush=True)'
        with tempfile.TemporaryDirectory() as tmp:
            w=Worker([sys.executable,'-u','-c',code],Path(tmp))
            try:
                for i in (0,1):self.assertEqual(w.request(dict(id=i))[0]['echo']['id'],i)
            finally:w.close()
            wire=(Path(tmp)/'wire.jsonl').read_text().splitlines()
            self.assertEqual(len(wire),5)
