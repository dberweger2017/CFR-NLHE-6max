"""Durable 2–6 seat tables: at most one human, native policies and scripted bots.

The Python hand is authoritative and journals every deal seed, action and bot
sampling seed. Every bot decision is made by the native decision service on
the same deck and record, after it confirms both engines agree on the legal
set and chip state. Completed hands are also settled natively and compared.
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from random import Random

from src.arena.runner import public_events
from src.arena.schedule import digest
from src.game.hand import Hand, Table
from src.game.types import Action, ActionKind
from src.play_api.native_decisions import (FORMAT as DECISION_FORMAT, SCRIPTS, card_name, expectation,
                                           native_action, python_action)
from src.play_api.service import PRESETS, PlayError, _events, _json, _rng

API_VERSION = "nseat-play-api-v1"
BUTTON_SCHEDULE = "rotating-seat-0-first-v1"
STACKS_BB = (20, 100, 200)
# Native `min-pot-conditional-jam-v1` menu labels.
MENU_LABELS = {0: "Fold", 1: "Check", 2: "Call", 3: "Min raise", 4: "Pot", 5: "All-in"}


@dataclass(frozen=True)
class SeatTable:
    """Fixed per server: one agent per physical seat, equal stacks reset every hand."""

    agents: tuple[str, ...]
    stack: int = 10000
    small_blind: int = 50
    big_blind: int = 100
    chip_unit: str = "0.01"

    def __post_init__(self):
        object.__setattr__(self, "agents", tuple(self.agents))
        if not 2 <= len(self.agents) <= 6:
            raise ValueError("Tables have 2–6 seats")
        for agent in self.agents:
            kind, _, name = agent.partition(":")
            if not (agent == "human" or (kind == "policy" and name)
                    or (kind == "script" and name in SCRIPTS)):
                raise ValueError(f"Unknown seat agent {agent!r}")
        if self.agents.count("human") > 1:
            raise ValueError("At most one human seat")
        if (type(self.stack) is not int or self.stack not in tuple(100 * bb for bb in STACKS_BB)
                or (self.small_blind, self.big_blind, self.chip_unit) != (50, 100, "0.01")):
            raise ValueError("Tables use 20, 100 or 200 BB stacks and 50/100 blinds")

    @property
    def players(self) -> int:
        return len(self.agents)

    @property
    def human(self) -> int | None:
        return self.agents.index("human") if "human" in self.agents else None

    def record(self):
        return {**asdict(self), "agents": list(self.agents)}

    def table(self, button: int) -> Table:
        return Table(tuple(f"seat{i}" for i in range(self.players)), (self.stack,) * self.players,
                     button=button, small_blind=self.small_blind, big_blind=self.big_blind,
                     chip_unit=self.chip_unit)


def deck_for(seed: int) -> list[int]:
    deck = list(range(52))
    Random(seed).shuffle(deck)
    return deck


class TableService:
    def __init__(self, db_path: Path, table: SeatTable, decisions, *, source_version: str = "unknown"):
        self.table = table
        self.decisions = decisions
        self.source_version = source_version
        seats = []
        for seat, agent in enumerate(table.agents):
            pin = None
            if agent.startswith("policy:"):
                pin = decisions.policies.get(agent[len("policy:"):])
                identity = pin and pin["identity"]
                if (identity is None or identity["players"] != table.players
                        or identity["stacks"] != [table.stack] * table.players
                        or (identity["small_blind"], identity["big_blind"]) != (table.small_blind, table.big_blind)):
                    raise ValueError(f"Seat {seat} policy is not loaded for this table configuration")
            seats.append({"seat": seat, "agent": agent, "pin": pin})
        self.identity = {"apiVersion": API_VERSION, "table": table.record(), "seats": seats,
                         "buttonSchedule": BUTTON_SCHEDULE, "decisionService": DECISION_FORMAT,
                         "schema": decisions.ready["schema"], "menu": decisions.ready["menu"],
                         "cardTables": decisions.ready["card_tables"]}
        self.lock = threading.RLock()
        db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(db_path.parent, 0o700)
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        os.chmod(db_path, 0o600)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, state TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS operations (key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, response TEXT NOT NULL)")
        self.db.commit()

    def close(self):
        self.db.close()

    def model_info(self):
        return self.identity

    def benchmark_result(self, *_):
        raise PlayError("Multi-seat tables have no human benchmark yet", 404)

    diagnostics = end_benchmark = benchmark_result

    # Journal replay -------------------------------------------------------

    def _hand(self, row, upto=None) -> Hand:
        cards = tuple(card_name(c) for c in deck_for(row["dealSeed"]))
        hand = Hand.from_deck(self.table.table(row["button"]), hand_id=row["handId"], deck=cards)
        for record in row["actions"][:upto]:
            if hand.actor != record["seat"]:
                raise RuntimeError("Private journal actor mismatch")
            hand = hand.apply(Action(ActionKind(record["kind"]), record["raiseTo"]))
        return hand

    def _native_hand(self, row, upto=None) -> dict:
        return {"stacks": [self.table.stack] * self.table.players, "sb": self.table.small_blind,
                "bb": self.table.big_blind, "button": row["button"], "deck": deck_for(row["dealSeed"]),
                "actions": [native_action(Action(ActionKind(r["kind"]), r["raiseTo"]))
                            for r in row["actions"][:upto]]}

    def _load(self, session_id):
        row = self.db.execute("SELECT state FROM sessions WHERE id=?", (session_id,)).fetchone()
        if row is None:
            raise PlayError("Unknown session", 404)
        state = json.loads(row[0])
        if state["identity"] != self.identity:
            raise PlayError("Session table or seat identities differ from this server", 409)
        return state

    def _mutate(self, key, fingerprint, session_id, operation):
        if not isinstance(key, str) or not 16 <= len(key) <= 128 or not key.isascii():
            raise PlayError("Invalid idempotency key")
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                prior = self.db.execute("SELECT fingerprint,response FROM operations WHERE key=?", (key,)).fetchone()
                if prior is not None:
                    if prior[0] != fingerprint:
                        raise PlayError("Idempotency key conflicts with an earlier request", 409)
                    if json.loads(prior[1])["table"] != self.identity:
                        raise PlayError("Acknowledgment belongs to another table", 409)
                    self.db.commit()
                    return json.loads(prior[1])
                state = self._load(session_id) if session_id else None
                state, response = operation(state)
                self.db.execute("INSERT OR REPLACE INTO sessions (id,state) VALUES (?,?)",
                                (state["sessionId"], _json(state)))
                self.db.execute("INSERT INTO operations (key,fingerprint,response) VALUES (?,?,?)",
                                (key, fingerprint, _json(response)))
                self.db.commit()
                return response
            except Exception:
                self.db.rollback()
                raise

    @staticmethod
    def _check_revision(state, body, keys, *, hand=True):
        if set(body) != keys or type(body.get("revision")) is not int:
            raise PlayError("Invalid request fields")
        if body["revision"] != state["revision"]:
            raise PlayError("Stale state revision", 409)
        if hand and (state["current"] is None or body.get("handId") != state["current"]["handId"]):
            raise PlayError("Stale or unknown hand", 409)

    # Operations -------------------------------------------------------------

    def create(self, key, body):
        if set(body) != {"playMode"} or body["playMode"] not in ("restricted", "free"):
            raise PlayError("Choose a valid play mode")
        if body["playMode"] == "free" and any(a.startswith("policy:") for a in self.table.agents):
            # Policy keys include every raise size; an off-menu size is an unseen key.
            raise PlayError("Model seats need restricted sizing until n-player action translation exists")
        if self.table.human is None and body["playMode"] != "restricted":
            raise PlayError("Bot-only tables have no human sizing to choose")

        def operation(_):
            deals, bots = Random(secrets.randbits(256)).getstate(), Random(secrets.randbits(256)).getstate()
            # The starting generator states let an audit re-derive every deal and bot seed.
            state = {"sessionId": secrets.token_urlsafe(18), "playMode": body["playMode"],
                     "revision": 0, "handsPlayed": 0, "totals": [0] * self.table.players,
                     "dealRng": deals, "botRng": bots, "dealRngStart": deals, "botRngStart": bots,
                     "current": None, "history": [], "sourceVersion": self.source_version,
                     "identity": self.identity}
            return state, self._view(state)

        return self._mutate(key, _json(["create", body]), None, operation)

    def state(self, session_id):
        with self.lock:
            return self._view(self._load(session_id))

    def new_hand(self, session_id, key, body):
        def operation(state):
            self._check_revision(state, body, {"revision"}, hand=False)
            if state["current"] is not None and not state["current"].get("completed"):
                raise PlayError("Finish the current hand first", 409)
            deals = _rng(state["dealRng"])
            state["current"] = {"handId": secrets.token_urlsafe(18), "number": state["handsPlayed"],
                                "button": state["handsPlayed"] % self.table.players,
                                "dealSeed": deals.randrange(2**63), "actions": []}
            state["dealRng"] = deals.getstate()
            state["revision"] += 1
            return state, self._view(state)

        return self._mutate(key, _json(["new-hand", session_id, body]), session_id, operation)

    def _menu(self, row, hand, seat):
        view = hand.observe(seat)
        response = self.decisions.decide(self._native_hand(row), seat, "menu", expect=expectation(view))
        return [(MENU_LABELS[label], python_action(pair)) for label, pair in zip(response["labels"], response["menu"])]

    def act(self, session_id, key, body):
        def operation(state):
            self._check_revision(state, body, {"handId", "revision", "kind", "raiseTo"})
            row = state["current"]
            hand = self._hand(row)
            human = self.table.human
            if human is None or hand.finished or hand.actor != human:
                raise PlayError("It is not your turn", 409)
            if body["kind"] not in tuple(k.value for k in ActionKind):
                raise PlayError("Invalid action")
            amount = body["raiseTo"]
            if body["kind"] == "raise" and type(amount) is not int:
                raise PlayError("Raise-to must be an exact integer chip amount")
            if body["kind"] != "raise" and amount is not None:
                raise PlayError("Only raises have a raise-to amount")
            try:
                action = Action(ActionKind(body["kind"]), amount)
                hand.observe(human).legal_actions.validate(action)
            except (TypeError, ValueError) as exc:
                raise PlayError("Action is not legal at this decision") from exc
            if state["playMode"] == "restricted" and action not in [a for _, a in self._menu(row, hand, human)]:
                raise PlayError("Action is outside the restricted menu")
            row["actions"].append(self._record(hand, action, "human"))
            state["revision"] += 1
            self._complete(state)
            return state, self._view(state)

        return self._mutate(key, _json(["action", session_id, body]), session_id, operation)

    def advance(self, session_id, key, body):
        """Exactly one bot decision, so clients can show each seat acting in turn."""
        def operation(state):
            self._check_revision(state, body, {"handId", "revision"})
            row = state["current"]
            hand = self._hand(row)
            if hand.finished or hand.actor == self.table.human:
                raise PlayError("No bot is acting", 409)
            seat = hand.actor
            agent = self.table.agents[seat]
            bot = _rng(state["botRng"])
            seed = bot.getrandbits(63)
            view = hand.observe(seat)
            decision = self.decisions.decide(self._native_hand(row), seat, agent, seed=seed,
                                             expect=expectation(view))
            action = python_action(decision["action"])
            view.legal_actions.validate(action)
            row["actions"].append(self._record(hand, action, agent, {
                "seed": seed, "menu": decision["menu"], "probabilities": decision["probabilities"],
                "trained": decision["trained"]}))
            state["botRng"] = bot.getstate()
            state["revision"] += 1
            self._complete(state)
            return state, self._view(state)

        return self._mutate(key, _json(["advance", session_id, body]), session_id, operation)

    @staticmethod
    def _record(hand, action, agent, decision=None):
        legal = hand.observe(hand.actor).legal_actions
        record = {"seat": hand.actor, "agent": agent, "kind": action.kind.value, "raiseTo": action.raise_to,
                  "street": hand.observe(hand.actor).street.value,
                  "legal": {"kinds": [kind.value for kind in legal.kinds], "call": legal.call_amount,
                            "minRaiseTo": legal.min_raise_to, "maxRaiseTo": legal.max_raise_to}}
        if decision is not None:
            record["decision"] = decision
        return record

    def _settle(self, row, hand):
        final = hand.observe(0)
        chips = [p.stack - self.table.stack for p in final.players]
        native = self.decisions.settle(self._native_hand(row))
        if sum(chips) != 0 or native["rewards"] != chips:
            raise RuntimeError("Python and native settlements differ")
        return chips

    def _complete(self, state):
        row = state["current"]
        hand = self._hand(row)
        if not hand.finished or row.get("completed"):
            return
        row["chips"] = self._settle(row, hand)
        row["completed"] = True
        row["publicEventsSha256"] = digest(public_events(hand.events))
        row["apiVersion"] = API_VERSION
        row["sourceVersion"] = state["sourceVersion"]
        row["playMode"] = state["playMode"]
        state["history"].append(row)
        state["handsPlayed"] += 1
        state["totals"] = [a + b for a, b in zip(state["totals"], row["chips"])]

    # Views ---------------------------------------------------------------------

    def _presets(self, view, seat):
        legal = view.legal_actions
        if ActionKind.RAISE not in legal.kinds:
            return []
        matched = view.players[seat].street_bet + legal.call_amount
        after_call = view.pot + legal.call_amount
        result = []
        for label, num, den in PRESETS:
            target = matched + (after_call * num * 2 + den) // (2 * den)
            result.append({"label": label, "raiseTo": target,
                           "available": legal.min_raise_to <= target <= legal.max_raise_to})
        result.append({"label": "All-in", "raiseTo": legal.max_raise_to, "available": True})
        return result

    def _view(self, state):
        human = self.table.human
        response = {"sessionId": state["sessionId"], "revision": state["revision"],
                    "playMode": state["playMode"], "table": self.identity, "humanSeat": human,
                    "handsPlayed": state["handsPlayed"], "totals": state["totals"],
                    "phase": "ready" if state["current"] is None else "playing", "hand": None}
        row = state["current"]
        if row is None:
            return response
        hand = self._hand(row)
        # Bot-only tables reveal every seat, so seat 0 serves as the public view.
        view = hand.observe(0 if human is None else human)
        own_turn = not hand.finished and human is not None and hand.actor == human
        # A bot-only table has no hidden information to protect from its viewer.
        revealed = range(self.table.players) if human is None else (human,)
        holes = {seat: list(hand.observe(seat).hole_cards) for seat in revealed}
        menu = self._menu(row, hand, human) if own_turn and state["playMode"] == "restricted" else []
        legal = view.legal_actions
        response["phase"] = "finished" if hand.finished else "playing"
        response["hand"] = {
            "id": row["handId"], "number": row["number"], "street": view.street.value,
            "board": list(view.board), "button": view.button, "smallBlind": view.small_blind,
            "bigBlind": view.big_blind, "actor": hand.actor,
            "pot": sum(pot.amount for pot in hand.events[-1].pots) if hand.finished else view.pot,
            "players": [{"seat": p.seat, "agent": self.table.agents[p.seat], "stack": p.stack,
                         "streetBet": p.street_bet, "contributed": p.contributed, "folded": p.folded,
                         "allIn": p.all_in, "shownCards": list(p.shown_cards),
                         "holeCards": holes.get(p.seat)} for p in view.players],
            "legal": {"kinds": [kind.value for kind in legal.kinds], "call": legal.call_amount,
                      "minRaiseTo": legal.min_raise_to, "maxRaiseTo": legal.max_raise_to} if own_turn else None,
            "menu": [{"label": label, "kind": a.kind.value, "raiseTo": a.raise_to} for label, a in menu],
            "presets": self._presets(view, human) if own_turn and state["playMode"] == "free" else [],
            "events": _events(hand),
            "result": row["chips"] if hand.finished else None,
            # A bot's distribution depends on its cards, so it stays private until the hand ends.
            "decisions": [{"seat": r["seat"], "agent": r["agent"], "street": r["street"],
                           "action": [r["kind"], r["raiseTo"]], **r["decision"]}
                          for r in row["actions"] if "decision" in r]
                         if hand.finished or human is None else None,
        }
        return response

    def history(self, session_id):
        with self.lock:
            state = self._load(session_id)
            human = self.table.human
            hands = []
            for row in state["history"]:
                hand = self._hand(row)
                view = hand.observe(0 if human is None else human)
                hands.append({"handId": row["handId"], "number": row["number"], "button": row["button"],
                              "board": list(view.board), "chips": row["chips"], "events": _events(hand),
                              "humanCards": list(view.hole_cards) if human is not None else None,
                              "publicEventsSha256": row["publicEventsSha256"]})
            return {"sessionId": session_id, "hands": hands}

    def verify_replay(self, session_id):
        """Replays every completed hand and re-asks the native service for each bot decision."""
        with self.lock:
            state = self._load(session_id)
            totals = [0] * self.table.players
            deals, bot = _rng(state["dealRngStart"]), _rng(state["botRngStart"])
            for row in state["history"]:
                if row["dealSeed"] != deals.randrange(2**63):
                    raise ValueError("Deal seed is not the session's next deal")
                for index, record in enumerate(row["actions"]):
                    if "decision" not in record:
                        continue
                    if record["decision"]["seed"] != bot.getrandbits(63):
                        raise ValueError("Bot seed is not the session's next bot draw")
                    hand = self._hand(row, index)
                    again = self.decisions.decide(self._native_hand(row, index), record["seat"], record["agent"],
                                                  seed=record["decision"]["seed"],
                                                  expect=expectation(hand.observe(record["seat"])))
                    if (again["action"] != [record["kind"], record["raiseTo"] or 0]
                            or again["probabilities"] != record["decision"]["probabilities"]):
                        raise ValueError("Bot decision replay mismatch")
                hand = self._hand(row)
                if (not hand.finished or digest(public_events(hand.events)) != row["publicEventsSha256"]
                        or self._settle(row, hand) != row["chips"]):
                    raise ValueError("Private hand replay mismatch")
                totals = [a + b for a, b in zip(totals, row["chips"])]
            if totals != state["totals"] or len(state["history"]) != state["handsPlayed"]:
                raise ValueError("Session totals mismatch")
            return len(state["history"])
