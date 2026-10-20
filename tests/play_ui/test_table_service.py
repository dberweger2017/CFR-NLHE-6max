import json
from random import Random

import pytest

from src.play_api.native_decisions import BINARY, NativeDecisions, NativeError
from src.play_api.service import PlayError
from src.play_api.table_service import SeatTable, TableService, deck_for

pytestmark = pytest.mark.skipif(not BINARY.is_file(), reason="needs the release nplayer_serve example")
SCRIPTS = ("script:random", "script:check-call", "script:tight-aggressive", "script:pot-pressure")


@pytest.fixture(scope="module")
def decisions():
    service = NativeDecisions()
    yield service
    service.close()


class Keys:
    def __init__(self):
        self.count = 0

    def __call__(self):
        self.count += 1
        return f"table-test-key-{self.count:06d}"


def table(tmp_path, decisions, agents, stack=10000):
    return TableService(tmp_path / f"{len(agents)}-{agents[0].replace(':', '_')}.sqlite",
                        SeatTable(tuple(agents), stack=stack), decisions)


def play(service, key, view, hands, rng=None):
    sid = view["sessionId"]
    for _ in range(hands):
        view = service.new_hand(sid, key(), {"revision": view["revision"]})
        while view["phase"] == "playing":
            hand = view["hand"]
            if hand["actor"] == view["humanSeat"]:
                legal = hand["legal"]
                if view["playMode"] == "restricted":
                    item = rng.choice(hand["menu"])
                    kind, amount = item["kind"], item["raiseTo"]
                else:
                    kind = rng.choice(legal["kinds"])
                    amount = rng.randint(legal["minRaiseTo"], legal["maxRaiseTo"]) if kind == "raise" else None
                view = service.act(sid, key(), {"handId": hand["id"], "revision": view["revision"],
                                                "kind": kind, "raiseTo": amount})
            else:
                view = service.advance(sid, key(), {"handId": hand["id"], "revision": view["revision"]})
    return view


@pytest.mark.parametrize("seats", [2, 3, 4, 5, 6])
def test_bot_tables_settle_rotate_and_replay_for_every_seat_count(tmp_path, decisions, seats):
    key = Keys()
    service = table(tmp_path, decisions, [SCRIPTS[i % 4] for i in range(seats)])
    view = play(service, key, service.create(key(), {"playMode": "restricted"}), 2 * seats)
    assert view["handsPlayed"] == 2 * seats and sum(view["totals"]) == 0
    state = service._load(view["sessionId"])
    assert [row["button"] for row in state["history"]] == [i % seats for i in range(2 * seats)]
    assert all(sum(row["chips"]) == 0 for row in state["history"])
    # Bot-only tables reveal every seat and every decision to their viewer.
    assert all(player["holeCards"] for player in view["hand"]["players"])
    assert view["hand"]["decisions"] and all("seed" in d for d in view["hand"]["decisions"])
    assert service.verify_replay(view["sessionId"]) == 2 * seats
    service.close()


@pytest.mark.parametrize("seats,stack", [(3, 2000), (6, 20000)])
def test_free_sized_human_actions_keep_both_engines_in_agreement(tmp_path, decisions, seats, stack):
    key = Keys()
    service = table(tmp_path, decisions, ["human", *SCRIPTS[:seats - 1]] if seats <= 5
                    else ["human", *SCRIPTS, "script:random"], stack)
    view = play(service, key, service.create(key(), {"playMode": "free"}), 25, Random(seats))
    assert view["handsPlayed"] == 25 and sum(view["totals"]) == 0
    assert service.verify_replay(view["sessionId"]) == 25
    service.close()


def test_human_tables_hide_bot_cards_and_distributions_until_the_hand_ends(tmp_path, decisions):
    key = Keys()
    service = table(tmp_path, decisions, ["script:pot-pressure", "human", "script:random"])
    view = service.create(key(), {"playMode": "restricted"})
    view = service.new_hand(view["sessionId"], key(), {"revision": view["revision"]})
    while view["hand"]["actor"] != 1:
        view = service.advance(view["sessionId"], key(), {"handId": view["hand"]["id"], "revision": view["revision"]})
        assert view["hand"]["decisions"] is None
    players = view["hand"]["players"]
    assert players[1]["holeCards"] and players[0]["holeCards"] is None and players[2]["holeCards"] is None
    assert [item["label"] for item in view["hand"]["menu"]][:2] in (["Fold", "Call"], ["Check", "Min raise"])
    view = service.act(view["sessionId"], key(), {"handId": view["hand"]["id"], "revision": view["revision"],
                                                  "kind": "fold", "raiseTo": None})
    while view["phase"] == "playing":
        view = service.advance(view["sessionId"], key(), {"handId": view["hand"]["id"], "revision": view["revision"]})
    assert view["hand"]["decisions"] is not None
    service.close()


def test_restricted_sessions_reject_off_menu_sizes_and_bad_turns(tmp_path, decisions):
    key = Keys()
    service = table(tmp_path, decisions, ["human", "script:check-call", "script:check-call"])
    view = service.create(key(), {"playMode": "restricted"})
    view = service.new_hand(view["sessionId"], key(), {"revision": view["revision"]})
    hand = view["hand"]
    assert hand["actor"] == 0  # three-handed, the button acts first preflop
    menu_sizes = {item["raiseTo"] for item in hand["menu"] if item["kind"] == "raise"}
    off_menu = next(size for size in range(hand["legal"]["minRaiseTo"], hand["legal"]["maxRaiseTo"])
                    if size not in menu_sizes)
    with pytest.raises(PlayError, match="restricted menu"):
        service.act(view["sessionId"], key(), {"handId": hand["id"], "revision": view["revision"],
                                               "kind": "raise", "raiseTo": off_menu})
    with pytest.raises(PlayError, match="No bot is acting"):
        service.advance(view["sessionId"], key(), {"handId": hand["id"], "revision": view["revision"]})
    service.close()


def test_idempotent_retries_and_conflicting_keys(tmp_path, decisions):
    key = Keys()
    service = table(tmp_path, decisions, ["script:random", "script:random", "script:random"])
    view = service.create(key(), {"playMode": "restricted"})
    request = {"revision": view["revision"]}
    first = service.new_hand(view["sessionId"], "fixed-retry-key-0001", request)
    assert service.new_hand(view["sessionId"], "fixed-retry-key-0001", request) == first
    with pytest.raises(PlayError, match="conflicts"):
        service.new_hand(view["sessionId"], "fixed-retry-key-0001", {"revision": 99})
    service.close()


def test_replay_audit_detects_a_changed_bot_seed_or_deal(tmp_path, decisions):
    key = Keys()
    service = table(tmp_path, decisions, ["script:random", "script:pot-pressure", "script:tight-aggressive"])
    view = play(service, key, service.create(key(), {"playMode": "restricted"}), 6)
    sid = view["sessionId"]
    original = service._load(sid)

    def tampered(change):
        state = json.loads(json.dumps(original))
        change(state)
        service.db.execute("UPDATE sessions SET state=? WHERE id=?", (json.dumps(state), sid))
        service.db.commit()
        with pytest.raises((ValueError, RuntimeError, NativeError)):
            service.verify_replay(sid)

    def seed(state):
        for row in state["history"]:
            for record in row["actions"]:
                if record["agent"] == "script:random":
                    record["decision"]["seed"] += 1
    tampered(seed)
    tampered(lambda state: state["history"][0].update(dealSeed=state["history"][0]["dealSeed"] + 1))
    service.close()


def test_native_service_refuses_engine_disagreement(decisions):
    hand = {"stacks": [10000] * 3, "sb": 50, "bb": 100, "button": 0, "deck": deck_for(7), "actions": []}
    menu = decisions.decide(hand, 0, "menu")
    assert menu["menu"][0] == ["fold", 0] and menu["action"] is None
    with pytest.raises(NativeError, match="engine parity"):
        decisions.decide(hand, 0, "menu", expect={"legal": {"check": False, "call": 50, "raise_to": [200, 10000]}})
    with pytest.raises(NativeError, match="not acting"):
        decisions.decide(hand, 1, "script:random", seed=1)
    with pytest.raises(NativeError, match="unknown policy"):
        decisions.decide(hand, 0, "policy:absent", seed=1)


class StubDecisions:
    ready = {"schema": "s", "menu": "m", "card_tables": None}

    def __init__(self, players):
        self.policies = {"p": {"identity": {"players": players, "stacks": [10000] * players,
                                            "small_blind": 50, "big_blind": 100}}}


def test_policy_seats_need_a_matching_model_and_restricted_sizing(tmp_path):
    with pytest.raises(ValueError, match="not loaded for this table"):
        TableService(tmp_path / "a.sqlite", SeatTable(("human", "policy:p")), StubDecisions(3))
    with pytest.raises(ValueError, match="not loaded for this table"):
        TableService(tmp_path / "b.sqlite", SeatTable(("human", "policy:q", "script:random")), StubDecisions(3))
    service = TableService(tmp_path / "c.sqlite", SeatTable(("human", "policy:p", "policy:p")), StubDecisions(3))
    with pytest.raises(PlayError, match="restricted sizing"):
        service.create("stub-create-key-0001", {"playMode": "free"})
    service.close()


@pytest.mark.parametrize("agents", [("human",), tuple(["script:random"] * 7), ("human", "human"),
                                    ("human", "script:unknown"), ("bot",)])
def test_table_shapes_are_validated(agents):
    with pytest.raises(ValueError):
        SeatTable(agents)
