"""River-search panels from three-player self-play traces.

Stage 1 of the river-search round: every river decision in a native
`nplayer_policy play` trace is counted by type, every first-river decision with
two live non-all-in players is classified by the native worker without solving,
and fixed random panels are drawn for tuning (dev) and judging (held-out).
Requests carry only public history and the acting seat's own holding.
"""

import argparse
import hashlib
import json
import math
import subprocess
from collections import Counter
from pathlib import Path
from random import Random

STREETS = ("preflop", "flop", "turn", "river")


def river_decisions(hand):
    """(index, kind) for each river decision, with the public request when eligible."""
    actions = [e for e in hand["history"] if e[1] != "board"]
    seen_river = False
    for index, state in enumerate(hand["states"][:-1]):
        if state["street"] != "river":
            continue
        first = not seen_river
        seen_river = True
        players = state["players"]
        live = [s for s, p in enumerate(players) if not p[3]]
        all_in = [s for s in live if players[s][0] == 0]
        if len(live) == 3:
            kind = "three-live" + ("-one-all-in" if all_in else "")
        else:
            # Only a river shove leaves a heads-up decision facing an all-in.
            kind = "heads-up" + ("-facing-all-in" if all_in else "")
        kind += "-first" if first else "-later"
        request = None
        if kind == "heads-up-first":
            seat = hand["actors"][index]
            legal = state["legal"]
            request = {"format": "nplayer-live-river-v1", "mode": "classify", "button": hand["button"],
                       "board": state["board"], "seat": seat, "hole": sorted(state["holes"][seat]),
                       "actions": [[e[1], STREETS.index(e[0]), e[2], e[3], e[4]] for e in actions[:index]],
                       "players": players,
                       "legal": {"check": legal["check"], "call_amount": legal["call"],
                                 "raise_to": legal["raise_to"]}}
        yield index, kind, request


def extract(trace):
    with trace.open() as stream:
        header = json.loads(next(stream))
        if header["format"] != "nplayer-privileged-policy-replay-v1" or header["identity"]["players"] != 3:
            raise ValueError("expected a three-player policy replay trace")
        counts, eligible, hands, river_hands = Counter(), [], 0, 0
        for line in stream:
            hand = json.loads(line)
            hands += 1
            reached = False
            for index, kind, request in river_decisions(hand):
                reached = True
                counts[kind] += 1
                if request is not None:
                    eligible.append({"hand": hand["hand"], "decision": index, "request": request})
            river_hands += reached
    if hands != header["hands"]:
        raise ValueError("trace is incomplete")
    return header, {"hands": hands, "hands_with_river_decision": river_hands, "decisions": dict(counts)}, eligible


class Worker:
    def __init__(self, binary, k50, model, sha256):
        self.process = subprocess.Popen([str(binary), str(k50), str(model), sha256], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, text=True)
        self.ready = json.loads(self.process.stdout.readline())
        if self.ready.get("status") != "ready" or self.ready.get("model_sha256") != sha256:
            raise RuntimeError("river worker did not start with the pinned model")

    def ask(self, request):
        self.process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("river worker stopped")
        return json.loads(line)

    def close(self):
        self.process.stdin.close()
        if self.process.wait(timeout=60):
            raise RuntimeError("river worker failed")


def wilson(successes, n, z=1.96):
    if n == 0:
        return None
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [centre - half, centre + half]


def quantiles(values, points=(0.5, 0.9, 0.95, 0.99)):
    ordered = sorted(values)
    return {f"p{round(100 * q)}": ordered[min(len(ordered) - 1, int(q * len(ordered)))] for q in points} if ordered else {}


def summarize(classified):
    """Support, rejection reasons and tree sizes; uncounted trees are reported as such."""
    n = len(classified)
    supported = sum(row["result"]["supported"] for row in classified)
    reasons = Counter(r["reason"] for row in classified for r in row["result"]["rejections"])
    only = Counter("+".join(sorted({r["reason"] for r in row["result"]["rejections"]})) or "supported"
                   for row in classified)
    counted = [row["result"]["full_menu"]["nodes"] for row in classified if row["result"]["full_menu"]["count_complete"]]
    tv = [row["result"]["law"]["projection_total_variation"] for row in classified if row["result"]["law"]]
    return {"decisions": n, "supported_by_375_limits": supported, "supported_share": supported / n if n else None,
            "supported_share_95ci": wilson(supported, n), "rejection_reasons": dict(reasons),
            "rejection_combinations": dict(only),
            "full_menu_nodes": {"counted": len(counted), "over_count_cap": n - len(counted),
                                "count_cap": classified[0]["result"]["full_menu"]["count_cap"] if n else None,
                                **quantiles(counted)},
            "projection_total_variation": quantiles(tv),
            "classification_seconds": quantiles([row["worker_seconds"] for row in classified])}


def run(args):
    args.out.mkdir(parents=True, exist_ok=False)
    header, composition, eligible = extract(args.trace)
    trace_sha = hashlib.sha256(args.trace.read_bytes()).hexdigest()
    worker = Worker(args.binary, args.k50, args.model, args.sha256)
    classified = []
    with (args.out / "classified.jsonl").open("w") as stream:
        for row in eligible:
            response = worker.ask(row["request"])
            if response["status"] != "ok":
                raise RuntimeError(f"classification refused hand {row['hand']}: {response.get('reason')}")
            row = {**row, "result": response["result"], "worker_seconds": response["worker_seconds_before_serialization"]}
            classified.append(row)
            stream.write(json.dumps(row, separators=(",", ":")) + "\n")
    worker.close()
    # The panel draw is fixed by its declared seed before any solving.
    panel = sorted(Random(args.panel_seed).sample(range(len(eligible)), min(args.panel_size, len(eligible))))
    with (args.out / "panel.jsonl").open("w") as stream:
        for i in panel:
            stream.write(json.dumps({k: eligible[i][k] for k in ("hand", "decision", "request")},
                                    separators=(",", ":")) + "\n")
    report = {"format": "river-search-panel-v1", "role": args.role, "trace": str(args.trace),
              "trace_sha256": trace_sha, "trace_seed": header["seed"], "model_sha256": args.sha256,
              "worker": worker.ready, "composition": composition,
              "eligible_first_heads_up": summarize(classified),
              "panel": {"seed": args.panel_seed, "size": len(panel),
                        "sha256": hashlib.sha256((args.out / "panel.jsonl").read_bytes()).hexdigest(),
                        "summary": summarize([classified[i] for i in panel])}}
    (args.out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"role": args.role, "composition": composition,
                      "supported_share": report["eligible_first_heads_up"]["supported_share"]}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("--role", choices=("dev", "held-out"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--k50", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--panel-seed", type=int, required=True)
    parser.add_argument("--panel-size", type=int, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
