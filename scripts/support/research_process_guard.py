"""Finite Unix research child supervision. Never substitutes missing sensors with zero."""
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time


class GuardSignal(BaseException):
    pass


def linux_temperatures(data):
    found = {"Package id 0": [], "Thermistor 15": []}
    if not isinstance(data, dict):
        raise ValueError("invalid sensors object")
    for chip in data.values():
        if not isinstance(chip, dict):
            continue
        for label in found:
            feature = chip.get(label)
            if isinstance(feature, dict):
                found[label].extend(v for k, v in feature.items() if k.endswith("_input"))
    result = {}
    for label, key in [("Package id 0", "cpu_c"), ("Thermistor 15", "vrm_c")]:
        values = found[label]
        if len(values) != 1 or isinstance(values[0], bool) or not isinstance(values[0], (float, int)) or not math.isfinite(values[0]):
            raise ValueError("missing/invalid/ambiguous temperature: " + label)
        result[key] = values[0]
    return result


def validate_reading(x):
    if x.get("kind") == "m4":
        if x.get("thermal_state") not in ("nominal", "fair"):
            raise ValueError("missing/invalid/unsafe M4 thermal state")
    elif x.get("kind") == "linux":
        for key, limit in [("cpu_c", 90), ("vrm_c", 100)]:
            v = x.get(key)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v >= limit:
                raise ValueError("missing/nonfinite/unsafe " + key)
    else:
        raise ValueError("unknown thermal schema")
    for key, floor in [("available_ram_bytes", 512 * 2**20), ("disk_free_bytes", 256 * 2**20)]:
        v = x.get(key)
        if isinstance(v, bool) or not isinstance(v, int) or v < floor:
            raise ValueError("missing/invalid/exhausted " + key)
    if not isinstance(x.get("pressure"), int) or isinstance(x["pressure"], bool) or not 0 <= x["pressure"] < 4:
        raise ValueError("missing/invalid/unsafe memory pressure")


def _group_states(pid):
    p = subprocess.run(["ps", "-axo", "pid=,pgid=,state="], text=True, capture_output=True, timeout=5)
    if p.returncode:
        raise RuntimeError("cannot inspect owned process group")
    return [fields[2] for line in p.stdout.splitlines()
            if len(fields := line.split()) == 3 and fields[1] == str(pid)]


def _terminate_group(child):
    # The direct child is not reaped until after both signals. Its PID therefore
    # cannot be recycled between group creation and final escalation.
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(child.pid, sig)
        except ProcessLookupError:
            pass
        except PermissionError:
            # Darwin can return EPERM for a group containing only zombies.
            # Do not reinterpret an active/inaccessible group as terminated.
            states = _group_states(child.pid)
            if not states or any(not state.startswith("Z") for state in states):
                raise
            break
    return child.wait()


def _exited_without_reaping(pid):
    if hasattr(os, "waitid") and hasattr(os, "WNOWAIT"):
        return os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
    if sys.platform == "darwin":
        # Darwin's Python may expose wait constants but not waitid. A zombie
        # remains our unreaped child, preserving the process-group identity.
        p = subprocess.run(["ps", "-o", "state=", "-p", str(pid)], text=True, capture_output=True, timeout=5)
        state = p.stdout.strip()
        if p.returncode or not state or state[0] not in "SRIDUTZ":
            raise RuntimeError("cannot inspect owned child state")
        return state[0] == "Z"
    raise RuntimeError("non-reaping child inspection unavailable")


def run(command, root, probe, *, stop=None, unchanged=lambda: True, interval=0.5, on_start=None):
    """A new owned session/group per command; no retries or elapsed/RSS/swap cap.

    Stops signal the entire owned group and reap the direct child. Grandchildren
    are terminated by the group signal; the OS may reap orphan zombies later.
    Receipts do not claim we can waitpid children owned by another process.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.monotonic()
    child = None
    failure = None
    peak = 0
    handlers = {}
    try:
        def interrupted(signum, _frame):
            raise GuardSignal("supervisor signal: " + str(signum))
        for sig in (signal.SIGTERM, signal.SIGHUP):
            handlers[sig] = signal.signal(sig, interrupted)
        initial = probe()
        validate_reading(initial)
        if not unchanged() or (stop is not None and Path(stop).exists()):
            raise ValueError("config changed or owner STOP")
        with (root / "stdout.log").open("x") as out, (root / "stderr.log").open("x") as err, (root / "resources.jsonl").open("x") as resources:
            resources.write(json.dumps(initial, allow_nan=False) + "\n")
            resources.flush()
            child = subprocess.Popen([str(x) for x in command], stdout=out, stderr=err, start_new_session=True)
            if on_start is not None:
                on_start(child.pid)
            # waitid with WNOWAIT retains the leader until our final group
            # cleanup. Supported research hosts are Unix with this primitive.
            while True:
                x = probe()
                validate_reading(x)
                peak = max(peak, x.get("worker_family_rss_bytes", 0))
                resources.write(json.dumps(x, allow_nan=False) + "\n")
                resources.flush()
                if not unchanged() or (stop is not None and Path(stop).exists()):
                    raise ValueError("config changed or owner STOP")
                if _exited_without_reaping(child.pid):
                    states = _group_states(child.pid)
                    if not states or any(not state.startswith("Z") for state in states):
                        raise RuntimeError("parent exited with active or unverifiable owned descendants")
                    code = _terminate_group(child)
                    if code:
                        raise RuntimeError("child failed: " + str(code))
                    break
                time.sleep(interval)
    except BaseException as e:
        failure = repr(e)
        if child is not None and child.returncode is None:
            _terminate_group(child)
        raise
    finally:
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        receipt = dict(command=[str(x) for x in command], pid=child.pid if child else None,
                       process_group=child.pid if child else None, returncode=child.returncode if child else None,
                       terminal_failure=failure, wall_seconds=time.monotonic()-start,
                       sampled_peak_family_rss_bytes=peak,
                       user_cpu_seconds=after.ru_utime-before.ru_utime,
                       system_cpu_seconds=after.ru_stime-before.ru_stime,
                       cpu_scope="Direct-child wait accounting; do not assume totals for orphan descendants.")
        (root / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
    return receipt
