import json
import os
from pathlib import Path

import numpy as np
import pytest

from scripts import suit_symmetry_pilot as pilot


def rows(n=48):
    rng = np.random.default_rng(81)
    x = rng.integers(0, 256, (n, 612), dtype=np.uint8)
    x[:, pilot.HOLE:pilot.CARDS_END] = 0
    street = np.arange(n, dtype=np.uint8) % 3 + 1
    for i, s in enumerate(street):
        cards = rng.choice(52, int(s) + 4, replace=False)
        x[i, pilot.HOLE + cards[:2]] = 255
        x[i, pilot.BOARD + cards[2:]] = 255
    x[:, 22:28] = [0, 255, 255, 0, 0, 0]
    return x, street


def test_all_suit_permutations_preserve_canonical_observable_input():
    x, _ = rows()
    c = pilot.canonicalize(x)
    assert np.array_equal(pilot.canonicalize(c), c)
    assert np.array_equal(x[:, :pilot.HOLE], c[:, :pilot.HOLE])
    assert np.array_equal(x[:, pilot.CARDS_END:], c[:, pilot.CARDS_END:])
    for p in pilot.PERMUTATIONS:
        transformed = pilot.permute(x, p)
        assert np.array_equal(pilot.canonicalize(transformed), c)
        # Per-rank card counts and shared-suit relationships are retained.
        for start in (pilot.HOLE, pilot.BOARD):
            assert np.array_equal(x[:, start:start + 52].reshape(-1, 13, 4).sum(2),
                                  c[:, start:start + 52].reshape(-1, 13, 4).sum(2))


def test_tied_suits_and_observation_orbit_deduplication():
    x = np.zeros((1, 612), np.uint8)
    x[0, pilot.HOLE + np.array([48, 49])] = 255
    x[0, pilot.BOARD + np.array([0, 1, 10])] = 255
    for p in pilot.PERMUTATIONS:
        assert pilot.orbit_keys(x) == pilot.orbit_keys(pilot.permute(x, p))
    different_history = x.copy()
    different_history[0, 200] = 1
    assert pilot.orbit_keys(x) != pilot.orbit_keys(different_history)
    # Different flush structure cannot collapse into the same canonical state.
    offsuit = x.copy()
    offsuit[0, pilot.HOLE + 49] = 0
    offsuit[0, pilot.HOLE + 50] = 255
    assert pilot.orbit_keys(x) != pilot.orbit_keys(offsuit)


def test_validation_rejects_cards_masks_and_illegal_targets():
    x, street = rows()
    legal = np.full(len(x), 6, np.uint8)
    target = np.tile([0, .4, .6, 0, 0, 0], (len(x), 1)).astype(np.float32)
    assert np.allclose(pilot.validate_rows(x, legal, street, target).sum(1), 1)
    bad = x.copy()
    bad[0, pilot.BOARD + np.flatnonzero(x[0, pilot.HOLE:pilot.BOARD])[0]] = 255
    with pytest.raises(ValueError, match='overlapping'):
        pilot.validate_rows(bad, legal, street, target)
    with pytest.raises(ValueError, match='mask'):
        pilot.validate_rows(x, legal + 1, street, target)
    bad_target = target.copy()
    bad_target[0, 0] = .1
    with pytest.raises(ValueError, match='probabilities'):
        pilot.validate_rows(x, legal, street, bad_target)


def test_original_hand_clustering_weights_deals_equally():
    result = pilot.interval(np.array([1., 1., 1., -1.]), np.array([4, 4, 4, 5]))
    assert result['hands'] == 2
    assert result['mean'] == 0


def test_python_canonical_key_matches_native_receipt():
    receipt = os.environ.get('SUIT_SYMMETRY_NATIVE_RECEIPT')
    if not receipt:
        pytest.skip('run native suit_symmetry_proof example and set receipt path')
    data = json.loads(Path(receipt).read_text())
    assert data['passed'] and data['checks'] == 3072 * 24
    x = np.zeros((len(data['cases']), 612), np.uint8)
    for i, case in enumerate(data['cases']):
        x[i, pilot.HOLE + np.array(case['hole'])] = 255
        x[i, pilot.BOARD + np.array(case['board'])] = 255
    canonical = pilot.canonicalize(x)
    for i, case in enumerate(data['cases']):
        key = 0
        for suit in range(4):
            h = sum((int(canonical[i, pilot.HOLE + rank * 4 + suit]) // 255) << rank for rank in range(13))
            b = sum((int(canonical[i, pilot.BOARD + rank * 4 + suit]) // 255) << rank for rank in range(13))
            key = (key << 26) | (h << 13) | b
        assert str(key) == case['key']
