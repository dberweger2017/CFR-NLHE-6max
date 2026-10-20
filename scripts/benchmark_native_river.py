"""Small fixed prepared-river qualification, never a poker strength experiment."""
import argparse
from copy import deepcopy
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import platform
import resource
import statistics
import subprocess
from time import monotonic

import numpy as np

from src.blueprint.native_river import BINARY, NativeRiver, prepared_request, profiles
from src.blueprint.river_cfr import RiverCFR, profile_quality, _visit
from src.blueprint.river_game import RiverGame
from src.blueprint.search import DECK
from src.game.hand import Hand, Table
from src.game.showdown import hand_value
from src.game.types import Action, ActionKind, Street


class ThreeSeatRiver(RiverGame):
    table_players = 3
    free_fold = False


def fixture(index=0, full=False, *, dead_money=False):
    """Only the public board/tree and separately stipulated ranges are exported."""
    hand = Hand.start(Table(('a', 'b', 'c'), (10_000, 9_901, 10_103),
                            button=index % 3, small_blind=51, big_blind=101),
                      hand_id=f'prepared-{index}', seed=2026102037300+index)
    fold_seat = (index % 3+1) % 3 if dead_money else index % 3
    flop_bet = [0, 0, 500, 500, 3000, 7000][index % 6]
    bet_used = False
    while hand.observe(hand.actor).street != Street.RIVER:
        view = hand.observe(hand.actor)
        if flop_bet and not bet_used and view.street == Street.FLOP and ActionKind.RAISE in view.legal_actions.kinds:
            hand = hand.apply(Action(ActionKind.RAISE, raise_to=flop_bet))
            bet_used = True
            continue
        kind = (ActionKind.FOLD if view.street == Street.PREFLOP
                and sum(not p.folded for p in view.players) > 2 and view.seat == fold_seat
                and ActionKind.FOLD in view.legal_actions.kinds
                else ActionKind.CHECK if ActionKind.CHECK in view.legal_actions.kinds
                else ActionKind.CALL)
        hand = hand.apply(Action(kind))
    if index % 2:
        from src.blueprint.abstraction import choices
        hand = hand.apply(next(c.action for c in choices(hand.observe(hand.actor))
                               if c.action.kind == ActionKind.RAISE))
    view = hand.observe(hand.actor)
    pairs = tuple(combinations(sorted(set(DECK)-set(view.board)), 2))
    if not full:
        pairs = pairs[::max(1, len(pairs)//8)][:8]
    live = [p.seat for p in view.players if not p.folded]
    ranges = {seat: tuple((pair, float(0 if (i+offset) % 11 == 0 else 1+(i*7+offset) % 13))
                         for i, pair in enumerate(pairs)) for offset, seat in enumerate(live)}
    return ThreeSeatRiver(view.history, ranges, raise_cap=2), ranges


def check_leaves(worker, game, request):
    request = deepcopy(request); request['sweeps'] = 1
    queries, expected = [], []
    for node in game.nodes:
        if node.terminal is None:
            continue
        t = node.terminal
        for seat in (0, 1):
            reach = np.array([((i*17+seat) % 23)/23 for i in range(len(game.holdings[1-seat]))])
            queries.append(dict(terminal=[t.base, t.win0, t.tie0], seat=seat, reach=reach.tolist()))
            expected.append(game.utility_vectors(t, game.seats[seat], reach))
    request['leaf_queries'] = queries
    result = worker.solve(request)
    error = max((float(np.max(np.abs(np.asarray(a)-b))) for a,b in zip(result['leaf_values'],expected)), default=0.)
    if error > 1e-10:
        raise AssertionError('native terminal values differ from dense reference: '+str(error))
    # Independent Python hand evaluator ordering, including blocked pairs and ties.
    ranks = [[hand_value(tuple(pair)+game.board) for pair in holdings] for holdings in game.holdings]
    order = {rank:i for i, rank in enumerate(sorted(set(ranks[0]+ranks[1])))}
    py = [np.array([order[r] for r in row]) for row in ranks]
    native = [np.array(row, dtype=np.int64) for row in result['ranks']]
    if not np.array_equal(np.sign(py[0][:,None]-py[1][None,:]),
                          np.sign(native[0][:,None]-native[1][None,:])):
        raise AssertionError('native holding strength/tie order differs')
    return dict(max_absolute_error_bb=error,queries=len(queries),native_seconds=result["leaf_query_seconds"])


def qualify(worker, game, ranges, sweeps):
    request = prepared_request(game, ranges, 1)
    request['strategy_queries'] = [dict(node=0,holding=0)]
    leaf = check_leaves(worker, game, request)
    # Compare one sweep under the same uniform initial profile. Even a second
    # learned profile can differ when near-zero regrets amplify rounding.
    for count in (1,):
        request['sweeps'] = count
        result = worker.solve(request)
        reference = RiverCFR(game); reference.solve(max_sweeps=count)
        for key, rows in (('regrets', reference.regrets), ('average_numer', reference.average_numer)):
            native = profiles(game, result[key])
            for node in rows:
                np.testing.assert_allclose(native[node], rows[node], rtol=1e-10, atol=1e-10)
        for node, row in reference.average_denom.items():
            np.testing.assert_allclose(result['average_denom'][node], row, rtol=1e-12, atol=1e-12)
    # Freeze identical nonuniform profiles for two sweeps to check both
    # weighted regret deltas and actual-own-reach averaging without conflating
    # those operations with different floating-point CFR learning paths.
    fixed = {}
    for n in game.nodes:
        if n.actor is None: continue
        rows = len(game.holdings[game.seats.index(n.actor)])
        p = (np.arange(rows*len(n.menu)).reshape(rows,len(n.menu)) % 11).astype(np.float64)
        p += 1; p /= p.sum(axis=1,keepdims=True); fixed[n.id] = p
    fixed_request = prepared_request(game,ranges,2,fixed_profile=fixed)
    fixed_native = worker.solve(fixed_request)
    ref = RiverCFR(game,fixed_profile=fixed);ref.solve(max_sweeps=2)
    expected_delta = {k:np.zeros_like(p) for k,p in fixed.items()}
    for seat in game.seats:
        other = game.seats[1] if seat==game.seats[0] else game.seats[0]
        _visit(game,0,seat,np.ones(len(game.holdings[game.seats.index(other)])),fixed,expected_delta,2)
    for field, expected in (('last_deltas',expected_delta),('average_numer',ref.average_numer)):
        actual = profiles(game,fixed_native[field])
        for node in expected:np.testing.assert_allclose(actual[node],expected[node],rtol=1e-10,atol=1e-10)
    for node,expected in ref.average_denom.items():np.testing.assert_allclose(fixed_native['average_denom'][node],expected,rtol=1e-12,atol=1e-12)
    records = []
    for count in sweeps:
        request['sweeps'] = count
        samples = [worker.solve(request) for _ in range(3)]
        # Same binary/fixed work must reproduce all mathematical fields exactly.
        for field in ('average','current','regrets','average_numer','average_denom','quality','leaf_values','ranks'):
            if any(x[field] != samples[0][field] for x in samples[1:]):
                raise AssertionError('native fixed work is not deterministic: '+field)
        result = samples[0]
        compact_request = dict(request, include_profiles=False)
        compact = [worker.solve(compact_request) for _ in range(3)]
        if any(x['strategy_rows'] != result['strategy_rows'] or x['quality'] != result['quality'] for x in compact):
            raise AssertionError('compact prepared strategy differs from full-profile result')
        start = monotonic(); reference = RiverCFR(game); solved = reference.solve(max_sweeps=count)
        ref_solve = monotonic()-start
        ref_quality = profile_quality(game, solved.average)
        native_average = profiles(game, result['average'])
        frozen = prepared_request(game,ranges,1,fixed_profile=solved.average,include_profiles=False)
        frozen_native = worker.solve(frozen)['quality']
        for field in ('exploitability_bb','zero_sum_error_bb'):
            if abs(frozen_native[field]-ref_quality[field]) > 1e-9:
                raise AssertionError('native evaluation of the exact Python profile differs')
        if np.max(np.abs(np.asarray(frozen_native['profile_values_bb'])-ref_quality['profile_values_bb'])) > 1e-9:
            raise AssertionError('same-profile values differ')
        # Evaluate the native policy with the unchanged dense reference too.
        cross = profile_quality(game, native_average)
        for field in ('exploitability_bb','zero_sum_error_bb'):
            if abs(cross[field]-result['quality'][field]) > 1e-9:
                raise AssertionError('native best-response quality disagrees with dense evaluation')
        if np.max(np.abs(np.asarray(cross['profile_values_bb'])-result['quality']['profile_values_bb'])) > 1e-9:
            raise AssertionError('native profile values disagree with dense evaluation')
        quality_gap = abs(ref_quality['exploitability_bb']-cross['exploitability_bb'])
        # Floating-point CFR paths may differ; compare converged quantities with
        # an explicit absolute floor plus 5% reference-relative tolerance.
        tolerance = max(1e-7, 0.05*ref_quality['exploitability_bb'])
        quality_within_tolerance = quality_gap <= tolerance
        # A finite-work quality difference is a measured result, not a terminal
        # value failure. Finish the original fixed grid and preserve the failed
        # agreement flag rather than extending work or loosening the tolerance.
        records.append(dict(sweeps=count, python_solve_seconds=ref_solve,
            native_solve_seconds=[x['solve_seconds'] for x in samples],
            preparation_seconds=[x['preparation_seconds'] for x in samples],
            quality_seconds=[x['quality_seconds'] for x in samples],
            roundtrip_seconds=[x['roundtrip_seconds'] for x in samples],
            compact_action_roundtrip_seconds=[x['roundtrip_seconds'] for x in compact],
            compact_action_probabilities=result['strategy_rows'][0]['probabilities'],
            json_parse_seconds=[x['json_parse_seconds'] for x in samples],
            solve_speedup=ref_solve/statistics.median(x['solve_seconds'] for x in samples),
            python_quality=ref_quality,native_quality=result['quality'],quality_gap_bb=quality_gap,
            quality_tolerance_bb=tolerance,quality_within_tolerance=quality_within_tolerance,quality_signed_gap_bb=cross["exploitability_bb"]-ref_quality["exploitability_bb"],deterministic_repetitions=3))
    return dict(same_profile_gradient_average_value_and_br_parity=True,leaf_evaluation_mode=result["leaf_evaluation_mode"],leaf_max_absolute_error_bb=leaf["max_absolute_error_bb"],leaf_queries=leaf["queries"],native_leaf_query_seconds=leaf["native_seconds"],prepared_request_sha256=sha256(json.dumps(request,sort_keys=True,allow_nan=False).encode()).hexdigest(),nodes=len(game.nodes),
                holdings=[len(h) for h in game.holdings],records=records)


def run(out, binary, smoke=False):
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    started = monotonic()
    from scripts.check_nplayer_parity import engine_identity
    source_paths = ["native/hu20-trainer/src/river.rs", "native/hu20-trainer/src/river/tests.rs", "native/hu20-trainer/src/river/prepared.rs", "native/hu20-trainer/examples/river_prepared.rs", "native/hu20-trainer/src/lib.rs", "native/hu20-trainer/Cargo.lock", "native/hu20-buckets/src/lib.rs", "src/blueprint/native_river.py", "src/blueprint/river_cfr.py", "src/blueprint/river_game.py", "scripts/benchmark_native_river.py"]
    result = dict(engine=engine_identity(),source_files={p:sha256(Path(p).read_bytes()).hexdigest() for p in source_paths},status='running',scope='prepared product-compatible fixtures; no full decision or strength claim',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        source_worktree_dirty=bool(subprocess.run(['git','diff','--quiet','HEAD','--']).returncode),
        binary_sha256=sha256(Path(binary).read_bytes()).hexdigest(),platform=platform.platform(),
        python=platform.python_version(),numpy=np.__version__,shared_host=True,
        declared_quality_tolerance='max(1e-7 BB, 5% of dense reference exploitability) at each endpoint',
        cases=[])
    try:
        with NativeRiver(binary) as worker:
            for index in range(1 if smoke else 6):
                for full in ([False] if smoke else [False,True]):
                    start = monotonic(); game, ranges = fixture(index, full)
                    build = monotonic()-start
                    case = qualify(worker,game,ranges,[1,16] if smoke else [16,64,256])
                    case.update(index=index,full_range=full,board=list(game.board),root_pot_bb=game.root_pot/game.big_blind,root_stacks=list(game.root_stacks),python_fixture_construction_seconds=build)
                    result['cases'].append(case)
                    (out/'progress.json').write_text(json.dumps(dict(cases_completed=len(result['cases']),at=__import__('time').time()))+'\n')
        result['numerical_correctness'] = 'passed'
        result['status'] = 'passed' if all(r['quality_within_tolerance'] for c in result['cases'] for r in c['records']) else 'quality-threshold-not-met'
    except BaseException as error:
        result.update(status='failed',error=repr(error)); raise
    finally:
        usage=resource.getrusage(resource.RUSAGE_CHILDREN)
        result.update(wall_seconds=monotonic()-started,child_peak_rss_bytes=usage.ru_maxrss*(1 if platform.system()=='Darwin' else 1024))
        (out/'results.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--binary',type=Path,default=BINARY)
    parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
    result=run(args.out,args.binary,args.smoke)
    print(json.dumps(dict(status=result['status'],cases=len(result['cases']),wall_seconds=result['wall_seconds'])))

if __name__=='__main__':main()
