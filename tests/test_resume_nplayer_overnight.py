import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.resume_nplayer_overnight import recovery_plan, remaining_quote, resume
from scripts.nplayer_overnight_thermal_handoff import ContinuationSupervisor, campaign


class RecoveryTests(unittest.TestCase):
    def test_only_saved10b_is_recovered_and_future_endpoints_unchanged(self):
        events=[dict(event='trained',target=10_000_000_000,nodes=10_000_000_706),
                dict(event='checkpoint',target=10_000_000_000,sha256='a'*64),
                dict(event='probe',nodes=15_000_000_123)]
        plan=recovery_plan(events)
        self.assertEqual(plan['targets'],[20_000_000_000,30_000_000_000])
        self.assertEqual(plan['probe_nodes'],[15_000_000_000,20_000_000_000,25_000_000_000,30_000_000_000])
        for bad in (events[:-1],events+[events[1]]):
            with self.assertRaises(ValueError):recovery_plan(bad)

    def test_original_deadline_refuses_unaffordable_recovery(self):
        c={'anchor_nodes':{str(s):3_000_000_000 for s in campaign.SEEDS}}
        p={'trained':{'nodes':10_000_000_000}}
        q=dict(nodes_per_second=5_000_000,save_allowance_seconds=4500,monitoring_seconds=1)
        result=remaining_quote(c,p,dict(nodes_per_second=4_700_000),q,0,36000)
        self.assertEqual(result['remaining_nodes'],74_000_000_000)
        self.assertEqual(result['original_deadline'],36000)
        with self.assertRaisesRegex(RuntimeError,'original-deadline'):
            remaining_quote(c,p,dict(nodes_per_second=4_700_000),q,0,100)

    def test_repeated_probe_must_match_every_retained_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=ContinuationSupervisor.__new__(ContinuationSupervisor)
            s.root=Path(tmp)
            s.seed=campaign.SEEDS[0]
            s.expected_probe=dict(event='probe',nodes=15_000_000_123,iteration=42,blocks=128,results=[{'block_bb100':[1,2]}])
            with patch.object(campaign.guard,'json_event_original',lambda line:json.loads(line),create=True):
                self.assertEqual(s.event(json.dumps(s.expected_probe)),s.expected_probe)
                self.assertTrue((s.root/'resume15b-verified.json').exists())
                bad=dict(s.expected_probe,results=[{'block_bb100':[1,3]}])
                with self.assertRaisesRegex(ValueError,'differs'):s.event(json.dumps(bad))

    def test_existing_swap_is_charged_rather_than_reset(self):
        from scripts.run_nplayer_storage_benchmark import GIB,enforce
        row=dict(temperatures_c={'Package id 0':40,'Thermistor 15':40},available_ram_bytes=16*GIB,
                 rss_bytes=8*GIB,swap_growth_bytes=140816384,free_disk_bytes=100_000_000_000)
        enforce(row,0,1,cpu_limit=90,thermistor_limit=100)
        with self.assertRaisesRegex(RuntimeError,'swap growth'):
            enforce(dict(row,swap_growth_bytes=256*1024**2+1),0,1,cpu_limit=90,thermistor_limit=100)

    def test_existing_recovery_root_is_not_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            origin=Path(tmp)/'original';origin.mkdir()
            root=Path(tmp)/'attempt';root.mkdir()
            marker=root/'failure.json';marker.write_text('original failure')
            with self.assertRaisesRegex(ValueError,'already exists'):resume(origin,root)
            self.assertEqual(marker.read_text(),'original failure')

    def test_original_attempt_bytes_are_charged_to_shared_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            origin=Path(tmp)/'original';origin.mkdir()
            (origin/'config.json').write_text(json.dumps({'cache':'/cache/original'}))
            s=ContinuationSupervisor.__new__(ContinuationSupervisor)
            s.origin=origin;s.cache=Path('/cache/original/resume100');s.external_refresh=0
            s.cpu_limit=90;s.thermistor_limit=100
            sizes={str(origin):100,'/cache/original':1000,str(s.cache):200}
            with patch.object(campaign.guard,'tree_bytes',lambda p:sizes[str(p)]),patch.object(campaign.Supervisor,'sample',return_value={}):
                row=s.sample(None,'test',0)
            self.assertEqual(s.initial_bytes,-100)
            self.assertEqual(s.initial_cache_bytes,-800)
            self.assertEqual(row['thermistor15_stop_c'],100)


if __name__=='__main__':unittest.main()
