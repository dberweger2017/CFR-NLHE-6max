"""One frozen menu expansion on PR377's existing diagnostic observations.

Strict-accuracy full-menu comparisons are separate from deployment-target
latency measurements. Neither phase plays hands or updates a blueprint.
"""

import argparse
import hashlib
import json
from pathlib import Path
from statistics import median
from time import monotonic

from scripts.river_search_panel import quantiles
from scripts.river_search_stage2 import Pool


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metric(result):
    evaluation = result["omitted_raise_evaluation"]
    hero = evaluation["hero_game_seat"]
    opponent = 1 - hero
    return {
        "opponent_gain_bb": evaluation["quality"]["best_response_gains_bb"][opponent],
        "blueprint_opponent_gain_bb": evaluation["blueprint_only_quality"]["best_response_gains_bb"][opponent],
        "max_player_gain_bb": max(evaluation["quality"]["best_response_gains_bb"]),
    }


def describe(values):
    return {"median": median(values), "mean": sum(values) / len(values),
            "max": max(values), **quantiles(values)} if values else None


def summarize(records, config):
    arms = config["menus"]
    strict = {(r["case_index"], r["menu"]): r for r in records if r["phase"] == "strict"}
    pairs = []
    for index in sorted({i for i, _ in strict}):
        a, b = (strict[index, arm] for arm in arms)
        qualified = all(x["result"]["checkpoints"][-1]["target_met"] for x in (a, b))
        if a["result"]["law"] != b["result"]["law"]:
            raise ValueError("comparison arms used different belief laws")
        am, bm = metric(a["result"]), metric(b["result"])
        if abs(am["blueprint_opponent_gain_bb"] - bm["blueprint_opponent_gain_bb"]) > 1e-10:
            raise ValueError("comparison arms disagree on the unchanged blueprint")
        pairs.append({"case_index": index, "directory": a["directory"], "hand": a["hand"],
                      "qualified": qualified, "baseline": am, "expanded": bm,
                      "opponent_gain_reduction_bb": am["opponent_gain_bb"] - bm["opponent_gain_bb"],
                      "node_ratio": b["result"]["nodes"] / a["result"]["nodes"]})
    qualified = [p for p in pairs if p["qualified"]]
    reductions = [p["opponent_gain_reduction_bb"] for p in qualified]
    out = {"format": "river-search-round2-comparison-v1", "pairs": len(pairs),
           "qualified_pairs": len(qualified), "inconclusive_pairs": len(pairs) - len(qualified),
           "primary_opponent_gain_reduction_bb": describe(reductions),
           "improved": sum(x > 1e-9 for x in reductions),
           "worsened": sum(x < -1e-9 for x in reductions),
           "unchanged": sum(abs(x) <= 1e-9 for x in reductions),
           "per_case": pairs, "arms": {}}
    for menu, label in zip(arms, ("baseline", "expanded")):
        strict_rows = [r for r in records if r["menu"] == menu and r["phase"] == "strict"]
        deploy = [r for r in records if r["menu"] == menu and r["phase"] == "deployment"]
        out["arms"][menu] = {
            "strict_target_met": sum(r["result"]["checkpoints"][-1]["target_met"] for r in strict_rows),
            "opponent_gain_bb_qualified_pairs": describe([p[label]["opponent_gain_bb"] for p in qualified]),
            "regressions_vs_blueprint_qualified_pairs": sum(
                p[label]["opponent_gain_bb"] > p[label]["blueprint_opponent_gain_bb"] + 1e-9
                for p in qualified),
            "strict_decision_seconds": describe([r["decision_seconds"] for r in strict_rows]),
            "nodes": describe([r["result"]["nodes"] for r in strict_rows]),
            "solver_f64_bytes": describe([r["result"]["solver_memory_bytes"] for r in strict_rows]),
            "deployment_target_met": sum(r["result"]["checkpoints"][-1]["target_met"] for r in deploy),
            "deployment_decision_seconds": describe([r["decision_seconds"] for r in deploy]),
        }
    return out


def run(args):
    config = json.loads(args.config.read_text())
    if digest(args.set) != config["diagnostic_set_sha256"]:
        raise ValueError("diagnostic set differs from the frozen comparison")
    frozen = json.loads(args.set.read_text())
    cases = frozen["cases"]
    if len(cases) != config["cases"]:
        raise ValueError("unexpected case count")
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "config.json").write_bytes(args.config.read_bytes())
    args.sha256 = config["model_sha256"]
    records = []
    started = monotonic()
    pool = Pool(config["workers"], args)
    load_seconds = monotonic() - started
    try:
        for phase in ("strict", "deployment"):
            jobs = []
            for index, case in enumerate(cases):
                # Alternate arm order by case; no cache flushing or reloading.
                menus = config["menus"] if index % 2 == 0 else list(reversed(config["menus"]))
                for menu in menus:
                    work = config[phase]
                    request = {**case["request"], "mode": "solve", "search_menu": menu,
                               "algorithm": config["algorithm"], "sweeps": work["checkpoints"][-1],
                               "checkpoints": work["checkpoints"], "stop_at_target": True,
                               "target": work["target"], "omitted": phase == "strict"}
                    jobs.append((index, case, menu, request))
            # Persist each ordered response, including unsupported roots.
            from concurrent.futures import ThreadPoolExecutor
            with (args.out / f"{phase}.jsonl").open("x") as stream, ThreadPoolExecutor(config["workers"]) as executor:
                responses = executor.map(pool.ask, (j[3] for j in jobs))
                for (index, case, menu, _), response in zip(jobs, responses):
                    row = {"case_index": index, "directory": case["directory"], "hand": case["hand"],
                           "menu": menu, "phase": phase, **response}
                    if response["status"] == "ok":
                        evaluation = response["result"]["omitted_raise_evaluation"]
                        row["decision_seconds"] = response["roundtrip_seconds"] - (evaluation["seconds"] if evaluation else 0.)
                    stream.write(json.dumps(row, separators=(",", ":")) + "\n")
                    stream.flush()
                    if response["status"] != "ok":
                        raise RuntimeError(f"unexpected unsupported comparison root: {response}")
                    records.append(row)
    finally:
        pool.close()
    summary = summarize(records, config)
    summary.update({"config_sha256": digest(args.config), "worker_start_seconds": load_seconds,
                    "wall_seconds": monotonic() - started})
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_case"}, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "set", "out", "binary", "k50", "model"):
        p.add_argument(f"--{name}", type=Path, required=True)
    args = p.parse_args()
    try:
        run(args)
    except Exception as error:
        if args.out.exists():
            (args.out / "failure.json").write_text(json.dumps({"error": str(error)}) + "\n")
        raise


if __name__ == "__main__":
    main()
