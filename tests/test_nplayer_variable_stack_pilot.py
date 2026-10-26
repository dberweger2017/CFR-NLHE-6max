"""Proof/substitution and replay-barrier tests; no poker or training is launched."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_nplayer_variable_stack_pilot as m


def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value))


class Pilot(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.b=Path(self.tmp.name);(self.b/'Local').mkdir()
        self.source=self.b/'source';native='native/hu20-trainer/src/lib.rs'
        p=self.source/native;p.parent.mkdir(parents=True);p.write_text('qualified native')
        self.manifest={native:m.sha(p)}
        qdir=self.b/'qualified';self.q=qdir/'COMPLETE.json'
        original=dict(source_manifest=self.manifest,python_sha256=m.sha(sys.executable))
        put(qdir/'config.json',original)
        put(self.q,dict(status='passed',fixture_only=True,no_pilot_started=True,
            config_sha256=m.sha(qdir/'config.json'),
            source_manifest_sha256=hashlib.sha256(json.dumps(self.manifest,sort_keys=True).encode()).hexdigest()))
        self.exe=self.b/'binary';self.exe.write_bytes(b'qualified executable')
        self.owner=self.b/'owner.json';put(self.owner,dict(status='owner-approved',study='PR441',targets=m.TARGETS,
             seed=m.SEED,max_entries=10_000_000,threads=2,allocation_seconds=3600))
        self.thermal=self.b/'thermal';self.thermal.write_bytes(b'qualified thermal')
        binding=self.b/'binding.json';put(binding,dict(qualification_sha256=m.sha(self.q),
             source_manifest_sha256=json.loads(self.q.read_text())['source_manifest_sha256'],binary_sha256=m.sha(self.exe)))
        self.c=dict(binary=str(self.exe),qualification=str(self.q),owner_admission=str(self.owner),thermal=str(self.thermal),
             binary_binding=str(binding),source_manifest=self.manifest,python_sha256=m.sha(sys.executable),tables=str(self.b/'tables'))
        for name in ['binary','qualification','owner_admission','thermal','binary_binding']:
            self.c[name+'_sha256']=m.sha(self.c[name])
        self.patches=[patch.object(m,'SOURCE',self.source),patch.object(m,'source_manifest',return_value=self.manifest),patch.object(m,'TABLES',{})]
        for p in self.patches:p.start();self.addCleanup(p.stop)

    def test_original_config_and_binding_substitution_are_refused(self):
        m.validate(self.c)
        original=self.q.parent/'config.json';before=original.read_bytes();original.write_text('{}')
        with self.assertRaisesRegex(ValueError,'qualification config'):m.validate(self.c)
        original.write_bytes(before)
        binding=Path(self.c['binary_binding']);x=json.loads(binding.read_text());x['binary_sha256']='0'*64;put(binding,x)
        self.c['binary_binding_sha256']=m.sha(binding)
        with self.assertRaisesRegex(ValueError,'qualified executable'):m.validate(self.c)

    def test_owner_scope_and_python_are_refused(self):
        x=json.loads(self.owner.read_text());x['allocation_seconds']=3599;put(self.owner,x)
        self.c['owner_admission_sha256']=m.sha(self.owner)
        with self.assertRaisesRegex(ValueError,'allocation'):m.validate(self.c)
        x['allocation_seconds']=3600;x['targets']=[1,2,3];put(self.owner,x)
        self.c['owner_admission_sha256']=m.sha(self.owner)
        with self.assertRaisesRegex(ValueError,'allocation'):m.validate(self.c)
        x['targets']=m.TARGETS;put(self.owner,x);self.c['owner_admission_sha256']=m.sha(self.owner)
        self.c['python_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Python'):m.validate(self.c)

    def execute(self,fail=False):
        root=self.b/'run';calls=[]
        def guarded(folder,c,*,phase,command,owner_stop):
            self.assertFalse((root/'COMPLETE.json').exists());calls.append(phase)
            if phase=='native-pilot':
                put(root/'native/native-complete.json',dict(status='native-complete-proof-pending',
                     endpoints=[dict(target_nodes=t,actual_nodes=t)for t in m.TARGETS]))
                for t in m.TARGETS:
                    p=root/'native'/str(t);p.mkdir();(p/'initial.jsonl').write_text('same');(p/'repeat.jsonl').write_text('same')
            if fail and phase=='replay-5000000-repeat':raise RuntimeError('replay failure')
            return dict(phase=phase,returncode=0)
        with patch.object(Path,'home',return_value=self.b),patch.object(m.subprocess,'check_output',side_effect=['Apple M4','AC Power']),patch.object(m,'sample',return_value=dict(available_ram_bytes=7*2**30,disk_free_bytes=20*2**30,thermal_state='nominal')),patch.object(m,'run_guarded',side_effect=guarded):
            if fail:
                with self.assertRaisesRegex(RuntimeError,'replay failure'):m.run(root,self.c)
                self.assertTrue((root/'failure.json').exists());self.assertFalse((root/'COMPLETE.json').exists())
            else:
                m.run(root,self.c)
                self.assertEqual(json.loads((root/'COMPLETE.json').read_text())['status'],'passed')
        return calls

    def test_all_six_replays_precede_complete(self):
        self.assertEqual(self.execute(),['native-pilot']+[f'replay-{t}-{a}'for t in m.TARGETS for a in ['initial','repeat']])

    def test_replay_failure_preserved_without_completion(self):
        self.assertEqual(self.execute(True),['native-pilot','replay-5000000-initial','replay-5000000-repeat'])


if __name__=='__main__':unittest.main()
