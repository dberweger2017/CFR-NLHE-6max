"""Observation privacy and action boundary; no actual hidden deals in requests."""
from dataclasses import replace
import json
import pytest
from src.blueprint.live_river import observation_request
from src.game.hand import Hand, Table
from src.game.types import Action, ActionKind, Street


def fixture(index=0):
    hand = Hand.start(Table(('a','b','c'), (10000,)*3, button=index % 3),
                      hand_id=f'legal-river-{index}', seed=2026102037500+index)
    folded = False
    while not hand.finished and hand.observe(hand.actor).street != Street.RIVER:
        view = hand.observe(hand.actor)
        action = (ActionKind.FOLD if not folded and ActionKind.FOLD in view.legal_actions.kinds
                  else ActionKind.CHECK if ActionKind.CHECK in view.legal_actions.kinds else ActionKind.CALL)
        folded |= action == ActionKind.FOLD
        hand = hand.apply(Action(action))
    return hand.observe(hand.actor)


def test_request_has_only_public_history_and_own_holding():
    view = fixture(); request = observation_request(view, 16)
    assert request['format'] == 'nplayer-live-river-v1'
    assert request['seat'] == view.seat
    assert len(request['actions']) > 3
    assert all(len(row) == 5 for row in request['actions'])
    assert not any(word in json.dumps(request) for word in ('seed', 'deck', 'opponent_cards', 'shown_cards'))
    assert observation_request(replace(view, hand_id='different-public-id'),16) == request
    with pytest.raises(TypeError): observation_request(object(),16)


def test_request_rejects_nonacting_state_and_wrong_work():
    view=fixture()
    for count in (0,1025,True,1.5):
        with pytest.raises(ValueError): observation_request(view,count)
    with pytest.raises(ValueError):observation_request(replace(view,actor=None),16)
    with pytest.raises(ValueError):observation_request(replace(view,hole_cards=()),16)
