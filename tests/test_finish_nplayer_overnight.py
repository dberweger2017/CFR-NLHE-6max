import json
from pathlib import Path
import tempfile
import unittest

from scripts.finish_nplayer_overnight import completed_model,final_seed_plan,SEED
from scripts.nplayer_overnight import evaluation_directory,preserve
from scripts.nplayer_overnight_thermal_handoff import ContinuedScalars


class FinishTests(unittest.TestCase):
    def test_only_remaining_seed_and_saves_are_requested(self):
        events=[dict(event='trained',target=10_000_000_000,nodes=10_000_002_106),
                dict(event='checkpoint',target=10_000_000_000,sha256='a'*64)]
        plan=final_seed_plan(events)
        self.assertEqual(plan['targets'],[20_000_000_000,30_000_000_000])
        self.assertEqual(plan['probe_nodes'],[15_000_000_000,20_000_000_000,25_000_000_000,30_000_000_000])
        with self.assertRaises(ValueError):final_seed_plan(events+[events[-1]])

    def test_reused_model_requires_matching_audit_and_export(self):
        events=[dict(event='trained',nodes=30_000_000_001,entries=100),
                dict(event='checkpoint',target=30_000_000_000,sha256='raw')]
        exported=dict(mode='average',sha256='average')
        audit=dict(status='passed',checkpoint_sha256='raw',policy_sha256='average',strategy='average',last_average_street=3,rows=100)
        self.assertEqual(completed_model(events,exported,audit)['sha256'],'raw')
        for change in [dict(policy_sha256='changed'),dict(rows=99),dict(status='failed')]:
            with self.assertRaises(ValueError):completed_model(events,exported,dict(audit,**change))

    def test_final_traces_are_only_created_in_owned_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run';cache=Path(tmp)/'cache';root.mkdir();cache.mkdir()
            (root/'config.json').write_text(json.dumps({'cache':str(cache)}))
            with self.assertRaisesRegex(ValueError,'owned cache'):
                evaluation_directory(root,{'evaluation_directory':str(Path(tmp)/'elsewhere')})
            evaluation_directory(root,{'evaluation_directory':str(cache/'evaluation')})
            data=root/'evaluation'/'case.json';data.write_text('retained')
            receipts=preserve(root,cache,['evaluation'])
            self.assertEqual(data.read_text(),'retained')
            self.assertEqual(receipts[0]['path'],'evaluation/case.json')
            with self.assertRaises(FileExistsError):evaluation_directory(root,{'evaluation_directory':str(cache/'evaluation')})

    def test_tensorboard_offsets_apply_to_third_seed_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            w=ContinuedScalars(Path(tmp),dict(active_seconds=1523,monitor_seconds=.05),seed=SEED)
            self.assertIn(f'{SEED}/training/active_seconds',w.offsets)
            self.assertNotIn('2026101541/training/active_seconds',w.offsets)
            w.close()


if __name__=='__main__':unittest.main()
