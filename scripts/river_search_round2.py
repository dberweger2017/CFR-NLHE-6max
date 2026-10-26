"""River search round 2: where the capped search's full-menu vulnerability comes from.

`freeze` builds a fixed diagnostic set from round 1's measured development
evidence (its dev panel and its former held-out panels, now development
evidence) by a declared rule. `diagnose` solves each case on the cap-3 menu to
a strict target and measures, in the full-menu game, each player's
best-response gain from every omitted action at every on-tree node.
"""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from scripts.river_search_stage2 import Pool

BANDS = ((0, 5), (5, 15), (15, 40), (40, float("inf")))
STRICT_TARGET = {"pot_fraction": 0.002, "cap_bb": 0.02}
STRICT_CHECKPOINTS = [64, 128, 256, 512, 1024, 2048, 4096, 8192]
MENU = "pot-jam-cap3-v1"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def panel(path):
    return {row["hand"]: row for row in map(json.loads, path.open())}


def candidates(round1):
    """Every round 1 root measured with DCFR at the deployment target, with its request."""
    out = []
    dev = panel(round1 / "stage1/panel-2026102101/panel.jsonl")
    for row in map(json.loads, (round1 / "stage3/deployable.jsonl").open()):
        if row["algorithm"] == "dcfr-1.5-0-2":
            out.append({"source": "round1-dev", "directory": "panel-2026102101", "hand": row["hand"],
                        "request": dev[row["hand"]]["request"], "deployed": max(row["deployed_gains_bb"]),
                        "blueprint": max(row["blueprint_only_gains_bb"]), "target_met": row["target_met"]})
    # Round 1 assessed panel 2026102102 then 2026102103, in panel order.
    former = [("panel-2026102102", panel(round1 / "stage1/panel-2026102102/panel.jsonl")),
              ("panel-2026102103", panel(round1 / "stage1/panel-2026102103/panel.jsonl"))]
    rows = list(map(json.loads, (round1 / "stage7/decisions.jsonl").open()))
    for i, row in enumerate(rows):
        directory, requests = former[i // 300]
        result = row["result"]
        evaluation = result["omitted_raise_evaluation"]
        out.append({"source": "round1-former-held-out", "directory": directory, "hand": row["hand"],
                    "request": requests[row["hand"]]["request"],
                    "deployed": max(evaluation["quality"]["best_response_gains_bb"]),
                    "blueprint": max(evaluation["blueprint_only_quality"]["best_response_gains_bb"]),
                    "target_met": result["checkpoints"][-1]["target_met"]})
    for c in out:
        c["pot_bb"] = sum(p[2] for p in c["request"]["players"]) / 100
        c["outcome"] = "regression" if c["deployed"] > c["blueprint"] else "improvement"
    return out


def freeze(args):
    pool = sorted(candidates(args.round1), key=lambda c: (c["directory"], c["hand"]))
    chosen, keys = [], set()

    def take(case, reason):
        key = (case["directory"], case["hand"])
        if key not in keys:
            keys.add(key)
            chosen.append({**case, "reason": reason})

    for low, high in BANDS:
        for outcome in ("regression", "improvement"):
            cell = [c for c in pool if low <= c["pot_bb"] < high and c["outcome"] == outcome]
            for case in cell[:2]:
                take(case, f"pot {low}-{high} BB, {outcome}, lowest hand ids")
    for case in pool:
        if not case["target_met"]:
            take(case, "missed the deployment quality target in round 1")
    take(max(pool, key=lambda c: c["deployed"] - c["blueprint"]), "largest regression against the blueprint")
    take(max(pool, key=lambda c: c["blueprint"] - c["deployed"]), "largest improvement over the blueprint")
    sources = ["stage3/deployable.jsonl", "stage7/decisions.jsonl", "stage1/panel-2026102101/panel.jsonl",
               "stage1/panel-2026102102/panel.jsonl", "stage1/panel-2026102103/panel.jsonl"]
    frozen = {"format": "river-search-round2-diagnostic-set-v1",
              "rule": ("Round 1 roots measured with DCFR at the deployment target (dev panel and former "
                       "held-out panels, now development evidence), sorted by panel and hand. Two per pot "
                       "band x full-menu outcome against the blueprint, then every round 1 quality-target "
                       "miss, then the largest regression and the largest improvement."),
              "bands_bb": [[low, None if high == float("inf") else high] for low, high in BANDS],
              "strict_target": STRICT_TARGET, "strict_checkpoints": STRICT_CHECKPOINTS, "menu": MENU,
              "sources": {s: sha256(args.round1 / s) for s in sources},
              "cases": [{k: c[k] for k in ("source", "directory", "hand", "pot_bb", "outcome", "deployed",
                                          "blueprint", "target_met", "reason", "request")} for c in chosen]}
    args.out.write_text(json.dumps(frozen, indent=2) + "\n")
    print(json.dumps({"cases": len(chosen), "by_reason": [c["reason"] for c in chosen]}, indent=2))


def entry_type(entry, hero):
    kind = {3: "min-raise", 4: "pot-raise", 5: "all-in"}.get(entry["label"], f"label-{entry['label']}")
    return (f"{'hero' if hero else 'opponent'} {'facing a bet' if entry['facing_bet'] else 'unopened'}, "
            f"{kind}, after {entry['river_raises_before']} river raise(s)")


def diagnose(args):
    args.out.mkdir(parents=True, exist_ok=False)
    frozen = json.loads(args.set.read_text())
    requests = [{**c["request"], "mode": "diagnose", "search_menu": frozen["menu"],
                 "checkpoints": frozen["strict_checkpoints"], "target": frozen["strict_target"]}
                for c in frozen["cases"]]
    pool = Pool(args.workers, args)
    try:
        responses = pool.map(requests)
    finally:
        pool.close()
    by_type = defaultdict(lambda: {"increment_bb": 0.0, "entries": 0, "cases": set()})
    cases = []
    with (args.out / "diagnosis.jsonl").open("w") as stream:
        for case, response in zip(frozen["cases"], responses):
            stream.write(json.dumps({"directory": case["directory"], "hand": case["hand"], **response},
                                    separators=(",", ":")) + "\n")
            if response["status"] != "ok":
                cases.append({"hand": case["hand"], "status": "unsupported", "reason": response.get("reason")})
                continue
            result = response["result"]
            row = {"directory": case["directory"], "hand": case["hand"], "pot_bb": case["pot_bb"],
                   "converged": result["search"]["converged"], "nodes": result["search"]["nodes"],
                   "full_menu_nodes": result["full_menu_nodes"], "players": []}
            for player in result["players"]:
                top = sorted(player["entries"], key=lambda e: -e["increment_over_capped_bb"])[:3]
                row["players"].append({
                    "hero": player["hero"], "full_menu_gain_bb": player["full_menu_gain_bb"],
                    "capped_actions_only_gain_bb": player["capped_actions_only_gain_bb"],
                    "blueprint_only_gain_bb": player["blueprint_only_gain_bb"],
                    "top_entries": [{"type": entry_type(e, player["hero"]), "path": e["path"], "action": e["action"],
                                     "increment_bb": e["increment_over_capped_bb"]} for e in top]})
                if result["search"]["converged"]:
                    for e in player["entries"]:
                        t = by_type[entry_type(e, player["hero"])]
                        t["increment_bb"] += max(e["increment_over_capped_bb"], 0.0)
                        t["entries"] += 1
                        t["cases"].add((case["directory"], case["hand"]))
            cases.append(row)
    ranking = sorted(({"type": k, "increment_bb": v["increment_bb"], "entries": v["entries"],
                       "cases": len(v["cases"])} for k, v in by_type.items()), key=lambda r: -r["increment_bb"])
    summary = {"format": "river-search-round2-diagnosis-v1", "set_sha256": sha256(args.set),
               "converged": sum(c.get("converged", False) for c in cases), "cases": len(cases),
               "entry_type_ranking": ranking, "per_case": cases}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("converged", "cases")} | {"top": ranking[:8]}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--round1", type=Path, required=True, help="round 1 evidence folder")
    f.add_argument("--out", type=Path, required=True)
    d = sub.add_parser("diagnose")
    d.add_argument("--set", type=Path, required=True)
    d.add_argument("--out", type=Path, required=True)
    for name in ("binary", "k50", "model"):
        d.add_argument(f"--{name}", type=Path, required=True)
    d.add_argument("--sha256", required=True)
    d.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()
    {"freeze": freeze, "diagnose": diagnose}[args.command](args)


if __name__ == "__main__":
    main()
