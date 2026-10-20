"""Explicit prepared-input adapter; never constructs a blueprint belief or acts."""
from pathlib import Path
import json
import subprocess
import tempfile
from time import monotonic

import numpy as np

BINARY = Path(__file__).resolve().parents[2] / 'native/hu20-trainer/target/release/examples/river_prepared'


def card_id(card):
    if not isinstance(card, str) or len(card) != 2:
        raise ValueError('expected a public/range card name')
    return '23456789TJQKA'.index(card[0])*4 + 'cdhs'.index(card[1])


def prepared_request(game, ranges, sweeps, *, fixed_profile=None, include_profiles=True):
    """Export the exact stipulated product-compatible law of a reference game.

    Ranges are explicit hypothetical distributions. An arbitrary correlated law
    cannot be represented by the linear kernel and is refused, even if labeled
    as product-compatible. Actual private deals are not an argument.
    """
    if type(sweeps) is not int or not 0 < sweeps <= 1_000_000:
        raise ValueError('positive fixed sweep count required')
    if set(ranges) != set(game.seats):
        raise ValueError('ranges must name exactly the two modeled seats')
    weights = []
    exported = []
    masks = []
    for seat, holdings in zip(game.seats, game.holdings):
        rows = ranges[seat]
        if tuple(tuple(sorted(pair)) for pair, _ in rows) != holdings:
            raise ValueError('prepared holding order differs from reference')
        w = np.array([mass for _, mass in rows], dtype=np.float64)
        if not np.isfinite(w).all() or (w < 0).any() or w.max() <= 0:
            raise ValueError('invalid prepared range mass')
        w = w/w.max(); w /= w.sum(); weights.append(w)
        exported.append([[card_id(pair[0]), card_id(pair[1]), float(mass)] for pair, mass in rows])
        masks.append(np.array([(1 << card_id(pair[0])) | (1 << card_id(pair[1])) for pair, _ in rows], dtype=np.uint64))
    expected = np.outer(*weights) * ((masks[0][:, None] & masks[1][None, :]) == 0)
    if expected.sum() <= 0:
        raise ValueError('no compatible prepared chance mass')
    expected /= expected.sum()
    if expected.shape != game.joint.shape or not np.allclose(expected, game.joint, rtol=1e-13, atol=1e-16):
        raise ValueError('linear prototype requires the stipulated product-compatible joint law')
    nodes = []
    for i, node in enumerate(game.nodes):
        if node.id != i:
            raise ValueError('reference node order differs')
        if node.terminal is not None:
            t = node.terminal
            nodes.append(dict(terminal=[t.base, t.win0, t.tie0]))
        else:
            nodes.append(dict(actor=game.seats.index(node.actor), children=list(node.children)))
    result = dict(format='river-prepared-v1', sweeps=sweeps, include_profiles=include_profiles,
                  game=dict(board=[card_id(c) for c in game.board], ranges=exported,
                            nodes=nodes, root_pot_bb=game.root_pot/game.big_blind))
    fixed = {}
    for key, profile in (fixed_profile or {}).items():
        node = game.nodes[key]
        shape = (len(game.holdings[game.seats.index(node.actor)]), len(node.menu))
        p = np.asarray(profile, dtype=np.float64)
        if p.shape != shape:
            raise ValueError('fixed profile shape differs')
        fixed[str(key)] = p.reshape(-1).tolist()
    if fixed:
        result['fixed'] = fixed
    return result


def profiles(game, rows):
    if len(rows) != len(game.nodes):
        raise ValueError('native profile node count differs')
    return {n.id: np.asarray(rows[n.id], dtype=np.float64).reshape(
                len(game.holdings[game.seats.index(n.actor)]), len(n.menu))
            for n in game.nodes if n.actor is not None}


class NativeRiver:
    """One sequential JSONL worker. Inputs/outputs are prepared fixture data."""
    def __init__(self, binary=BINARY):
        self.stderr = tempfile.TemporaryFile()
        try:
            self.process = subprocess.Popen([str(Path(binary).absolute())], stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, stderr=self.stderr, text=True)
        except BaseException:
            self.stderr.close()
            raise

    def solve(self, request):
        started = monotonic()
        data = json.dumps(request, allow_nan=False, separators=(',', ':'))+'\n'
        self.process.stdin.write(data); self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('native prepared worker exited without a response')
        value = json.loads(line)
        elapsed = monotonic()-started
        if value.get('status') != 'ok':
            raise ValueError(value.get('error', 'invalid prepared worker response'))
        result = value['result']
        if result.get('format') != 'river-prepared-result-v1':
            raise ValueError('native prepared result format differs')
        result['json_parse_seconds'] = value['json_parse_seconds']
        result['roundtrip_seconds'] = elapsed
        return result

    def close(self):
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        if self.process.stdout:
            self.process.stdout.close()
        try:
            code = self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate(); self.process.wait(timeout=10)
            raise RuntimeError('prepared worker did not close')
        finally:
            self.stderr.close()
        if code:
            raise RuntimeError('prepared worker exited with code '+str(code))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
