"""One reviewed M4 research qualification; measured budget acceptance precedes main."""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.nplayer_four_player_feasibility import TABLES, sample, sha, write
from scripts.nplayer_variable_stack_qualification import source_manifest
from scripts.support.research_process_guard import run as guarded

SOURCE = Path(__file__).resolve().parents[1]
SEED = 20261028456011
EXTRAS = ["docs/nplayer-passive-learning-qualification.md", "tests/test_research_process_guard.py",
          "tests/test_nplayer_passive_learning_qualification.py"]


def manifest():
    result = source_manifest(SOURCE)
    result.update({p: sha(SOURCE/p) for p in EXTRAS})
    return result


def digest(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate(c, *, main=False):
    if c["study"] != "PR457" or c["source_files"] != manifest():
        raise ValueError("study/frozen source differs")
    if sha(sys.executable) != c["python_sha256"]:
        raise ValueError("Python changed")
    for name in ["binary", "thermal", "review"]:
        if sha(c[name]) != c[name+"_sha256"]:
            raise ValueError(name+" changed")
    for name, pin in TABLES.items():
        if sha(Path(c["tables"])/name) != pin:
            raise ValueError("K50 changed")
    review = json.loads(Path(c["review"]).read_text())
    if (review.get("status") != "approved" or review.get("study") != "PR457"
            or review.get("source_sha256") != digest(c["source_files"])
            or review.get("binary_sha256") != c["binary_sha256"]
            or not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip()
            or review.get("scope") != "perturbed-policy-math-information-qualification-v1"
            or review.get("unresolved") != []):
        raise ValueError("independent code/binary review unresolved")
    if main:
        for name in ["calibration", "owner"]:
            if sha(c[name]) != c[name+"_sha256"]:
                raise ValueError(name+" changed")
        q = json.loads(Path(c["calibration"]).read_text())
        parent = Path(c["calibration"]).parent
        complete = json.loads((parent/"COMPLETE.json").read_text())
        status = json.loads((parent/"status.json").read_text())
        stages = json.loads((parent/"stage-costs.json").read_text())
        if ((parent/"failure.json").exists() or complete.get("status") != "quoted"
                or complete.get("quote_sha256") != c["calibration_sha256"]
                or status.get("status") != "complete" or not stages
                or any(s.get("returncode") != 0 for s in stages)):
            raise ValueError("calibration did not settle successfully")
        owner = json.loads(Path(c["owner"]).read_text())
        if (q["status"] != "quoted" or q["binary_sha256"] != c["binary_sha256"]
                or q["source_sha256"] != digest(c["source_files"])):
            raise ValueError("calibration/source/executable binding differs")
        acceptance(owner, q)


def acceptance(owner, quote):
    if (owner.get("study") != "PR457" or owner.get("status") != "owner-approved"
            or owner.get("seed") != SEED or owner.get("targets") != [128, 512]
            or owner.get("cap") != 2_000_000 or owner.get("threads") != 2
            or owner.get("epsilon") != .02 or owner.get("watch_hands") != 512):
        raise ValueError("fixed owner scope differs")
    seconds = owner.get("allocation_seconds")
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < quote["reserved_seconds"]:
        raise ValueError("accepted allocation below measured reserve")


def comparable(x):
    if isinstance(x, dict):
        return {k: comparable(v) for k, v in x.items()
                if k != "mode" and not k.endswith("_seconds") and k != "row_copy_retained"}
    if isinstance(x, list):
        return [comparable(v) for v in x]
    return x


def evidence_proxy(w):
    thresholds = [("retained_nonzero_regret_roots", "regret"), ("retained_positive_average_roots", "average")]
    passed = True
    for roots, kind in thresholds:
        count = w[roots]
        if not isinstance(count, int) or not 0 <= count <= w["all_root_contexts"]:
            raise ValueError("invalid distinct-root count")
        passed &= count >= 4
        for weighting in ["raw", "linear"]:
            m = w[f"{kind}_{weighting}_coefficients"]
            values = [m[k] for k in ["sum", "sum_squares", "ess"]]
            if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in values):
                raise ValueError("invalid coefficient moments")
            if m["events"] != count:
                raise ValueError("coefficient root denominator differs")
            ess = (m["sum"] / math.sqrt(m["sum_squares"]))**2 if m["sum_squares"] else 0
            if not math.isclose(ess, m["ess"], rel_tol=1e-10, abs_tol=1e-10):
                raise ValueError("coefficient ESS arithmetic differs")
            passed &= m["ess"] >= 4  # same declared float64 boundary as the native ledger
    if bool(w["replicated_learning_proxy"]) != bool(passed):
        raise ValueError("reported per-key proxy differs")
    return bool(passed)


def proxy(w):
    all_evidence = dict(w, replicated_learning_proxy=w["all_history_key_proxy"])
    evidence_proxy(all_evidence)
    names = ["P0", "P1", "P2", "other", "merged-families"]
    families = w["by_actual_training_family"]
    if set(families) != set(names):
        raise ValueError("watch contributing-family inventory differs")
    qualified = []
    targets = w["public_watch_metadata"]["families"]
    for i, name in enumerate(names):
        x = families[name]
        if x["all_root_contexts"] != w["all_root_contexts"]:
            raise ValueError("family root denominator differs")
        ok = evidence_proxy(x)
        if i <= 2 and i in targets and ok:
            qualified.append(name)
    for key in ["encountered_root_groups", "retained_root_groups", "declined_root_groups",
                "retained_nonzero_regret_roots", "retained_positive_average_roots"]:
        if sum(families[name][key] for name in names) != w[key]:
            raise ValueError("watch family attribution differs")
    if w["qualifying_target_families"] != qualified or bool(w["replicated_learning_proxy"]) != bool(qualified):
        raise ValueError("target-family proxy differs")
    return bool(qualified)


def verify(initial, repeat):
    if initial["status"] != "native-complete-proof-pending" or repeat["status"] != initial["status"]:
        raise ValueError("native completion absent")
    if comparable(initial) != comparable(repeat):
        raise ValueError("root/row/learning reproduction differs")
    if [x["name"] for x in initial["arms"]] != ["control", "exploration"]:
        raise ValueError("arm inventory differs")
    for arm in initial["arms"]:
        if [e["iteration"] for e in arm["endpoints"]] != [128, 512]:
            raise ValueError("endpoint inventory differs")
        for e in arm["endpoints"]:
            l = e["learning"]
            if len(l["watch"]) != l["watch_keys"] or len(l["cells"]) != 20:
                raise ValueError("zero/sparse inventory differs")
            if l["all_root_contexts"] != e["iteration"]*3*8 or l["admitted_rows"] != e["entries"]:
                raise ValueError("root/admission denominator differs")
            if len({w["key"] for w in l["watch"]}) != l["watch_keys"]:
                raise ValueError("duplicate watch key")
            qualified = 0
            for w in l["watch"]:
                if w["all_root_contexts"] != l["all_root_contexts"]:
                    raise ValueError("watch root denominator differs")
                qualified += proxy(w)
            if qualified != l["qualified_retained_watch_keys"]:
                raise ValueError("qualified watch count differs")
            cells = {(x["street"], x["family"]) for x in l["cells"]}
            if cells != {(s, f) for s in range(4) for f in ["P0", "P1", "P2", "other", "merged-families"]}:
                raise ValueError("family/street inventory differs")
            audit = e["row_audit"]
            if len(audit["by_street"]) != 4 or any(len(x) != 5 for x in audit["by_street"]):
                raise ValueError("row street inventory differs")
            if sum(x[0] for x in audit["by_street"]) != e["entries"] or sum(x[3] for x in audit["by_street"]) != l["fully_zero_final_rows"]:
                raise ValueError("row audit/admission differs")
    a, b = [arm["endpoints"][-1]["learning"] for arm in initial["arms"]]
    if [w["key"] for w in a["watch"]] != [w["key"] for w in b["watch"]]:
        raise ValueError("fixed watch inventory differs")
    count_a, count_b = a["qualified_retained_watch_keys"], b["qualified_retained_watch_keys"]
    zero_a = a["fully_zero_final_rows"] / max(1, a["admitted_rows"])
    zero_b = b["fully_zero_final_rows"] / max(1, b["admitted_rows"])
    signal = count_b >= 5 and count_b-count_a >= 5 and zero_b-zero_a <= .05
    return dict(status="settled", no_strength_claim=True, no_automatic_extension=True,
                control_proxy_keys=count_a, exploration_proxy_keys=count_b,
                control_zero_final_share=zero_a, exploration_zero_final_share=zero_b,
                small_qualification_signal=signal,
                interpretation="Research heuristic only; inspect magnitudes and sparse-path limits before proposing mature work.")


def pricing(native, cost, source, binary):
    endpoints = [e for arm in native["arms"] for e in arm["endpoints"]]
    train = sum(e["added_training_seconds"] for e in endpoints)
    row_rate = max(e["row_proof"]["write_or_hash_seconds"] / max(1, e["entries"]) for e in endpoints)
    nonrow = sum(max(0, e["readout_seconds"]-e["row_proof"]["write_or_hash_seconds"]) for e in endpoints)
    startup = native["startup_and_watch_seconds"]*8  # 512 vs 64 fixed watched hands
    rows = row_rate*4*2_100_000  # 2 arms x 2 endpoints, whole-sweep overshoot scenario
    central = 2*(startup+train*32*2+rows+nonrow*8)+60
    reserve = 2*(startup*2+train*32*4+rows*3+nonrow*16)+300
    return dict(status="quoted", source_sha256=digest(source), binary_sha256=binary,
                central_seconds=central, reserved_seconds=reserve, calibration_stage=cost,
                projected_main_family_rss_bytes=5*2**30, ram_headroom_bytes=2**30,
                projected_new_main_bytes=4*2**30, disk_headroom_bytes=4*2**30,
                main_started=False, explicit_budget_acceptance_required=True,
                assumptions="Fixed sweep count, two fresh processes with hash-only row reproduction. Training scales16 to512 sweeps with2x/4x larger-table scenarios; row cost assumes2.1M per endpoint, 3x reserve; watch/metadata64 to512. Not a completion guarantee, power forecast or mature-model rate.")


def reach_scenarios():
    n = 512*3*8
    rows = []
    for menu in [2, 5]:
        for blocked in [1, 2, 4, 6]:
            p = (.02/menu)**blocked
            rows.append(dict(menu_actions=menu, persistent_zero_base_opponent_actions=blocked,
                             root_opportunities=n, conditional_path_probability=p,
                             generous_expected_root_hits=n*p,
                             four_hit_probability_union_upper_bound=min(1, math.comb(n, 4)*p**4)))
    return dict(status="ex-ante-conditional-scenarios", rows=rows,
                limits="Assumes base probability stays zero at each named opponent action and all other chance/key/history conditions have probability one. Independent identical root opportunities; union bound via E[choose(hits,4)]. This is not the adaptive experiment's power or a bound when base probabilities learn or multiple histories share a key.")


def run(mode, root, c):
    if "Apple M4" not in subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True):
        raise ValueError("M4 only")
    if "AC Power" not in subprocess.check_output(["pmset", "-g", "batt"], text=True):
        raise ValueError("AC required")
    root.mkdir(parents=True, exist_ok=False)
    write(root/"config.json", c)
    config_pin = sha(root/"config.json")
    locks = []
    clock = time.monotonic()
    stages = []
    try:
        for path in [Path.home()/"Local/.hu20-m4-research.lock", root.parent/".passive-learning.lock"]:
            f = path.open("a+"); locks.append(f)
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        validate(c, main=mode == "main")
        before = sample(root, c["thermal"])
        ram, disk = (5, 4) if mode == "main" else (3, 2)
        write(root/"admission.json", dict(sample=before, forecast_family_rss_bytes=ram*2**30,
              ram_headroom_bytes=2**30, forecast_new_bytes=disk*2**30, disk_headroom_bytes=4*2**30))
        if before["available_ram_bytes"] < (ram+1)*2**30 or before["disk_free_bytes"] < (disk+4)*2**30:
            raise ValueError("fresh forecast/headroom unavailable")

        def stage(name, native_mode):
            active = {"pid": None}
            def probe():
                return dict(sample(root, c["thermal"], active["pid"]), kind="m4")
            native = dict(mode=native_mode, seed=SEED if mode == "main" else 20261028456021,
                          cap=2_000_000 if mode == "main" else 100_000,
                          targets=[128, 512] if mode == "main" else [8, 16],
                          watch_hands=512 if mode == "main" else 64, threads=2, tables=c["tables"],
                          review_approved=True, owner_approved=mode == "main", out=str(root/name/"native"))
            out = root/name; out.mkdir()
            write(out/"manifest.json", native)
            write(root/"status.json", dict(status="running", stage=name))
            receipt = guarded([c["binary"], out/"manifest.json"], out/"guard", probe,
                              stop=root/"STOP", unchanged=lambda: sha(root/"config.json")==config_pin and sha(c["thermal"])==c["thermal_sha256"],
                              on_start=lambda pid: active.update(pid=pid))
            stages.append(dict(stage=name, **receipt));write(root/"stage-costs.json", stages)
            return json.loads((out/"native/native-complete.json").read_text())

        if mode == "calibrate":
            native = stage("calibration", "calibrate")
            validate(c)
            quote = pricing(native, stages[0], c["source_files"], c["binary_sha256"])
            write(root/"quote.json", quote)
            write(root/"COMPLETE.json", dict(status="quoted", quote_sha256=sha(root/"quote.json"), main_started=False))
        else:
            initial = stage("initial", "initial")
            repeat = stage("repeat", "repeat")
            result = verify(initial, repeat)
            validate(c, main=True)
            write(root/"results.json", result)
            write(root/"COMPLETE.json", dict(status="passed", result_sha256=sha(root/"results.json"),
                  initial_proof_sha256=sha(root/"initial/native/native-complete.json"),
                  repeat_proof_sha256=sha(root/"repeat/native/native-complete.json"),
                  no_strength_claim=True, no_automatic_extension=True))
        write(root/"status.json", dict(status="complete", mode=mode))
    except BaseException as e:
        write(root/"failure.json", dict(error=repr(e), terminal=True, no_retry=True));raise
    finally:
        write(root/"WRAPPER-COST.json", dict(wall_seconds=time.monotonic()-clock, stages=stages))
        for f in reversed(locks):f.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["calibrate", "main"])
    p.add_argument("root", type=Path)
    p.add_argument("config", type=Path)
    a = p.parse_args()
    run(a.mode, a.root, json.loads(a.config.read_text()))


if __name__ == "__main__":
    main()
