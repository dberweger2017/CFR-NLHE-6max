from pathlib import Path
import tempfile
import unittest

from scripts.nplayer_overnight_thermal_handoff import BOUNDARY, ContinuedScalars, SEED, resume_plan
from scripts.run_nplayer_storage_benchmark import GIB, enforce


def boundary_events():
    events=[dict(event='probe',nodes=n) for n in (2_949_726_632,5_000_001_820,10_000_000_706,15_000_000_100,20_000_000_100)]
    for n in (10_000_000_000,BOUNDARY):
        events.extend([dict(event='trained',target=n,nodes=n+100,active_seconds=3500.,monitor_seconds=.1),
                       dict(event='checkpoint',target=n,path=f'{n}.gz',sha256='a'*64)])
    return events


class ThermalHandoffTests(unittest.TestCase):
    def test_resume_does_not_repeat_saved_training_or_monitoring(self):
        plan=resume_plan(boundary_events())
        self.assertEqual(plan['checkpoint']['target'],BOUNDARY)
        self.assertEqual(plan['targets'],[30_000_000_000])
        self.assertEqual(plan['probe_nodes'],[25_000_000_000,30_000_000_000])

    def test_incomplete_or_duplicate_boundary_refused(self):
        events=boundary_events()
        for invalid in (events[:-1],events+[events[-1]],events[1:]):
            with self.assertRaises(ValueError):resume_plan(invalid)

    def test_new_temperature_boundary_and_unchanged_cpu_stop(self):
        row=dict(temperatures_c={'Package id 0':89.5,'Thermistor 15':99.5},
                 available_ram_bytes=16*GIB,rss_bytes=8*GIB,swap_growth_bytes=0,
                 free_disk_bytes=100_000_000_000)
        enforce(row,0,1,cpu_limit=90,thermistor_limit=100)
        for sensor,value in [('Package id 0',90),('Thermistor 15',100)]:
            altered=dict(row,temperatures_c=dict(row['temperatures_c'],**{sensor:value}))
            with self.assertRaisesRegex(RuntimeError,'thermal stop'):
                enforce(altered,0,1,cpu_limit=90,thermistor_limit=100)

    def test_existing_tensorboard_files_preserved_and_counters_continue(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);original=folder/'events.original';original.write_bytes(b'unchanged')
            writer=ContinuedScalars(folder,dict(active_seconds=3500.,monitor_seconds=.1))
            writer.add(f'{SEED}/training/active_seconds',5.,20_000_000_001)
            writer.close()
            self.assertEqual(original.read_bytes(),b'unchanged')
            self.assertNotEqual(writer.path,original)
            self.assertEqual(writer.offsets[f'{SEED}/training/active_seconds'],3500.)
            self.assertIn(b'active_seconds',writer.path.read_bytes())


if __name__=='__main__':unittest.main()
