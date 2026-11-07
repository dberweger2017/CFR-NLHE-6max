import json
import math
import os
from pathlib import Path
import subprocess
import sys
import signal
import time
import unittest
from tempfile import TemporaryDirectory
from scripts.support import research_process_guard as guard


def healthy():
    return dict(kind="m4", thermal_state="nominal", available_ram_bytes=2**30,
                disk_free_bytes=2**30, pressure=1)


class GuardTests(unittest.TestCase):
    def test_temperature_schema_refuses_missing_nonfinite_and_duplicates(self):
        valid={"cpu":{"Package id 0":{"temp1_input":50}},"vrm":{"Thermistor 15":{"temp15_input":60}}}
        self.assertEqual(guard.linux_temperatures(valid),dict(cpu_c=50,vrm_c=60))
        for bad in [{}, {"cpu":valid["cpu"]}, {"cpu":valid["cpu"],"vrm":{"Thermistor 15":{"a_input":math.nan}}},
                    {"cpu":valid["cpu"],"vrm":{"Thermistor 15":{"a_input":math.inf}}},
                    {"cpu":valid["cpu"],"vrm":{"Thermistor 15":{"a_input":"60"}}},
                    {**valid,"other":valid["cpu"]}]:
            with self.assertRaises(ValueError):guard.linux_temperatures(bad)

    def test_missing_thermal_or_resource_fields_fail_closed(self):
        x=healthy();guard.validate_reading(x)
        for key in x:
            y=dict(x);del y[key]
            with self.assertRaises(ValueError):guard.validate_reading(y)
        for state in [None,"serious","critical","",float("nan")]:
            with self.assertRaises(ValueError):guard.validate_reading(dict(x,thermal_state=state))
        for cpu,vrm in [(math.nan,60),(50,math.inf),(90,60),(50,100),(None,60)]:
            with self.assertRaises(ValueError):guard.validate_reading(dict(x,kind="linux",cpu_c=cpu,vrm_c=vrm))

    def test_rejection_happens_before_child_launch(self):
        with TemporaryDirectory()as d:
            marker=Path(d)/"launched"
            with self.assertRaises(ValueError):guard.run([sys.executable,"-c",f"open({str(marker)!r},'w').write('bad')"],Path(d)/"run",lambda:dict(healthy(),thermal_state=""))
            self.assertFalse(marker.exists());self.assertIsNone(json.loads((Path(d)/"run/receipt.json").read_text())["pid"])

    def test_success_and_nonzero_exit_receipts(self):
        with TemporaryDirectory()as d:
            r=guard.run([sys.executable,"-c","print('ok')"],Path(d)/"ok",healthy,interval=.01)
            self.assertEqual(r["returncode"],0)
            with self.assertRaises(RuntimeError):guard.run([sys.executable,"-c","raise SystemExit(7)"],Path(d)/"bad",healthy,interval=.01)
            self.assertEqual(json.loads((Path(d)/"bad/receipt.json").read_text())["returncode"],7)

    def test_runtime_sensor_failure_kills_entire_group(self):
        with TemporaryDirectory()as d:
            marker=Path(d)/"grandchild"
            grand="import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)"
            parent="import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c',"+repr(grand)+"]);Path("+repr(str(marker))+").write_text(str(p.pid));time.sleep(60)"
            ticks=0
            def probe():
                nonlocal ticks
                ticks+=1
                if marker.exists():return dict(healthy(),thermal_state="missing")
                if ticks>300:raise RuntimeError("fixture child did not start")
                return healthy()
            with self.assertRaises(ValueError):guard.run([sys.executable,"-c",parent],Path(d)/"run",probe,interval=.01)
            pid=int(marker.read_text())
            until=time.monotonic()+2
            while time.monotonic()<until:
                p=subprocess.run(["ps","-o","state=","-p",str(pid)],text=True,capture_output=True)
                if p.returncode or p.stdout.strip().startswith("Z"):break
                time.sleep(.01)
            else:self.fail("owned grandchild still active")
            self.assertIsNotNone(json.loads((Path(d)/"run/receipt.json").read_text())["terminal_failure"])

    def test_owner_stop_and_changed_config_are_terminal(self):
        for mode in ["stop","config"]:
            with TemporaryDirectory()as d:
                stop=Path(d)/"STOP";calls=0
                def unchanged():
                    nonlocal calls
                    calls+=1
                    if calls>=2 and mode=="stop":stop.touch()
                    return calls<2 or mode=="stop"
                with self.assertRaises(ValueError):guard.run([sys.executable,"-c","import time;time.sleep(60)"],Path(d)/"run",healthy,stop=stop,unchanged=unchanged,interval=.01)

    def test_clean_parent_exit_with_live_worker_is_not_success(self):
        with TemporaryDirectory()as d:
            parent="import subprocess,sys;subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])"
            with self.assertRaisesRegex(RuntimeError,"descendants"):
                guard.run([sys.executable,"-c",parent],Path(d)/"run",healthy,interval=.01)

    def test_supervisor_signal_still_stops_owned_child_and_restores_handler(self):
        with TemporaryDirectory()as d:
            before=signal.getsignal(signal.SIGTERM);calls=0
            def probe():
                nonlocal calls
                calls+=1
                if calls==2:os.kill(os.getpid(),signal.SIGTERM)
                return healthy()
            with self.assertRaises(guard.GuardSignal):
                guard.run([sys.executable,"-c","import time;time.sleep(60)"],Path(d)/"run",probe,interval=.01)
            receipt=json.loads((Path(d)/"run/receipt.json").read_text())
            self.assertIsNotNone(receipt["returncode"]);self.assertIn("GuardSignal",receipt["terminal_failure"])
            self.assertEqual(signal.getsignal(signal.SIGTERM),before)


if __name__=="__main__":unittest.main()
