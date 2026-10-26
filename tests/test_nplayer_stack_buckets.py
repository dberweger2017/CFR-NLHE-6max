import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import nplayer_stack_buckets as b


class StackBucketsGuardTests(unittest.TestCase):
    def test_reference_target_and_content_pins_are_frozen(self):
        refs=b.references()
        self.assertEqual([x['target_nodes']for x in refs],b.TARGETS)
        self.assertEqual(refs[-1]['binary_sha256'],'a4de26403d6495de6e21fbb037a9074f64460659a3cda2441b8291eed7d7c928')
        with patch.object(b,'sha',return_value='changed'):
            with self.assertRaisesRegex(ValueError,'reference provenance'):b.references()

    def test_cross_panel_contract_and_inventory_cannot_be_ignored(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp)
            panels={'original':dict(seed=20261026441002,observations=10),
                    'heldout':dict(seed=20261026443002,observations=12),'union':dict(seed=0,observations=22)}
            for n,x in panels.items():
                x.update(protected_contract_violations=0,checkpoint_binary_panel_float64_parity=True)
                (root/(n+'-panel.json')).write_text(json.dumps(x))
            b.panel_barrier(root)
            panels['union']['protected_contract_violations']=1
            (root/'union-panel.json').write_text(json.dumps(panels['union']))
            with self.assertRaisesRegex(ValueError,'contract'):b.panel_barrier(root)
            panels['union'].update(protected_contract_violations=0,observations=21)
            (root/'union-panel.json').write_text(json.dumps(panels['union']))
            with self.assertRaisesRegex(ValueError,'inventory'):b.panel_barrier(root)

    def test_success_barrier_requires_all_six_replays(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp)/'main';calls=[]
            def guarded(folder,c,*,phase,command,owner_stop):
                calls.append(phase)
                if phase=='native-pilot':
                    out=root/'native';out.mkdir()
                    (out/'native-complete.json').write_text(json.dumps(dict(status='native-complete-proof-pending',endpoints=[dict(target_nodes=n,actual_nodes=n)for n in b.TARGETS])))
                    for n in b.TARGETS:
                        d=out/str(n);d.mkdir();(d/'initial.jsonl').write_text('identical');(d/'repeat.jsonl').write_text('identical')
                return dict(returncode=0,phase=phase)
            with patch.object(b.subprocess,'check_output',side_effect=lambda args,**kw:'Apple M4'if args[0]=='sysctl'else'AC Power'),patch.object(b,'validate'),patch.object(b,'panel_barrier'),patch.object(b,'sample',return_value=dict(available_ram_bytes=8*2**30,disk_free_bytes=30*2**30,thermal_state='nominal')),patch.object(b,'run_guarded',side_effect=guarded),patch.object(Path,'home',return_value=Path(tmp)):
                (Path(tmp)/'Local').mkdir()
                b.run('pilot',root,dict(thermal='unused',binary='unused',owner_admission='unused',tables='unused',qualification_sha256='q',source_manifest={}))
            self.assertEqual(calls,['native-pilot']+[f'replay-{n}-{a}'for n in b.TARGETS for a in ['initial','repeat']])
            self.assertEqual(json.loads((root/'COMPLETE.json').read_text())['status'],'passed')

    def test_owner_review_budget_and_scope_refusals(self):
        owner=dict(status='owner-approved',study='PR444',targets=b.TARGETS,seed=b.SEED,max_entries=10_000_000,threads=2,allocation_seconds=1200)
        b.acceptance(owner,dict(pilot_cleared=True),dict(reserved_seconds=1000))
        for name,value in [('seed',1),('max_entries',20_000_000),('threads',4),('allocation_seconds',3600)]:
            with self.assertRaisesRegex(ValueError,'allocation differs'):
                b.acceptance(dict(owner,**{name:value}),dict(pilot_cleared=True),dict(reserved_seconds=1000))
        with self.assertRaisesRegex(ValueError,'review unresolved'):b.acceptance(owner,{},dict(reserved_seconds=1000))
        with self.assertRaisesRegex(ValueError,'exceeds'):b.acceptance(owner,dict(pilot_cleared=True),dict(reserved_seconds=1201))

    def test_replay_failure_is_terminal_and_keeps_complete_absent(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp)/'main';calls=[]
            def guarded(folder,c,*,phase,command,owner_stop):
                calls.append(phase)
                if phase=='native-pilot':
                    out=root/'native';out.mkdir()
                    (out/'native-complete.json').write_text(json.dumps(dict(status='native-complete-proof-pending',endpoints=[dict(target_nodes=n,actual_nodes=n)for n in b.TARGETS])))
                else:raise RuntimeError('replay fixture mismatch')
                return dict(returncode=0,phase=phase)
            with patch.object(b.subprocess,'check_output',side_effect=lambda args,**kw:'Apple M4'if args[0]=='sysctl'else'AC Power'),patch.object(b,'validate'),patch.object(b,'panel_barrier'),patch.object(b,'sample',return_value=dict(available_ram_bytes=8*2**30,disk_free_bytes=30*2**30,thermal_state='nominal')),patch.object(b,'run_guarded',side_effect=guarded),patch.object(Path,'home',return_value=Path(tmp)):
                (Path(tmp)/'Local').mkdir()
                with self.assertRaisesRegex(RuntimeError,'replay fixture'):b.run('pilot',root,dict(thermal='unused',binary='unused',owner_admission='unused',tables='unused'))
            self.assertFalse((root/'COMPLETE.json').exists())
            self.assertTrue(json.loads((root/'failure.json').read_text())['terminal'])
            self.assertEqual(len(calls),2)

    def test_source_mutation_is_rejected_before_reference_reads(self):
        with patch.object(b,'manifest',return_value={'source':'new'}):
            with self.assertRaisesRegex(ValueError,'source differs'):b.validate(dict(source_manifest={'source':'old'}))


if __name__=='__main__':unittest.main()
