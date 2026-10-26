"""Linux process ownership regressions; these never train or play poker."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from scripts.guarded_process_group import live_group_members


def until(predicate, seconds=10):
    end = time.monotonic()+seconds
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(.02)
    raise AssertionError('owned process did not reach expected state')


@unittest.skipUnless(sys.platform == 'linux', 'Linux guardian integration')
class GroupOwnershipTests(unittest.TestCase):
    def test_exited_command_cannot_leave_term_resistant_descendant(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            code = "import signal,time,os;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path(%r).write_text(str(os.getpid()));time.sleep(60)" % str(root/'descendant.pid')
            parent = ("import subprocess,sys,time;from pathlib import Path;"
                      "subprocess.Popen([sys.executable,'-c',%r]);"
                      "\nwhile not Path(%r).exists():time.sleep(.01)\n" % (code, str(root/'descendant.pid')))
            p = subprocess.Popen([sys.executable,'-m','scripts.guarded_process_group',str(root),'--',sys.executable,'-c',parent], start_new_session=True)
            try:
                self.assertNotEqual(p.wait(timeout=10), 0)
                until(lambda:not live_group_members(p.pid))
                receipt = json.loads((root/'group-termination.json').read_text())
                self.assertIn(int((root/'descendant.pid').read_text()), receipt['members'])
            finally:
                if live_group_members(p.pid):os.killpg(p.pid,signal.SIGKILL)
                p.wait()

    def test_guardian_death_kills_complete_stage_group(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            code = "import signal,time,os;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path(%r).write_text(str(os.getpid()));time.sleep(60)" % str(root/'descendant.pid')
            guardian = '''import os,sys,json
from pathlib import Path
from scripts import run_nplayer_storage_benchmark as g
root=Path(sys.argv[1]);command=json.loads(sys.argv[2])
class Probe(g.Supervisor):
 def sample(self,*a):return dict(rss_bytes=0)
with (root/'lock').open('w') as lock:
 s=Probe(root,lock.fileno(),cpus=os.sched_getaffinity(0),protect_group=True)
 s.execute('stage',command,Path.cwd(),dict(os.environ,RAYON_NUM_THREADS='1'))
'''
            command=[sys.executable,'-c',code]
            p=subprocess.Popen([sys.executable,'-c',guardian,str(root),json.dumps(command)],start_new_session=True)
            group=None
            try:
                until(lambda:(root/'descendant.pid').exists())
                pid=int((root/'descendant.pid').read_text());group=os.getpgid(pid)
                os.kill(p.pid,signal.SIGKILL);p.wait(timeout=10)
                until(lambda:not live_group_members(group))
                self.assertTrue((root/'measurements/stage/group-termination.json').exists())
            finally:
                if p.poll() is None:p.kill();p.wait()
                if group and live_group_members(group):os.killpg(group,signal.SIGKILL)
