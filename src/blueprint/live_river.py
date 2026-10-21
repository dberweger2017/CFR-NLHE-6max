"""Legal observation adapter for the bounded native river engineering pilot.

No action is sampled or applied. The result is a legal action distribution and
measured diagnostics; adoption needs a separate paired strength experiment.
"""
import json
from pathlib import Path
import subprocess
import tempfile
from time import monotonic

from src.blueprint.native_river import card_id
from src.game.observation import ActionTaken, Observation
from src.game.types import Action, ActionKind, Street

BINARY = Path(__file__).resolve().parents[2] / 'native/hu20-trainer/target/release/examples/river_live'


def observation_request(view: Observation, sweeps: int, *, debug=False):
    """Copies only public fields and the observation owner's own holding."""
    if not isinstance(view, Observation):
        raise TypeError('legal immutable Observation required')
    if (view.street != Street.RIVER or view.actor != view.seat or len(view.players) != 3
            or len(view.board) != 5 or len(view.hole_cards) != 2
            or any(isinstance(e, ActionTaken) and e.street == Street.RIVER for e in view.history)):
        raise ValueError('acting first-river three-seat observation required')
    if type(sweeps) is not int or not 1 <= sweeps <= 1024 or type(debug) is not bool:
        raise ValueError('fixed pilot sweeps/debug required')
    bounds = view.legal_actions
    return dict(format='nplayer-live-river-v1', button=view.button,
                board=[card_id(c) for c in view.board], seat=view.seat,
                hole=[card_id(c) for c in view.hole_cards],
                actions=[[e.seat, (Street.PREFLOP, Street.FLOP, Street.TURN, Street.RIVER).index(e.street), e.action.kind.value,
                          e.action.raise_to if e.action.kind == ActionKind.RAISE else 0, e.paid]
                         for e in view.history if isinstance(e, ActionTaken)],
                players=[[p.stack, p.street_bet, p.contributed, p.folded] for p in view.players],
                legal=dict(check=ActionKind.CHECK in bounds.kinds, call_amount=bounds.call_amount,
                           raise_to=[bounds.min_raise_to, bounds.max_raise_to]
                           if ActionKind.RAISE in bounds.kinds else None),
                sweeps=sweeps, debug=debug)


class LiveRiver:
    def __init__(self, k50, model, sha256, *, binary=BINARY):
        self.stderr = tempfile.TemporaryFile()
        tick = monotonic()
        try:
            self.process = subprocess.Popen([str(binary), str(k50), str(model), sha256],
                                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=self.stderr, text=True)
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError('legal river worker failed before ready')
            self.load = json.loads(line)
            if self.load.get('status') != 'ready' or self.load.get('model_sha256') != sha256:
                raise RuntimeError('legal river worker identity differs')
            self.load['roundtrip_startup_seconds'] = monotonic()-tick
        except BaseException:
            if hasattr(self, 'process'):
                self.process.kill(); self.process.wait()
            self.stderr.close()
            raise

    def decide(self, view, sweeps, *, debug=False):
        tick = monotonic()
        request = observation_request(view, sweeps, debug=debug)
        self.process.stdin.write(json.dumps(request, allow_nan=False, separators=(',', ':'))+'\n')
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('legal river worker exited without a response')
        response = json.loads(line)
        if response.get('status') == 'ok':
            import math
            result = response['result']
            p = result['probabilities']
            if (not p or len(p) != len(result['actions']) or any(not math.isfinite(x) or x < 0 for x in p)
                    or abs(sum(p)-1) > 1e-10):
                raise ValueError('invalid returned probability row')
            for kind, target in result['actions']:
                view.legal_actions.validate(Action(ActionKind(kind), raise_to=target if kind == 'raise' else None))
        elif response.get('status') != 'unsupported':
            raise RuntimeError('invalid legal river response')
        response['complete_decision_seconds'] = monotonic()-tick
        return response

    def close(self):
        self.process.stdin.close(); self.process.stdout.close()
        try:
            code = self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate(); self.process.wait(timeout=10)
            raise RuntimeError('legal river worker did not close')
        finally:
            self.stderr.close()
        if code:
            raise RuntimeError('legal river worker exited: '+str(code))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
