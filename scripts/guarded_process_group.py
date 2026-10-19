"""Keep a guarded stage's complete process group tied to its guardian parent."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def live_group_members(pgid):
    members = []
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(')', 1)[1].split()
            if fields[0] != 'Z' and int(fields[2]) == pgid:
                members.append(int(path.parent.name))
        except (OSError, ValueError):
            continue
    return members


def run(folder, command):
    pgid = os.getpgrp()
    if pgid != os.getpid():
        raise RuntimeError('guarded wrapper must lead its own process group')
    def terminate(signum, frame):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            (folder/'group-termination.json').write_text(json.dumps(dict(
                at=time.time(), signal=signum, pid=os.getpid(), members=live_group_members(pgid))))
        finally:
            os.killpg(pgid, signal.SIGKILL)
    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    # The guardian sets PR_SET_PDEATHSIG before exec. No descendants exist before
    # handlers are ready, so death during Python startup cannot orphan science.
    if os.getppid() == 1:
        terminate(signal.SIGTERM, None)
    child = subprocess.Popen(command)
    code = child.wait()
    if any(pid != os.getpid() for pid in live_group_members(pgid)):
        print('guarded command exited with live descendants; terminating owned group', file=sys.stderr, flush=True)
        terminate(signal.SIGTERM, None)
    return code if code >= 0 else 128-code


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder', type=Path)
    p.add_argument('command', nargs=argparse.REMAINDER)
    args = p.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        p.error('missing guarded command')
    sys.exit(run(args.folder, command))
