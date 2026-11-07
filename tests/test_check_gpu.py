import json

import pytest

from scripts import check_gpu


def test_quick_check_reports_the_device_and_measurements(capsys):
    pytest.importorskip('torch')
    assert check_gpu.main(['--quick']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['device'] in ('cuda', 'mps', 'cpu')
    assert report['matmul_tflops']['float32'] > 0
    mlp = report['policy_mlp']
    assert mlp['steps_per_second'] > 0 and mlp['parameters'] == 256 * 128 + 128 + 2 * (128 * 128 + 128) + 128 * 6 + 6


def test_require_fails_when_the_device_is_missing(capsys, monkeypatch):
    torch = pytest.importorskip('torch')
    monkeypatch.setattr(check_gpu, 'device', lambda _: torch.device('cpu'))
    assert check_gpu.main(['--quick', '--require', 'cuda']) == 1
    assert 'required device cuda' in capsys.readouterr().err
