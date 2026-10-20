"""Six declared legal public river roots, including two low-stack controls.

Synthetic engineering states, not a frequency-weighted sample of played hands.
"""
from src.blueprint.abstraction import choices
from src.game.hand import Hand, Table
from src.game.types import Action, ActionKind, Street


def fixture(index):
    if index not in range(6):
        raise ValueError('declared six-case panel only')
    hand=Hand.start(Table(('a','b','c'),(10000,)*3,button=index%3),
                    hand_id=f'live-river-pilot-{index}',seed=2026102037500+index)
    sb=(index%3+1)%3
    preflop_raises=0
    raises={Street.FLOP:0,Street.TURN:0}
    while not hand.finished:
        view=hand.observe(hand.actor)
        if view.street==Street.RIVER:
            return view
        menu=choices(view,raise_cap=None,free_fold=False)
        candidates=[c.action for c in menu if c.action.kind==ActionKind.RAISE]
        passive=Action(ActionKind.CHECK if ActionKind.CHECK in view.legal_actions.kinds else ActionKind.CALL)
        action=passive
        if view.street==Street.PREFLOP:
            if index==0 and view.seat==index%3 and ActionKind.FOLD in view.legal_actions.kinds:
                action=Action(ActionKind.FOLD)
            elif index>0 and view.seat==sb and ActionKind.FOLD in view.legal_actions.kinds:
                action=Action(ActionKind.FOLD)
            elif index>=2 and candidates and preflop_raises < (1 if index<4 else 4):
                # min/pot order is the production menu. The fourth preflop
                # raise is the minimum, preserving two non-all-in players.
                nonjam=[a for a in candidates if a.raise_to<view.legal_actions.max_raise_to]
                if nonjam:
                    action=nonjam[-1] if preflop_raises<3 else nonjam[0]
                    preflop_raises+=1
        elif index in (2,3) and raises[view.street] < (1 if index==2 else 2) and candidates:
            nonjam=[a for a in candidates if a.raise_to<view.legal_actions.max_raise_to]
            if nonjam:
                action=nonjam[-1] if raises[view.street]==0 else nonjam[0]
                raises[view.street]+=1
        elif index>=4 and candidates:
            # Declared near-all-in support controls. These min-raise histories
            # are legal but deliberately not called typical poker situations.
            target=300 if view.street==Street.FLOP else (4000 if index==4 else 3900)
            if candidates[0].raise_to<=target:
                action=candidates[0]
        hand=hand.apply(action)
    raise AssertionError('declared fixture settled before river')
