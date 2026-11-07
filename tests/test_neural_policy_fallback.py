import json
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import neural_policy_fallback as fallback
from scripts import neural_policy_imitation as imitation
from scripts import nplayer_loss_diagnosis as diagnosis
from scripts import openpoker_phantom_depth as study


def test_tables_compare_uniform_and_the_runs_network_on_the_same_model():
    tables = fallback.tables(2)
    assert [t['table'] for t in tables] == ['3p-5bb', '3p-short-deep', '3p-unequal', '4p-short-deep', '6p-5bb', '6p-short-deep', '6p-unequal']
    for t in tables:
        assert t['focals'] == ['widemix', 'widemix'] and t['fallback'] == ['uniform', 'network:net2']
        assert list(t['fields'])[0] == 'mixed' and ('live-copies' in t['fields']) == (t['players'] == 6)
    assert fallback.verdict('fallback', 0.1, 3) == 'network better'
    assert fallback.verdict('fallback', -3, -0.1) == 'uniform better'
    assert fallback.verdict('fallback', -1, 1) == 'no difference shown'


def test_manifest_carries_the_networks_and_each_arms_fallback(tmp_path, monkeypatch):
    model = tmp_path / 'widemix.bin'
    model.write_bytes(b'w')
    models = tmp_path / 'models.json'
    models.write_text(json.dumps({'widemix': {'path': str(model), 'sha256': study.sha(model), 'mass': str(tmp_path), 'mass_sha256': '0' * 64}}))
    nets = tmp_path / 'networks.json'
    nets.write_text(json.dumps({'net1': {'path': '/n.npnet', 'sha256': 'a' * 64}}))
    monkeypatch.setattr(study, 'tables', lambda: fallback.tables(1))
    monkeypatch.setattr(study, 'BANKS', 1)
    study.manifest(SimpleNamespace(out=tmp_path / 'out', models=models, networks=nets))
    m = json.loads((tmp_path / 'out' / 'arena-manifest-b0.json').read_text())
    assert m['networks'] == {'net1': {'path': '/n.npnet', 'sha256': 'a' * 64}}
    assert len(m['cases']) == 38 and all(c['focal_untrained_fallback'] == ['uniform', 'network:net1'] for c in m['cases'])


def row(status, action, check, network=None):
    lookup = {'status': status}
    if network is not None:
        lookup['network'] = network
    return {'actors': [0], 'actions': [action], 'states': [{'legal': {'check': check}}], 'lookups': [lookup]}


def test_network_fallbacks_must_record_a_legal_positive_probability_label():
    mode = 'network:net1'
    p = [0, 0.5, 0, 0.5, 0, 0]
    assert diagnosis.fallback_violations(row('missing', ['check', 0], True, {'p': p, 'label': 1}), 0, mode) == 0
    assert diagnosis.fallback_violations(row('zero_mass', ['raise', 400], True, {'p': p, 'label': 3}), 0, mode) == 0
    assert diagnosis.fallback_violations(row('missing', ['check', 0], True), 0, mode) == 1, 'no network record'
    assert diagnosis.fallback_violations(row('missing', ['call', 0], True, {'p': p, 'label': 2}), 0, mode) == 1, 'zero probability'
    assert diagnosis.fallback_violations(row('missing', ['raise', 400], True, {'p': p, 'label': 1}), 0, mode) == 1, 'label differs'
    assert diagnosis.fallback_violations(row('positive_mass', ['check', 0], True, {'p': p, 'label': 1}), 0, mode) == 1, 'trained row'
    assert diagnosis.fallback_violations(row('positive_mass', ['check', 0], True), 0, mode) == 0
    assert diagnosis.fallback_violations(row('missing', ['check', 0], True, {'p': p, 'label': 1}), 1, mode) == 1, 'not the focal'


def test_export_writes_every_layer_in_the_rust_layout(tmp_path):
    torch = pytest.importorskip('torch')
    out = tmp_path / 'model'
    out.mkdir()
    net = imitation.network(torch, 8, (4,))
    torch.save(net.state_dict(), out / 'weights.pt')
    (out / 'model.json').write_text(json.dumps({'features': 8, 'hidden': [4], 'layout_sha256': 'ab' * 32,
                                                'weights_sha256': 'cd' * 32, 'seed': 1}))
    path = tmp_path / 'n.npnet'
    imitation.export(SimpleNamespace(model=str(out), out=str(path)))
    b = path.read_bytes()
    assert b[:8] == imitation.NET_MAGIC
    size = int.from_bytes(b[8:16], 'little')
    header = json.loads(b[16:16 + size])
    assert header['layers'] == [{'in': 8, 'out': 4}, {'in': 4, 'out': 6}]
    floats = np.frombuffer(b[16 + size:], '<f4')
    assert len(floats) == 8 * 4 + 4 + 4 * 6 + 6
    assert np.allclose(floats[:32].reshape(4, 8), net[0].weight.detach().numpy())
