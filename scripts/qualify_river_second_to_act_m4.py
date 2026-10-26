"""The explicitly permitted fixture-only closeout when the local input gate is open.

This command cannot train, load a policy, run an arena or claim model-panel parity.
All build/test work is guarded by the ordinary Mac mutex and thermal supervisor.
"""
import argparse
import fcntl
import gzip
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time

from scripts.nplayer_four_player_feasibility import SOURCE, Supervisor, sample, sha, write


def inventory(paths):
    rows = []
    for path in paths:
        p = Path(path)
        before = p.stat()
        with gzip.open(p, 'rb') as f:
            line = f.readline(131073)
        if len(line) > 131072:
            raise ValueError('policy header exceeds bound')
        h = json.loads(line)
        after = p.stat()
        if before != after:
            raise ValueError('input metadata changed during header inventory')
        identity = h.get('identity', {})
        players = h.get('players', identity.get('players'))
        reason = 'wrong-player-count' if players != 3 else 'requires-full-input-admission'
        rows.append(dict(path=str(p), bytes=before.st_size, inode=before.st_ino,
                         mtime_ns=before.st_mtime_ns, header_sha256=__import__('hashlib').sha256(line).hexdigest(),
                         format=h.get('format'), players=players, entries=h.get('entries'),
                         strategy=h.get('strategy'), last_average_street=h.get('last_average_street'),
                         disposition=reason))
    return dict(exhaustive=False, method='bounded-first-header-only; explicit catalog paths', candidates=rows,
                compatible_model_admitted=False, no_model_loaded=True)


def verify_panel(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines()]
    if len(rows) != 48:
        raise ValueError('fixed panel must contain all 48 roots')
    for i, row in enumerate(rows):
        if (row['id'], row['history'], row['board_index'], row['entry']) != (i, i // 12, (i // 4) % 3, i % 4):
            raise ValueError('fixed panel identity differs')
        r = row['request']
        if (r['algorithm'] != 'dcfr-1.5-0-2' or r['sweeps'] != 2048
                or r['checkpoints'] != [8, 16, 32, 64, 128, 256, 512, 1024, 2048]
                or r['search_menu'] != 'pot-jam-cap3-root-min-responses-v1'
                or r['stop_at_target'] is not True or r['target'] != dict(pot_fraction=.01, cap_bb=.1)
                or any(k in r for k in ('deck', 'holes', 'seed'))):
            raise ValueError('request scope differs')
    return dict(roots=48, first_to_act=12, second_to_act=36, sha256=sha(path),
                legal_generation='native Hand + production menu; generator tests', model_requests=0)


def test_receipt(path):
    text = Path(path).read_text()
    matches = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored', text)
    if len(matches) != 1 or int(matches[0][0]) == 0 or any(int(x) for x in matches[0][1:]):
        raise ValueError('missing, failed or skipped native test summary')
    return dict(passed=int(matches[0][0]), failed=0, ignored=0)


def run(root, catalog, thermal):
    if platform.system() != 'Darwin' or 'Apple M4' not in subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string'], text=True):
        raise ValueError('M4-only qualification')
    if root.exists():
        raise FileExistsError('attempt already exists; preserve, no automatic retry')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=SOURCE, text=True).strip():
        raise ValueError('clean committed source required')
    if 'AC Power' not in subprocess.check_output(['pmset', '-g', 'batt'], text=True):
        raise ValueError('AC power required at admission')
    if shutil.disk_usage(root.parent).free < 20 * 2**30:
        raise ValueError('20GiB actual free required before preparation')
    root.mkdir()
    started = time.time()
    try:
        with (Path.home() / 'Local/.hu20-m4-research.lock').open('a+') as ordinary, (root.parent / '.second-to-act-qualification.lock').open('a+') as study:
            for lock in (ordinary, study):
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            admission = sample(root, thermal)
            if admission['available_ram_bytes'] < 7 * 2**30:
                raise ValueError('6GiB conservative fixture-family forecast +1GiB headroom unavailable')
            paths = json.loads(catalog.read_text())
            inv = inventory(paths)
            write(root / 'input-inventory.json', inv)
            if any(r['players'] == 3 for r in inv['candidates']):
                raise ValueError('potential three-player input found; review full admission instead of fixture-only closeout')
            names = subprocess.check_output(['git', 'ls-files'], cwd=SOURCE, text=True).splitlines()
            c = dict(scope='fixture-only; model-panel-unrun', source=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip(),
                     source_files={n:sha(SOURCE/n) for n in names if (SOURCE/n).is_file()},
                     python=sys.executable, python_sha256=sha(sys.executable),
                     catalog_sha256=sha(catalog), inventory_sha256=sha(root/'input-inventory.json'),
                     borrowed_thermal=str(thermal), borrowed_thermal_sha256=sha(thermal),
                     admission=admission, forecast_family_ram_bytes=6*2**30,
                     ordinary_lock_inode=os.fstat(ordinary.fileno()).st_ino,
                     study_lock_inode=os.fstat(study.fileno()).st_ino,
                     native_test_threads=2, rayon_threads=1, started_epoch=started)
            write(root/'config.json', c)
            env = {**os.environ, 'PYTHONPATH':str(SOURCE), 'CARGO_TARGET_DIR':str(root/'target'),
                   'CARGO_BUILD_JOBS':'2', 'RAYON_NUM_THREADS':'1', 'RUST_TEST_THREADS':'2',
                   'OMP_NUM_THREADS':'1', 'OPENBLAS_NUM_THREADS':'1', 'MKL_NUM_THREADS':'1'}
            sup = Supervisor(root, env, thermal)
            owned_thermal = root/'thermal-state'
            sup.stage('thermal-build', ['swiftc', SOURCE/'scripts/support/m4_thermal_state.swift', '-o', owned_thermal])
            sup.thermal = owned_thermal
            cargo = str(Path.home()/'.cargo/bin/cargo')
            args = [cargo, 'test', '--release', '--locked', '--offline', '--manifest-path', SOURCE/'native/hu20-trainer/Cargo.toml']
            sup.stage('native-tests', [*args, '--lib', '--', '--test-threads=2'])
            sup.stage('panel-tests', [*args, '--example', 'nplayer_river_panel', '--', '--test-threads=2'])
            sup.stage('python-tests', [sys.executable, '-m', 'unittest', 'tests.test_river_second_to_act_m4',
                                      'tests.test_river_arena_expectation', 'tests.test_river_whole_hand_pilot'])
            sup.stage('panel-build', [cargo, 'build', '--release', '--locked', '--offline', '--manifest-path',
                                     SOURCE/'native/hu20-trainer/Cargo.toml', '--example', 'nplayer_river_panel'])
            binary = root/'target/release/examples/nplayer_river_panel'
            for i in (0, 1):
                sup.stage(f'panel-generate-{i}', [binary, root/f'panel-{i}.jsonl'])
            panel = verify_panel(root/'panel-0.jsonl')
            if sha(root/'panel-1.jsonl') != panel['sha256']:
                raise ValueError('panel reproduction differs')
            if inv != inventory(paths) or sha(thermal) != c['borrowed_thermal_sha256']:
                raise ValueError('borrowed input metadata/helper changed')
            result = dict(status='complete-fixtures-only-input-unresolved', source=c['source'],
                          config_sha256=sha(root/'config.json'), input_inventory_sha256=sha(root/'input-inventory.json'),
                          native_tests=test_receipt(root/'measurements/native-tests/stdout.log'),
                          panel_tests=test_receipt(root/'measurements/panel-tests/stdout.log'),
                          panel=dict(panel, byte_identical_reproduction=True),
                          binary_sha256=sha(binary), thermal_sha256=sha(owned_thermal),
                          compiler=subprocess.check_output([str(Path.home()/'.cargo/bin/rustc'), '-Vv'], text=True),
                          model_panel='unrun', cost_preflight='unrun-no-compatible-model',
                          policy_loads=0, model_solve_requests=0, new_arena_hands=0, new_training_nodes=0,
                          stage_costs=sup.costs, wall_seconds=time.time()-started,
                          no_bb128_work=True, no_archival_or_upload=True)
            write(root/'results.json', result)
            write(root/'status.json', dict(status=result['status'], result_sha256=sha(root/'results.json')))
    except BaseException as e:
        write(root/'failure.json', dict(error=repr(e), epoch=time.time(), preserve=True, automatic_retry=False))
        write(root/'status.json', dict(status='failed'))
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    p.add_argument('--catalog', required=True, type=Path)
    p.add_argument('--thermal', required=True, type=Path)
    a = p.parse_args()
    run(a.root.resolve(), a.catalog.resolve(), a.thermal.resolve())
