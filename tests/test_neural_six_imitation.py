import json
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import neural_six_imitation as six
from scripts import neural_policy_imitation as imitation
from scripts import neural_six_run as controller
from tests.test_neural_policy_imitation import write


def test_export_is_fixed_depth_and_has_disjoint_roots(tmp_path):
    m = six.export_manifest(tmp_path, tmp_path, tmp_path, 9, verify=False)
    assert list(m['models']) == ['six'] and m['teachers'] == ['six']
    assert sum(j['hands'] for j in m['jobs'] if j['name'].startswith('train-')) == 2400000
    assert sum(j['hands'] for j in m['jobs'] if j['name'].startswith('heldout-')) == 120000
    assert all(j['stacks'] == [100] * 6 and j['players'] == len(j['seats']) == 6 for j in m['jobs'])
    assert all('peer' not in j['seats'] for j in m['jobs'])
    q = six.export_manifest(tmp_path, tmp_path, tmp_path, 9, qualification=True, verify=False)
    assert [j['threads'] for j in q['jobs']] == [1, 9]
    assert q['jobs'][0]['root'] == q['jobs'][1]['root']
    assert len({j['root'] for j in m['jobs'] + q['jobs']}) == 13
    eval_roots = {six.ARENA_ROOT + 100000 * (r - 1) + 1000 * b + i
                  for r in (1, 2, 3) for b in range(4 if r == 1 else 1) for i in range(6)}
    assert eval_roots.isdisjoint({j['root'] for j in m['jobs'] + q['jobs']})


def gate_result(tmp_path, run, point, lower=-9, harm=False, check_harm=False):
    fields = {f: {'harm_flag': harm if f == 'random' else check_harm if f == 'check-call' else False}
              for f in six.gate_tables(run)[0]['fields']}
    fields['trained'] = {'change': {'adjusted': {'mean_bb100': point}},
                         'decision_interval': [lower, point + 5],
                         'verdict': 'non-inferior' if lower > -10 else 'non-inferiority not shown'}
    p = tmp_path / f'run{run}.json'
    p.write_text(json.dumps({'tables': {'6p-100bb': {'study': 'deep', 'primary': 'trained', 'fields': fields}}}))
    return p


def test_gate_d_keeps_strict_margin_replication_and_check_call_exemption(tmp_path):
    paths = [gate_result(tmp_path, r, -3, check_harm=True) for r in (1, 2, 3)]
    assert six.decide(paths)['gate_d']['passed']
    gate_result(tmp_path, 1, -3, lower=-10)
    assert not six.decide(paths)['gate_d']['passed']
    gate_result(tmp_path, 1, -3, harm=True)
    assert not six.decide(paths)['gate_d']['passed']
    gate_result(tmp_path, 1, -3)
    gate_result(tmp_path, 3, -10)
    assert not six.decide(paths)['gate_d']['passed']
    paths[0].write_text('{"tables": {}}')
    with pytest.raises(ValueError, match='Gate D only'):
        six.decide(paths)


def test_disk_cache_is_identical_to_original_positive_rows(tmp_path):
    paths = [tmp_path / f'data{i}.npfeat' for i in (1, 2)]
    for p in paths:
        write(p, 'six', 107, np.random.default_rng(int(p.stem[-1])), rescue_share=.3)
    original = imitation.training_arrays(paths)
    cached = imitation.cached_training_arrays(paths, tmp_path / 'cache', chunk=13)
    assert original[-1] == cached[-1]
    for a, b in zip(original[:-1], cached[:-1]):
        np.testing.assert_array_equal(a, b)
    with pytest.raises(FileExistsError):
        imitation.cached_training_arrays(paths, tmp_path / 'cache')


def test_cached_and_ram_training_have_identical_weights_on_cpu(tmp_path, monkeypatch):
    torch = pytest.importorskip('torch')
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: False)
    p = tmp_path / 'train.npfeat'
    write(p, 'six', 211, np.random.default_rng(1), rescue_share=.2)
    for name, cache in [('ram', None), ('mapped', tmp_path / 'cache')]:
        imitation.train(SimpleNamespace(data=[str(p)], seed=3, out=str(tmp_path / name), array_cache=cache),
                        hidden=(16,), epochs=2, batch=32)
    a, b = [torch.load(tmp_path / name / 'weights.pt', weights_only=True) for name in ('ram', 'mapped')]
    assert all(torch.equal(a[k], b[k]) for k in a)


def test_gate_table_is_exactly_step_four_gate_d():
    for run in (1, 2, 3):
        t, = six.gate_tables(run)
        assert t['fallback'] == ['uniform', f'network-all:net{run}']
        assert t['fields']['trained'] == ['peer'] * 5
        assert len(t['fields']) == 6 and t['views'] == ['native', 'native']


def test_guard_reserves_and_deadline_fail_closed():
    g = controller.GIB
    s = {'available_bytes': 4 * g, 'free_disk_bytes': 10 * g, 'gpu_c': 86.9}
    reason = controller.stop_reason
    assert reason(s, 100, 99) is None
    assert reason(s, 100, 100) == 'work deadline'
    assert reason(s, 100, 99, True) == 'STOP file'
    assert reason(s | {'available_bytes': 4 * g - 1}, 100, 99) == 'memory reserve'
    assert reason(s | {'free_disk_bytes': 10 * g - 1}, 100, 99) == 'disk reserve'
    assert reason(s | {'gpu_c': 87}, 100, 99) == 'GPU temperature'


def test_controller_stops_on_failed_child_and_records_command(tmp_path, monkeypatch):
    import sys
    import time
    monkeypatch.setattr(controller, 'resources', lambda _: {'available_bytes': 8 * controller.GIB,
                        'free_disk_bytes': 100 * controller.GIB, 'gpu_c': 40})
    r = controller.Runner(SimpleNamespace(out=tmp_path / 'run', deadline=time.time() + 60))
    with pytest.raises(RuntimeError, match='exit 7'):
        r.run('failure', [sys.executable, '-c', 'raise SystemExit(7)'])
    assert json.loads((r.root / 'stages.jsonl').read_text())['stage'] == 'failure'
    assert (r.root / 'logs' / '001-failure.log').exists()


def test_guard_uses_the_pods_cgroup_v1_memory_limit(tmp_path, monkeypatch):
    from pathlib import Path
    files = {'/proc/meminfo': 'MemAvailable: 100000000 kB\n',
             '/sys/fs/cgroup/memory/memory.limit_in_bytes': '50000000000',
             '/sys/fs/cgroup/memory/memory.usage_in_bytes': '47000000000'}
    monkeypatch.setattr(Path, 'exists', lambda p: str(p) in files)
    monkeypatch.setattr(Path, 'read_text', lambda p: files[str(p)])
    monkeypatch.setattr(controller.shutil, 'disk_usage', lambda p: SimpleNamespace(free=100 * controller.GIB))
    monkeypatch.setattr(controller.subprocess, 'check_output', lambda *a, **k: '40, 100\n')
    s = controller.resources(tmp_path)
    assert s['available_bytes'] == 3000000000
    assert controller.stop_reason(s, 100, 99) == 'memory reserve'
