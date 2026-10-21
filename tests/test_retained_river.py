"""Legal later observations; IDs never enter solving or disclose hidden worlds."""
from dataclasses import replace
import json
import pytest

from src.blueprint.live_river import public_observation, observation_request
from src.blueprint.retained_river import RetainedRiver
from src.game.hand import Hand, Table
from src.game.types import Action, ActionKind, Street


def later():
    hand=Hand.start(Table(('a','b','c'),(10000,)*3,button=0),hand_id='retained-fixture',seed=82)
    folded=False
    while hand.observe(hand.actor).street!=Street.RIVER:
        view=hand.observe(hand.actor)
        kind=(ActionKind.FOLD if not folded else ActionKind.CHECK if ActionKind.CHECK in view.legal_actions.kinds else ActionKind.CALL)
        folded|=kind==ActionKind.FOLD
        hand=hand.apply(Action(kind))
    root=hand.observe(hand.actor)
    hand=hand.apply(Action(ActionKind.CHECK))
    view=hand.observe(hand.actor)
    hand=hand.apply(Action(ActionKind.RAISE,raise_to=view.legal_actions.min_raise_to))
    return root,hand.observe(hand.actor)


def test_later_public_copy_has_only_legal_information_and_preserves_old_first_contract():
    root,view=later()
    assert public_observation(root)=={k:v for k,v in observation_request(root,16).items() if k not in ('sweeps','debug')}
    with pytest.raises(ValueError):observation_request(view,16)
    request=public_observation(view)
    assert len(request['actions'])==len(public_observation(root)['actions'])+2
    assert not any(s in json.dumps(request) for s in ('deck','seed','opponent_cards','hand_id'))
    assert request==public_observation(replace(view,hand_id='different-operational-id'))
    with pytest.raises(TypeError):public_observation(object())
    with pytest.raises(ValueError):public_observation(replace(view,seat=(view.seat+1)%3))


def test_client_lifecycle_and_hand_id_are_transport_only():
    root,view=later()
    client=object.__new__(RetainedRiver);client.session=None;sent=[]
    def ask(request,view=None):
        sent.append(request)
        return {'result':{'session':{'handle':'opaque','hand_id':request['hand_id']}}}
    client._ask=ask
    client.begin(root)
    assert sent[0]['observation']['algorithm']=='dcfr-1.5-0-2'
    assert 'hand_id' not in sent[0]['observation']
    with pytest.raises(ValueError):client.begin(root)
    with pytest.raises(ValueError):client.continue_hand(replace(view,hand_id='wrong-hand'))
    client.continue_hand(view)
    assert sent[-1]['mode']=='retained-continue'
    assert sent[-1]['handle']=='opaque'
    client.release()
    assert client.session is None
    with pytest.raises(ValueError):client.continue_hand(view)
