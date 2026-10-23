"""Verify a prepared v0.6.1 bundle in the existing local-table runtime.

Twelve hands per seed check integration/replay, never estimate playing strength.
Journals and the receipt are created in a fresh private output directory.
"""
import argparse
import json
import os
from pathlib import Path
from random import Random
import time

from scripts.play_v061 import table_arguments
from src.play_api.native_decisions import BINARY, NativeDecisions
from src.play_api.service import PlayError
from src.play_api.table_service import SeatTable, TableService
from src.policies.v061_bundle import MODELS, VERSION, read_manifest, verify_small_assets, regular


def check(bundle, seed, cache, output, binary=BINARY, *, tables=None, expected_source=None, model=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    started = time.monotonic()
    if model is None:
        args = table_arguments(bundle, seed, cache, allow_prepared=True,tables=tables,expected_source=expected_source)
        model = args[args.index('--policy') + 2]
    else:
        manifest = read_manifest(bundle, seed, expected_source)
        verify_small_assets(bundle, manifest, seed, tables)
        model = regular(model)
        # Native startup fully verifies the pinned whole binary and schema.
        # Reuse that mandatory pass instead of a redundant Python hash first.
    alias = f'{VERSION}-{seed}'
    assembled = time.monotonic()
    decisions = NativeDecisions(card_buckets=Path(tables or bundle),
                                policies={alias: (model, MODELS[seed]['sha256'])}, binary=Path(binary))
    loaded = time.monotonic()
    receipts = []
    counter = 0

    def key():
        nonlocal counter
        counter += 1
        return f'release-runtime-check-{counter:06d}'

    def privacy(view, human):
        if human is not None and view['phase'] == 'playing':
            assert view['hand']['decisions'] is None
            assert all(p['holeCards'] is None for i, p in enumerate(view['hand']['players']) if i != human)

    try:
        assert decisions.ready['loaded_weight_tables'] == 1
        assert decisions.policies[alias]['sha256'] == MODELS[seed]['sha256']
        assert decisions.policies[alias]['identity'] == MODELS[seed]['metadata']['policy']['identity']
        for watch in (False, True):
            agents = tuple([f'policy:{alias}'] * 3) if watch else ('human', f'policy:{alias}', f'policy:{alias}')
            table = SeatTable(agents, stack=20000)
            journal = output / ('spectator.sqlite' if watch else 'human.sqlite')
            service = TableService(journal, table, decisions, source_version=VERSION+'-prepared')
            try:
                try:
                    service.create(key(), {'playMode': 'free'})
                except PlayError:
                    pass
                else:
                    raise AssertionError('model table accepted free sizing')
                view = service.create(key(), {'playMode': 'restricted'})
                sid = view['sessionId']
                rng = Random(2026102036901)
                for _ in range(6):
                    view = service.new_hand(sid, key(), {'revision': view['revision']})
                    privacy(view, table.human)
                    while view['phase'] == 'playing':
                        hand = view['hand']
                        request = {'handId': hand['id'], 'revision': view['revision']}
                        if hand['actor'] == table.human:
                            item = rng.choice(hand['menu'])
                            view = service.act(sid, key(), dict(request, kind=item['kind'], raiseTo=item['raiseTo']))
                        else:
                            view = service.advance(sid, key(), request)
                        privacy(view, table.human)
                    assert sum(view['totals']) == 0
                assert view['handsPlayed'] == 6
                if watch:
                    assert all(p['holeCards'] for p in view['hand']['players'])
                assert service.verify_replay(sid) == 6
                service.close()
                service = TableService(journal, table, decisions, source_version=VERSION+'-prepared')
                assert service.verify_replay(sid) == 6
                receipts.append(dict(mode='spectator' if watch else 'human', session=sid,
                                     hands=6, replayed_before_and_after_restart=True, chip_conservation=True,
                                     restricted_menu=True, privacy=True))
            finally:
                service.close()
        result = dict(status='passed', seed=seed, source_commit=expected_source, model_sha256=MODELS[seed]['sha256'],
                      loaded_weight_tables=1, native_ready=decisions.ready, tables=receipts,
                      model_path=str(model), stack_bb=200,
                      assembly_and_asset_check_seconds=assembled-started,
                      native_start_seconds=loaded-assembled,
                      play_and_double_replay_seconds=time.monotonic()-loaded,
                      limitation='Twelve integration hands, no poker-strength estimate')
        (output/'receipt.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
        return result
    finally:
        decisions.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--card-tables', type=Path)
    parser.add_argument('--expect-source', required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--seed', choices=MODELS, required=True)
    parser.add_argument('--model', type=Path, help='Reuse an exact existing binary; native loader verifies it')
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--binary', type=Path, default=BINARY)
    args = parser.parse_args()
    os.umask(0o077)
    print(json.dumps(check(args.bundle, args.seed, args.cache, args.out, args.binary, tables=args.card_tables, expected_source=args.expect_source, model=args.model)))


if __name__ == '__main__':
    main()
