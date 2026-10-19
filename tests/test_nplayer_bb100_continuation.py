import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import nplayer_bb100_continuation as s
from scripts.audit_nplayer_policy import sha
from scripts.audit_nplayer_policy_parallel import audit
from scripts.qualify_nplayer_bb100_continuation import compare_trajectories


class ProtocolTests(unittest.TestCase):
    def test_matrix_is_exact_paired_mixed_and_disjoint(self):
        rows=s.cases()
        self.assertEqual(len(rows),18)
        self.assertEqual(sum(x['blocks']*6 for x in rows),884736)
        self.assertEqual(len({x['name'] for x in rows}),18)
        old={r['root'] for phase in ('nodes','clock') for r in s.prior.cases(phase)}
        self.assertFalse({r['root'] for r in rows} & ({r['root'] for r in s.cases(True)} | old))
        for a,b in zip(rows[2::2],rows[3::2]):
            self.assertEqual(a['root'],b['root'])
            self.assertEqual(a['players'][1:],b['players'][1:])
            self.assertEqual((a['players'][0],b['players'][0]),('candidate','baseline'))
        self.assertEqual(sum(r['group']=='mixed-trained' for r in rows),4)
        self.assertEqual(sum(r['group']=='mixed-script' for r in rows),4)

    def test_resume_uses_one_endpoint_and_preserves_recipe(self):
        m=s.prior.baseline();c=s.training_config('tables','output','STOP',model=m)
        self.assertEqual(c['targets'],[10_000_000_000])
        self.assertEqual(c['input_sha256'],m['checkpoint_sha256'])
        self.assertEqual((c['seed'],c['threads'],c['max_entries']),(2026101935003,16,250000000))
        self.assertTrue(c['freeze_at_cap'] and c['parallel_gzip'])
        self.assertEqual(c['probe_blocks'],0)
        self.assertNotIn('pruning',c)
        self.assertFalse(c['save_anchor'])

    def test_relaunch_refuses_before_altering_completed_or_running_root(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s.guard.write(root/'launch.json',{'pid':123})
            with self.assertRaisesRegex(ValueError,'already launched'):s.run(root)
            self.assertEqual(s.load(root/'launch.json'),{'pid':123})
            self.assertFalse((root/'failure.json').exists())

    def test_unqualified_configuration_never_creates_root(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);q=root/'q.json';s.guard.write(q,dict(status='failed'))
            with patch.object(s.prior,'python_environment',return_value=('venv-python',{})),patch.object(s,'checked_build',return_value={}):
                with self.assertRaises(ValueError):s.configure(root/'run',root/'build',root/'tables',Path('venv'),q)
            self.assertFalse((root/'run').exists())

    def test_readout_refuses_before_reading_outcomes_without_global_proof(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);s.guard.write(root/'evaluation-manifest.json',{})
            s.guard.write(root/'evaluation-verified.json',{})
            s.guard.write(root/'status.json',dict(status='playing'))
            with self.assertRaises(ValueError):s.read(root)
            self.assertFalse((root/'results.json').exists())

    def test_diagnostics_comparison_detects_a_changed_action_not_only_payoff(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);a=root/'a';b=root/'b'
            h=dict(identity={},blocks=1,hands=1,seed=1,policies=[],distinct_policy_instances=3)
            row=dict(actions=[['call',0]],rewards=[0,0,0])
            a.write_text(json.dumps(h)+'\n'+json.dumps(row)+'\n')
            b.write_text(json.dumps(h)+'\n'+json.dumps(dict(row,lookups=[{}]))+'\n')
            self.assertEqual(compare_trajectories(a,b,True),1)
            b.write_text(json.dumps(h)+'\n'+json.dumps(dict(row,lookups=[{}],actions=[['fold',0]]))+'\n')
            with self.assertRaises(ValueError):compare_trajectories(a,b,True)


class MassAuditTests(unittest.TestCase):
    def fixture(self,root,corrupt=False):
        cp=root/'cp.gz';policy=root/'policy.gz'
        # Both normalized rows are uniform; only original accumulators distinguish them.
        rows=[['01'*16,0,0,6,1,[0.,0.],[2.,2.]],['02'*16,1,1,6,0,[0.,0.],[0.,0.]]]
        h=dict(format='nplayer-cfr-v1',game=dict(players=3),players=3,entries=2,last_average_street=3,
               counts=dict(decisions=[1]*4,missing=[0]*4))
        with gzip.open(cp,'wt') as f:
            f.write(json.dumps(h)+'\n')
            for row in rows:f.write(json.dumps(row)+'\n')
        ph=dict(format='nplayer-policy-v1',identity=h['game'],players=3,entries=2,last_average_street=3,
                strategy='average',continuation='none',source_checkpoint_sha256=sha(cp))
        with gzip.open(policy,'wt') as f:
            f.write(json.dumps(ph)+'\n')
            for row in rows:f.write(json.dumps(row[:4]+[[.7,.3] if corrupt else [.5,.5]])+'\n')
        return cp,policy

    def test_audit_classifies_original_mass_and_preserves_default_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cp,policy=self.fixture(root)
            old=audit(cp,policy,1,1);out=root/'mass'
            r=audit(cp,policy,2,1,lookup_out=out)
            self.assertTrue(all(r[k]==v for k,v in old.items()))
            self.assertEqual((r['zero_mass_rows'],r['positive_mass_rows']),(1,1))
            self.assertEqual((out/'zero-keys.bin').read_bytes(),bytes.fromhex('02'*16))
            self.assertEqual(r['keyset_sha256'],hashlib.sha256(bytes.fromhex('01'*16+'02'*16)).hexdigest())
            model=dict(checkpoint=str(cp),checkpoint_sha256=sha(cp),path=str(policy),sha256=sha(policy))
            pinned=s.mass_model(model,out,r['keyset_sha256'])
            self.assertEqual(pinned['mass_sha256'],sha(out/'receipt.json'))
            (out/'zero-keys.bin').write_bytes(b'corruption')
            with self.assertRaises(ValueError):s.mass_model(model,out,r['keyset_sha256'])

    def test_failure_keeps_partial_but_never_publishes_pass_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cp,policy=self.fixture(root,True);out=root/'mass'
            with self.assertRaises(ValueError):audit(cp,policy,1,1,lookup_out=out)
            self.assertTrue(out.exists())
            self.assertFalse((out/'receipt.json').exists())
            with self.assertRaises(FileExistsError):audit(cp,policy,1,1,lookup_out=out)


if __name__=='__main__':unittest.main()
