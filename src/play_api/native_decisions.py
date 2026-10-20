"""Client for the native 2–6 seat decision service (`examples/nplayer_serve.rs`).

The play service deals and keeps the authoritative Python hand. For each bot
decision it sends the deck and action record; the native engine replays them,
checks the Python legal set and chip state against its own, and gives the
agent only the acting seat's observation.
"""

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

from src.game.types import Action, ActionKind

BINARY = Path(__file__).resolve().parents[2] / "native/hu20-trainer/target/release/examples/nplayer_serve"
FORMAT = "nplayer-decision-service-v1"
SCRIPTS = ("random", "check-call", "tight-aggressive", "pot-pressure")
RANKS, SUITS = "23456789TJQKA", "cdhs"


def card_index(name: str) -> int:
    return RANKS.index(name[0]) * 4 + SUITS.index(name[1])


def card_name(index: int) -> str:
    return RANKS[index // 4] + SUITS[index % 4]


def native_action(action: Action) -> list:
    return [action.kind.value, action.raise_to or 0]


def python_action(pair) -> Action:
    kind = ActionKind(pair[0])
    return Action(kind, pair[1] if kind == ActionKind.RAISE else None)


def expectation(view) -> dict:
    """The Python engine's view of the acting decision, checked natively."""
    legal = view.legal_actions
    raising = ActionKind.RAISE in legal.kinds
    return {"legal": {"check": ActionKind.CHECK in legal.kinds, "call": legal.call_amount,
                      "raise_to": [legal.min_raise_to, legal.max_raise_to] if raising else None},
            "players": [[p.stack, p.street_bet, p.contributed, p.folded] for p in view.players]}


class NativeError(RuntimeError):
    pass


class NativeDecisions:
    """One long-lived service process; policies load once and are shared by seats."""

    def __init__(self, *, card_buckets: Path | None = None, policies: dict | None = None,
                 binary: Path = BINARY):
        if not binary.is_file():
            raise FileNotFoundError(
                f"{binary} is missing; build it with "
                "`cargo build --release --example nplayer_serve` in native/hu20-trainer")
        command = [str(binary), "serve"]
        if card_buckets is not None:
            command += ["--card-buckets", str(card_buckets)]
        for name, (path, sha256) in (policies or {}).items():
            command += ["--policy", name, str(path), sha256]
        self.lock = threading.Lock()
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, bufsize=1)
        line = self.process.stdout.readline()
        if not line:
            error = self.process.stderr.read().strip()
            self.process.wait()
            raise NativeError(error or "native decision service exited during startup")
        self.ready = json.loads(line)
        if self.ready.get("format") != FORMAT or self.ready.get("ok") is not True:
            self.close()
            raise NativeError("unexpected native decision service")

    @property
    def policies(self) -> dict:
        return self.ready["policies"]

    def _call(self, request: dict) -> dict:
        with self.lock:
            if self.process.poll() is not None:
                raise NativeError("native decision service is not running")
            self.process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
            self.process.stdin.flush()
            line = self.process.stdout.readline()
        if not line:
            raise NativeError("native decision service stopped")
        response = json.loads(line)
        if response.get("ok") is not True:
            raise NativeError(response.get("error", "native decision failed"))
        return response

    def decide(self, hand: dict, seat: int, agent: str, *, seed: int = 0, expect: dict | None = None) -> dict:
        return self._call({"op": "decide", "hand": hand, "seat": seat, "agent": agent,
                           "seed": seed, "expect": expect})

    def settle(self, hand: dict) -> dict:
        return self._call({"op": "settle", "hand": hand})

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        for stream in (self.process.stdout, self.process.stderr):
            if stream and not stream.closed:
                stream.close()
