"""Stage 2 of the river-search round: capped search menus on the dev panel only.

For each capped menu, every dev decision is classified for tree size and
support, then a fixed slice of the dev panel is solved at fixed work levels.
Each solve reports latency and both players' best-response gains in the
declared (capped, projected) search game. The omitted-raise test separately
measures the deployed policy, capped solution plus blueprint fallback after
an omitted raise, in the full-menu game. Held-out panels are not read.
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Queue
from time import monotonic

from scripts.river_search_panel import Worker, quantiles, wilson

MENUS = ("pot-jam-cap2-v1", "pot-jam-cap3-v1")
SWEEPS = (16, 64, 256)
OMITTED_AT = (64, 256)


def gate(quality, pot_bb):
    """Frozen quality gate: each player's best-response gain within min(1% of pot, 0.1 BB)."""
    limit = min(0.01 * pot_bb, 0.1)
    return all(g <= limit for g in quality["best_response_gains_bb"]), limit


class Pool:
    def __init__(self, size, args):
        self.workers = Queue()
        with ThreadPoolExecutor(size) as starting:
            for worker in starting.map(lambda _: Worker(args.binary, args.k50, args.model, args.sha256), range(size)):
                self.workers.put(worker)
        self.size = size

    def ask(self, request):
        worker = self.workers.get()
        try:
            tick = monotonic()
            response = worker.ask(request)
            response["roundtrip_seconds"] = monotonic() - tick
            return response
        finally:
            self.workers.put(worker)

    def map(self, requests):
        with ThreadPoolExecutor(self.size) as pool:
            return list(pool.map(self.ask, requests))

    def close(self):
        while not self.workers.empty():
            self.workers.get().close()


def classify(pool, eligible, menu):
    responses = pool.map([{**row["request"], "search_menu": menu} for row in eligible])
    if any(r["status"] != "ok" for r in responses):
        raise RuntimeError("a dev root could not be classified")
    results = [r["result"] for r in responses]
    nodes = [r["search_menu"]["nodes"] for r in results if r["search_menu"]["count_complete"]]
    supported = sum(r["supported"] for r in results)
    return {"decisions": len(results), "supported": supported, "supported_share": supported / len(results),
            "supported_share_95ci": wilson(supported, len(results)),
            "rejection_reasons": {reason: sum(any(x["reason"] == reason for x in r["rejections"]) for r in results)
                                  for reason in ("likelihood", "projection", "own-zero-reach", "tree-nodes", "strategy-cells")},
            "nodes": {"max": max(nodes), **quantiles(nodes)},
            "full_menu_nodes": quantiles([r["full_menu"]["nodes"] for r in results if r["full_menu"]["count_complete"]])}


def solve(pool, panel, menu):
    records = []
    for sweeps in SWEEPS:
        requests = [{**row["request"], "mode": "solve", "sweeps": sweeps, "search_menu": menu,
                     "omitted": sweeps in OMITTED_AT} for row in panel]
        for row, response in zip(panel, pool.map(requests)):
            if response["status"] != "ok":
                records.append({"hand": row["hand"], "sweeps": sweeps, "status": "unsupported",
                                "reason": response.get("reason")})
                continue
            result = response["result"]
            pot_bb = sum(p[2] for p in row["request"]["players"]) / 100
            passed, limit = gate(result["quality"], pot_bb)
            omitted = result["omitted_raise_evaluation"]
            evaluation = omitted["seconds"] if omitted else 0.0
            record = {"hand": row["hand"], "sweeps": sweeps, "status": "ok", "nodes": result["nodes"],
                      "pot_bb": pot_bb, "gate_limit_bb": limit, "search_game": result["quality"],
                      "search_game_gate": passed,
                      # The live decision excludes the offline omitted-raise evaluation.
                      "decision_seconds": response["roundtrip_seconds"] - evaluation,
                      "native_timings": result["timings"]}
            if omitted:
                deployed_passed, _ = gate(omitted["quality"], pot_bb)
                record["deployed_full_menu"] = {**omitted, "gate": deployed_passed}
            records.append(record)
    return records


def summarize_solves(records):
    out = {}
    for sweeps in SWEEPS:
        rows = [r for r in records if r["sweeps"] == sweeps and r["status"] == "ok"]
        if not rows:
            continue
        seconds = [r["decision_seconds"] for r in rows]
        gains = [max(r["search_game"]["best_response_gains_bb"]) for r in rows]
        summary = {"supported": len(rows),
                   "unsupported": sum(r["sweeps"] == sweeps and r["status"] != "ok" for r in records),
                   "decision_seconds": {"mean": sum(seconds) / len(seconds), "max": max(seconds), **quantiles(seconds)},
                   "search_game_gate_pass": sum(r["search_game_gate"] for r in rows),
                   "search_game_max_player_gain_bb": quantiles(gains)}
        deployed = [r["deployed_full_menu"] for r in rows if "deployed_full_menu" in r]
        if deployed:
            summary["deployed_full_menu_gate_pass"] = sum(d["gate"] for d in deployed)
            summary["blueprint_only_full_menu_max_player_gain_bb"] = quantiles(
                [max(d["blueprint_only_quality"]["best_response_gains_bb"]) for d in deployed])
            # Paired per decision: positive means the deployed search is less exploitable.
            summary["deployed_improvement_over_blueprint_bb"] = quantiles(
                [max(d["blueprint_only_quality"]["best_response_gains_bb"]) - max(d["quality"]["best_response_gains_bb"])
                 for d in deployed])
            summary["deployed_full_menu_max_player_gain_bb"] = quantiles(
                [max(d["quality"]["best_response_gains_bb"]) for d in deployed])
            summary["omitted_raise_evaluation_seconds"] = quantiles([d["seconds"] for d in deployed])
        out[str(sweeps)] = summary
    return out


def run(args):
    args.out.mkdir(parents=True, exist_ok=False)
    eligible = [json.loads(line) for line in (args.dev / "classified.jsonl").open()]
    panel = [json.loads(line) for line in (args.dev / "panel.jsonl").open()][:args.solve_count]
    summary = {"format": "river-search-stage2-v1", "dev": str(args.dev), "solve_count": len(panel),
               "sweeps": SWEEPS, "omitted_at": OMITTED_AT, "menus": {}}
    tick = monotonic()
    pool = Pool(args.workers, args)
    summary["worker_start_seconds"] = monotonic() - tick
    try:
        for menu in MENUS:
            tick = monotonic()
            classification = classify(pool, eligible, menu)
            classification["seconds"] = monotonic() - tick
            tick = monotonic()
            records = solve(pool, panel, menu)
            with (args.out / f"{menu}.jsonl").open("w") as stream:
                for record in records:
                    stream.write(json.dumps(record, separators=(",", ":")) + "\n")
            summary["menus"][menu] = {"classification": classification, "solves": summarize_solves(records),
                                      "solve_seconds": monotonic() - tick}
            (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    finally:
        pool.close()
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dev", type=Path, help="stage 1 dev panel directory")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--k50", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--solve-count", type=int, default=60)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
