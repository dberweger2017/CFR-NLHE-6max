"""Stage 3 of the river-search round: profiling, the fold-leaf path and DCFR.

Development inputs only: #375's 801-node fixture and the stage 1 dev panel.

1. Profile: phase timing (traversal, fold and showdown leaves, updates,
   quality checks, ranges) on the fixture and on capped dev roots.
2. Fold-leaf fast path: the same requests on the previous binary and the
   current one; distributions must be identical and times are compared.
3. DCFR (alpha 1.5, beta 0, gamma 2) against linear CFR on identical roots,
   menu and beliefs: quality against elapsed time including the checks, and
   roots that never reach the frozen target.
4. The deployable point: each algorithm stopping at the target, with the
   omitted-raise evaluation of the deployed policy.
"""

import argparse
import json
from pathlib import Path
from time import monotonic

from scripts.river_search_panel import quantiles, wilson
from scripts.river_search_stage2 import Pool

MENU = "pot-jam-cap3-v1"
ALGORITHMS = ("linear-cfr", "dcfr-1.5-0-2")
CHECKPOINTS = [8, 16, 32, 64, 128, 256, 512, 1024, 2048]


def solve(request, **fields):
    return {**request, "mode": "solve", **fields}


def ok(response):
    if response["status"] != "ok":
        raise RuntimeError(f"unexpected unsupported root: {response.get('reason')}")
    return response


def profile(pool, fixture, panel):
    rows = []
    cases = [("fixture-801", "full", fixture)] + [(f"dev-{row['hand']}", MENU, row["request"]) for row in panel]
    for algorithm in ALGORITHMS:
        requests = [solve(r, sweeps=256, search_menu=menu, algorithm=algorithm, profile=True)
                    for _, menu, r in cases]
        for (name, menu, _), response in zip(cases, pool.map(requests)):
            result = ok(response)["result"]
            rows.append({"case": name, "menu": menu, "algorithm": algorithm, "nodes": result["nodes"],
                         "native": result["timings"], "solver": result["solver_timing"],
                         "roundtrip_seconds": response["roundtrip_seconds"]})
    return rows


def timed(worker, request):
    tick = monotonic()
    response = ok(worker.ask(request))
    response["roundtrip_seconds"] = monotonic() - tick
    return response


def fold_path(before, after, fixture, panel):
    """Identical linear requests on both binaries, one at a time for clean timing."""
    cases = [("fixture-801", "full", fixture)] + [(f"dev-{row['hand']}", MENU, row["request"]) for row in panel]
    rows = []
    for name, menu, request in cases:
        for sweeps in (64, 256):
            r = solve(request, sweeps=sweeps, search_menu=menu)
            old, new = timed(before, r), timed(after, r)
            same = old["result"]["probabilities"] == new["result"]["probabilities"]
            rows.append({"case": name, "sweeps": sweeps, "identical_distribution": same,
                         "identical_quality": old["result"]["quality"] == new["result"]["quality"],
                         "before_solve_seconds": old["result"]["timings"]["solve_seconds"],
                         "after_solve_seconds": new["result"]["timings"]["solve_seconds"],
                         "before_roundtrip_seconds": old["roundtrip_seconds"],
                         "after_roundtrip_seconds": new["roundtrip_seconds"]})
    return rows


def curves(pool, panel):
    rows = []
    for algorithm in ALGORITHMS:
        requests = [solve(row["request"], sweeps=CHECKPOINTS[-1], checkpoints=CHECKPOINTS,
                          search_menu=MENU, algorithm=algorithm) for row in panel]
        for row, response in zip(panel, pool.map(requests)):
            result = ok(response)["result"]
            first = next((c for c in result["checkpoints"] if c["target_met"]), None)
            rows.append({"hand": row["hand"], "algorithm": algorithm, "target_bb": result["target_bb"],
                         "nodes": result["nodes"], "checkpoints": result["checkpoints"],
                         "first_target_sweeps": first and first["sweeps"],
                         "first_target_elapsed_seconds": first and first["elapsed_seconds"],
                         "fixed_overhead_seconds": result["timings"]["likelihood_seconds"]
                         + result["timings"]["projection_seconds"]
                         + result["timings"]["tree_and_solver_preparation_seconds"]})
    return rows


def deployable(pool, panel):
    rows = []
    for algorithm in ALGORITHMS:
        requests = [solve(row["request"], sweeps=CHECKPOINTS[-1], checkpoints=CHECKPOINTS, stop_at_target=True,
                          search_menu=MENU, algorithm=algorithm, omitted=True) for row in panel]
        for row, response in zip(panel, pool.map(requests)):
            result = ok(response)["result"]
            evaluation = result["omitted_raise_evaluation"]
            limit = result["target_bb"]
            rows.append({"hand": row["hand"], "algorithm": algorithm, "sweeps": result["sweeps"],
                         "target_met": result["checkpoints"][-1]["target_met"], "target_bb": limit,
                         # The live decision excludes the offline omitted-raise evaluation.
                         "decision_seconds": response["roundtrip_seconds"] - evaluation["seconds"],
                         "search_game_gains_bb": result["quality"]["best_response_gains_bb"],
                         "deployed_gains_bb": evaluation["quality"]["best_response_gains_bb"],
                         "deployed_gate": all(g <= limit for g in evaluation["quality"]["best_response_gains_bb"]),
                         "blueprint_only_gains_bb": evaluation["blueprint_only_quality"]["best_response_gains_bb"]})
    return rows


def summarize(profiles, folds, curve_rows, deploy_rows):
    out = {"profile": {}, "fold_path": {}, "curves": {}, "deployable": {}}
    for algorithm in ALGORITHMS:
        for group, pick in (("fixture-801", lambda r: r["case"] == "fixture-801"),
                            ("dev-capped", lambda r: r["case"] != "fixture-801")):
            rows = [r for r in profiles if r["algorithm"] == algorithm and pick(r)]
            keys = ("traversal_excluding_leaves_seconds", "fold_leaf_seconds", "showdown_leaf_seconds", "update_seconds")
            phase = {k: sum(r["solver"][k] for r in rows) / len(rows) for k in keys}
            phase["quality_check_seconds"] = sum(r["native"]["quality_seconds"] for r in rows) / len(rows)
            phase["ranges_seconds"] = sum(r["native"]["likelihood_seconds"] + r["native"]["projection_seconds"]
                                          for r in rows) / len(rows)
            phase["preparation_seconds"] = sum(r["native"]["tree_and_solver_preparation_seconds"] for r in rows) / len(rows)
            phase["mean_nodes"] = sum(r["nodes"] for r in rows) / len(rows)
            out["profile"][f"{group}/{algorithm}"] = phase
    for group, pick in (("fixture-801", lambda r: r["case"] == "fixture-801"),
                        ("dev-capped", lambda r: r["case"] != "fixture-801")):
        rows = [r for r in folds if pick(r)]
        ratios = [r["before_solve_seconds"] / r["after_solve_seconds"] for r in rows]
        out["fold_path"][group] = {"requests": len(rows),
                                   "identical": sum(r["identical_distribution"] and r["identical_quality"] for r in rows),
                                   "solve_speedup": quantiles(ratios, (0.1, 0.5, 0.9))}
    for algorithm in ALGORITHMS:
        rows = [r for r in curve_rows if r["algorithm"] == algorithm]
        reached = [r for r in rows if r["first_target_sweeps"] is not None]
        out["curves"][algorithm] = {
            "roots": len(rows), "reached_target": len(reached),
            "never_reached_by_2048": len(rows) - len(reached),
            "reached_share_95ci": wilson(len(reached), len(rows)),
            "sweeps_to_target": quantiles([r["first_target_sweeps"] for r in reached]),
            "seconds_to_target_including_checks": quantiles([r["first_target_elapsed_seconds"] for r in reached]),
            "max_gain_bb_by_sweeps": {str(c): quantiles([max(r["checkpoints"][i]["best_response_gains_bb"]) for r in rows])
                                      for i, c in enumerate(CHECKPOINTS)},
            "elapsed_seconds_by_sweeps": {str(c): quantiles([r["checkpoints"][i]["elapsed_seconds"] for r in rows])
                                          for i, c in enumerate(CHECKPOINTS)}}
    for algorithm in ALGORITHMS:
        rows = [r for r in deploy_rows if r["algorithm"] == algorithm]
        seconds = [r["decision_seconds"] for r in rows]
        out["deployable"][algorithm] = {
            "roots": len(rows), "search_game_target_met": sum(r["target_met"] for r in rows),
            "decision_seconds": {"mean": sum(seconds) / len(seconds), "max": max(seconds), **quantiles(seconds)},
            "deployed_full_menu_gate": sum(r["deployed_gate"] for r in rows),
            "deployed_max_gain_bb": quantiles([max(r["deployed_gains_bb"]) for r in rows]),
            "blueprint_only_max_gain_bb": quantiles([max(r["blueprint_only_gains_bb"]) for r in rows]),
            "deployed_improvement_over_blueprint_bb": quantiles(
                [max(r["blueprint_only_gains_bb"]) - max(r["deployed_gains_bb"]) for r in rows])}
    return out


def run(args):
    args.out.mkdir(parents=True, exist_ok=False)
    fixture = json.loads(args.fixture.read_text())
    panel = [json.loads(line) for line in (args.dev / "panel.jsonl").open()]
    profiled = panel[:args.profile_count]
    timings = {}
    tick = monotonic()
    pool = Pool(args.workers, args)
    timings["worker_start_seconds"] = monotonic() - tick
    results = {}
    try:
        for name, step in (("profile", lambda: profile(pool, fixture, profiled)),
                           ("curves", lambda: curves(pool, panel)),
                           ("deployable", lambda: deployable(pool, panel))):
            tick = monotonic()
            results[name] = step()
            timings[f"{name}_seconds"] = monotonic() - tick
            with (args.out / f"{name}.jsonl").open("w") as stream:
                for row in results[name]:
                    stream.write(json.dumps(row, separators=(",", ":")) + "\n")
    finally:
        pool.close()
    # Before/after fold-path timing uses one worker each, with nothing else running.
    from scripts.river_search_panel import Worker
    tick = monotonic()
    before = Worker(args.before_binary, args.k50, args.model, args.sha256)
    after = Worker(args.binary, args.k50, args.model, args.sha256)
    try:
        results["fold_path"] = fold_path(before, after, fixture, profiled)
    finally:
        before.close()
        after.close()
    timings["fold_path_seconds"] = monotonic() - tick
    with (args.out / "fold_path.jsonl").open("w") as stream:
        for row in results["fold_path"]:
            stream.write(json.dumps(row, separators=(",", ":")) + "\n")
    summary = {"format": "river-search-stage3-v1", "menu": MENU, "checkpoints": CHECKPOINTS,
               "dev_panel_roots": len(panel), "profiled_roots": len(profiled), "timings": timings,
               **summarize(results["profile"], results["fold_path"], results["curves"], results["deployable"])}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dev", type=Path, help="stage 1 dev panel directory")
    parser.add_argument("--fixture", type=Path, required=True, help="#375 case 2 request (801 nodes)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--before-binary", type=Path, required=True, help="river_live before the fold-leaf path")
    parser.add_argument("--k50", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--profile-count", type=int, default=30)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
