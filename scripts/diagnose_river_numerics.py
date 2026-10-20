"""Review the preserved case2 trajectory, without altering its original screen."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import numpy as np

from scripts.benchmark_native_river import fixture
from src.blueprint.native_river import NativeRiver, BINARY, prepared_request, profiles
from src.blueprint.river_cfr import RiverCFR, profile_quality, _visit


def diagnose(binary):
    game, ranges = fixture(2)
    reference = RiverCFR(game)
    first = None
    maximum_same_profile_delta_error = 0.
    with NativeRiver(binary) as worker:
        for step in range(1, 17):
            native = worker.solve(prepared_request(game, ranges, step))
            reference.solve(max_sweeps=1)
            learned = profiles(game, native['current'])
            for node in learned:
                diff = np.abs(learned[node]-reference.last_played[node])
                if first is None and diff.max() > 1e-8:
                    row = int(np.unravel_index(diff.argmax(), diff.shape)[0])
                    previous = worker.solve(prepared_request(game, ranges, step-1))
                    old_ref = RiverCFR(game); old_ref.solve(max_sweeps=step-1)
                    first = dict(sweep=step, node=node, holding=row,
                                 holding_cards=game.holdings[game.seats.index(game.nodes[node].actor)][row],
                                 native_previous_regrets=profiles(game, previous['regrets'])[node][row].tolist(),
                                 python_previous_regrets=old_ref.regrets[node][row].tolist(),
                                 native_strategy=learned[node][row].tolist(),
                                 python_strategy=reference.last_played[node][row].tolist(),
                                 max_probability_difference=float(diff.max()))
            # Feed the *same* entire learned profile into both traversals.
            fixed = prepared_request(game, ranges, 1, fixed_profile=learned)
            frozen = worker.solve(fixed)
            deltas = {n: np.zeros_like(p) for n, p in learned.items()}
            for seat in game.seats:
                other = 1-game.seats.index(seat)
                _visit(game, 0, seat, np.ones(len(game.holdings[other])), learned, deltas, 1)
            actual = profiles(game, frozen['last_deltas'])
            error = max(float(np.max(np.abs(actual[n]-p))) for n, p in deltas.items())
            maximum_same_profile_delta_error = max(maximum_same_profile_delta_error, error)
            if error > 1e-10:
                raise AssertionError('same-profile traversal differs')
        curves = []
        for sweeps in (16, 64, 256):
            py = RiverCFR(game); solved = py.solve(max_sweeps=sweeps)
            ref = profile_quality(game, solved.average)
            row = dict(sweeps=sweeps, python=ref)
            for mode in ('linear', 'scalar'):
                request = prepared_request(game, ranges, sweeps)
                request['scalar_control'] = mode == 'scalar'
                native = worker.solve(request)
                cross = profile_quality(game, profiles(game, native['average']))
                if abs(cross['exploitability_bb']-native['quality']['exploitability_bb']) > 1e-10:
                    raise AssertionError('independent scalar-profile quality disagrees')
                row[mode] = native['quality']
            curves.append(row)
    if first is None:
        raise AssertionError('original divergence was not reproduced')
    return dict(status='review-complete', first_divergence=first,
                same_profile_delta_max_absolute_error_bb=maximum_same_profile_delta_error,
                identical_profile_checks=16, curves=curves,
                binary_sha256=sha256(Path(binary).read_bytes()).hexdigest(),
                original_screen_preserved=True,
                interpretation='near-zero regret matching can amplify roundoff; same-profile math agrees; finite-work policies need not agree')


def main():
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--binary', type=Path, default=BINARY); a = p.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    if a.out.exists():
        raise FileExistsError(a.out)
    result = diagnose(a.binary)
    a.out.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()
