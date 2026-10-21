"""Opt-in research client. One retained hand; no arena/default integration."""
import json
import math
from time import monotonic

from src.blueprint.live_river import LiveRiver, public_observation
from src.game.types import Action, ActionKind


class RetainedRiver(LiveRiver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = None

    def _ask(self, request, view=None):
        tick = monotonic()
        self.process.stdin.write(json.dumps(request, allow_nan=False, separators=(',', ':'))+'\n')
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('retained worker exited without a response')
        response = json.loads(line)
        if response.get('status') != 'ok':
            raise RuntimeError(f'retained request rejected: {response.get("reason")}')
        result = response['result']
        if view is not None:
            p = result['probabilities']
            if (not p or len(p) != len(result['actions'])
                    or any(not math.isfinite(x) or x < 0 for x in p) or abs(sum(p)-1) > 1e-10):
                raise ValueError('invalid retained probability row')
            for kind, target in result['actions']:
                view.legal_actions.validate(Action(ActionKind(kind), raise_to=target if kind == 'raise' else None))
        response['complete_decision_seconds'] = monotonic()-tick
        return response

    def begin(self, view):
        if self.session is not None:
            raise ValueError('release the previous retained hand first')
        observation = public_observation(view)
        observation.update(mode='solve', algorithm='dcfr-1.5-0-2',
                           search_menu='pot-jam-cap3-root-check-min-v1', sweeps=2048,
                           checkpoints=[8, 16, 32, 64, 128, 256, 512, 1024, 2048], stop_at_target=True)
        response = self._ask(dict(mode='retained-begin', hand_id=view.hand_id, observation=observation), view)
        self.session = response['result']['session']
        return response

    def continue_hand(self, view):
        if self.session is None or view.hand_id != self.session['hand_id']:
            raise ValueError('no retained session for this hand')
        return self._ask(dict(mode='retained-continue', hand_id=view.hand_id,
                              handle=self.session['handle'], observation=public_observation(view)), view)

    def release(self):
        if self.session is None:
            raise ValueError('no retained session')
        response = self._ask(dict(mode='retained-release', hand_id=self.session['hand_id'], handle=self.session['handle']))
        self.session = None
        return response
