"""Stages 6 and 7 of the river-search round: belief controls and the held-out assessment.

`pilot` sizes the exact-joint controls on dev roots only. `controls` and
`heldout` read every setting from the frozen configuration and judge the
held-out panels once; nothing is tuned after they run.
"""

import argparse
import hashlib
import json
from pathlib import Path
from time import monotonic

from scripts.river_search_panel import Worker, quantiles, wilson
from scripts.river_search_stage2 import Pool


def load_panel(path):
    return [json.loads(line) for line in path.open()]


def control_request(row, config, reference_checkpoints, tolerance):
    return {**row["request"], "mode": "belief-control", "search_menu": config["menu"],
            "checkpoints": config["checkpoints"], "reference_checkpoints": reference_checkpoints,
            "reference_tolerance_bb": tolerance}


def run_controls(worker, rows, config, reference_checkpoints, tolerance, out, mode="w"):
    results = []
    with out.open(mode) as stream:
        for row in rows:
            tick = monotonic()
            response = worker.ask(control_request(row, config, reference_checkpoints, tolerance))
            record = {"hand": row["hand"], "status": response["status"], "roundtrip_seconds": monotonic() - tick}
            if response["status"] == "ok":
                record["result"] = response["result"]
            else:
                record["reason"] = response.get("reason")
            results.append(record)
            stream.write(json.dumps(record, separators=(",", ":")) + "\n")
            stream.flush()
    return results


def summarize_controls(results):
    ok = [r["result"] for r in results if r["status"] == "ok"]
    qualified = [r for r in ok if r["reference"]["qualified"]]
    return {"controls": len(results), "unsupported": len(results) - len(ok), "references_qualified": len(qualified),
            "passes": sum(r["passes"] for r in ok),
            "verdict": ("inconclusive" if len(qualified) < len(results)
                        else "pass" if all(r["passes"] for r in ok) else "fail"),
            "max_excess_gain_bb": quantiles([max(r["excess_gain_bb"]) for r in qualified], (0.5, 0.9, 1.0)),
            "reference_error_bb": quantiles([max(r["reference"]["exact_game_quality"]["best_response_gains_bb"])
                                             for r in ok], (0.5, 0.9, 1.0)),
            "reference_sweeps": quantiles([r["reference"]["sweeps"] for r in ok], (0.5, 0.9, 1.0)),
            "reference_seconds": quantiles([r["reference"]["seconds"] for r in ok], (0.5, 0.9, 1.0)),
            "projection_total_variation": quantiles([r["law"]["projection_total_variation"] for r in ok], (0.5, 0.9, 1.0)),
            "deployed_gain_projected_vs_exact_bb": {
                "projected": quantiles([max(r["deployed"]["projected_game_quality"]["best_response_gains_bb"]) for r in ok], (0.5, 0.9)),
                "exact": quantiles([max(r["deployed"]["exact_game_quality"]["best_response_gains_bb"]) for r in ok], (0.5, 0.9))}}


def pilot(args):
    args.out.mkdir(parents=True, exist_ok=False)
    config = json.loads(args.config.read_text())
    rows = load_panel(args.dev / "panel.jsonl")[:args.count]
    worker = Worker(args.binary, args.k50, args.model, args.sha256)
    try:
        results = run_controls(worker, rows, config, args.reference_checkpoints, args.tolerance,
                               args.out / "pilot.jsonl")
    finally:
        worker.close()
    summary = {"format": "river-search-belief-pilot-v1", "dev": str(args.dev), "count": len(rows),
               "reference_checkpoints": args.reference_checkpoints, "tolerance_bb": args.tolerance,
               **summarize_controls(results),
               "roundtrip_seconds": quantiles([r["roundtrip_seconds"] for r in results], (0.5, 0.9, 1.0))}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def frozen(args):
    config = json.loads(args.config.read_text())
    panels = []
    for entry in config["held_out_panels"]:
        path = args.stage1 / entry["directory"] / "panel.jsonl"
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"held-out panel {path} differs from the frozen configuration")
        panels.append(load_panel(path))
    return config, panels


def controls(args):
    config, panels = frozen(args)
    # Frozen rule: the first control_count / 2 roots of each held-out panel, in panel order.
    half = config["control_count"] // 2
    rows = [row for panel in panels for row in panel[:half]]
    path = args.out / "controls.jsonl"
    previous = []
    if args.resume:
        # An interrupted run keeps its completed controls; only the rest are run,
        # unchanged, after checking the kept ones are the frozen rule's prefix.
        previous = [json.loads(line) for line in path.open()]
        if [r["hand"] for r in previous] != [row["hand"] for row in rows[:len(previous)]]:
            raise ValueError("kept controls are not the frozen rule's prefix")
    else:
        args.out.mkdir(parents=True, exist_ok=False)
    worker = Worker(args.binary, args.k50, args.model, args.sha256)
    try:
        results = previous + run_controls(worker, rows[len(previous):], config, config["reference_checkpoints"],
                                          config["reference_tolerance_bb"], path, "a" if args.resume else "w")
    finally:
        worker.close()
    summary = {"format": "river-search-belief-controls-v1", "config_sha256":
               hashlib.sha256(args.config.read_bytes()).hexdigest(), **summarize_controls(results)}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def heldout(args):
    args.out.mkdir(parents=True, exist_ok=False)
    config, panels = frozen(args)
    rows = [row for panel in panels for row in panel]
    eligible = [json.loads(line) for entry in config["held_out_panels"]
                for line in (args.stage1 / entry["directory"] / "classified.jsonl").open()]
    pool = Pool(args.workers, args)
    try:
        coverage = pool.map([{**row["request"], "search_menu": config["menu"]} for row in eligible])
        requests = [{**row["request"], "mode": "solve", "search_menu": config["menu"], "algorithm": config["algorithm"],
                     "sweeps": config["checkpoints"][-1], "checkpoints": config["checkpoints"],
                     "stop_at_target": True, "omitted": True} for row in rows]
        responses = pool.map(requests)
    finally:
        pool.close()
    with (args.out / "decisions.jsonl").open("w") as stream:
        for row, response in zip(rows, responses):
            stream.write(json.dumps({"hand": row["hand"], **response}, separators=(",", ":")) + "\n")
    supported = sum(r["status"] == "ok" and r["result"]["supported"] for r in coverage)
    solved = [r["result"] for r in responses if r["status"] == "ok"]
    seconds = [r["roundtrip_seconds"] - r["result"]["omitted_raise_evaluation"]["seconds"]
               for r in responses if r["status"] == "ok"]
    met = sum(r["checkpoints"][-1]["target_met"] for r in solved)
    deployed = [max(r["omitted_raise_evaluation"]["quality"]["best_response_gains_bb"]) for r in solved]
    blueprint = [max(r["omitted_raise_evaluation"]["blueprint_only_quality"]["best_response_gains_bb"]) for r in solved]
    deployed_gate = sum(all(g <= r["target_bb"] for g in r["omitted_raise_evaluation"]["quality"]["best_response_gains_bb"])
                        for r in solved)
    median = quantiles(seconds, (0.5,))["p50"]
    p95 = quantiles(seconds, (0.95,))["p95"]
    summary = {
        "format": "river-search-heldout-v1", "config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
        "concurrent_workers": args.workers,
        "coverage": {"eligible_decisions": len(eligible), "supported": supported,
                     "share": supported / len(eligible), "share_95ci": wilson(supported, len(eligible)),
                     "panel_solved": len(solved), "panel_roots": len(rows),
                     "gate": "pass" if supported / len(eligible) >= 0.9 else "fail"},
        "latency": {"median": median, "p95": p95, "mean": sum(seconds) / len(seconds), "max": max(seconds),
                    "gate": "pass" if median <= 0.5 and p95 <= 2 else "fail"},
        "search_game_quality": {"target_met": met, "roots": len(solved), "share_95ci": wilson(met, len(solved)),
                                "sweeps": quantiles([r["sweeps"] for r in solved], (0.5, 0.9, 1.0)),
                                # Frozen reading: the gate applies to every held-out decision.
                                "gate": "pass" if met == len(solved) == len(rows) else "fail"},
        "full_menu_reported_separately": {
            "deployed_gate_met": deployed_gate, "deployed_max_gain_bb": quantiles(deployed),
            "blueprint_only_max_gain_bb": quantiles(blueprint),
            "deployed_worse_than_blueprint": sum(d > b for d, b in zip(deployed, blueprint)),
            "paired_improvement_bb": quantiles([b - d for d, b in zip(deployed, blueprint)], (0.1, 0.5, 0.9))}}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("pilot", "controls", "heldout"):
        p = sub.add_parser(name)
        p.add_argument("--config", type=Path, required=True)
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--binary", type=Path, required=True)
        p.add_argument("--k50", type=Path, required=True)
        p.add_argument("--model", type=Path, required=True)
        p.add_argument("--sha256", required=True)
        if name == "controls":
            p.add_argument("--resume", action="store_true")
        if name == "pilot":
            p.add_argument("--dev", type=Path, required=True)
            p.add_argument("--count", type=int, default=6)
            p.add_argument("--reference-checkpoints", type=json.loads, required=True)
            p.add_argument("--tolerance", type=float, required=True)
        else:
            p.add_argument("--stage1", type=Path, required=True)
            p.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    {"pilot": pilot, "controls": controls, "heldout": heldout}[args.command](args)


if __name__ == "__main__":
    main()
