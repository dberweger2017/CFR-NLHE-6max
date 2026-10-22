from copy import deepcopy

import pytest

from scripts.river_search_round2_compare import summarize


def records():
    rows = []
    for index in range(2):
        for phase in ("strict", "deployment"):
            for menu, gain in (("base", 2.0), ("expanded", 0.5)):
                rows.append({
                    "case_index": index, "directory": "panel", "hand": index,
                    "menu": menu, "phase": phase, "decision_seconds": 0.2,
                    "result": {"checkpoints": [{"target_met": index == 0 or menu == "expanded"}],
                               "law": {"id": "same"}, "nodes": 40, "solver_memory_bytes": 1024,
                               "omitted_raise_evaluation": {
                                   # Hero is seat 1: the primary opponent is seat 0.
                                   "hero_game_seat": 1,
                                   "quality": {"best_response_gains_bb": [gain, 20.]},
                                   "blueprint_only_quality": {"best_response_gains_bb": [1., 30.]}}}})
    return rows


def test_primary_tracks_opponent_and_excludes_unqualified_pairs_without_dropping_them():
    result = summarize(list(reversed(records())), {"menus": ["base", "expanded"]})
    assert result["pairs"] == 2
    assert result["qualified_pairs"] == 1
    assert result["inconclusive_pairs"] == 1
    assert len(result["per_case"]) == 2
    assert result["primary_opponent_gain_reduction_bb"]["median"] == 1.5
    assert result["arms"]["base"]["regressions_vs_blueprint_qualified_pairs"] == 1
    assert result["arms"]["expanded"]["regressions_vs_blueprint_qualified_pairs"] == 0


@pytest.mark.parametrize("field", ["law", "blueprint"])
def test_mismatched_beliefs_or_blueprint_stop_the_comparison(field):
    rows = deepcopy(records())
    if field == "law":
        rows[1]["result"]["law"] = {"id": "changed"}
    else:
        rows[1]["result"]["omitted_raise_evaluation"]["blueprint_only_quality"]["best_response_gains_bb"][0] = 2.
    with pytest.raises(ValueError):
        summarize(rows, {"menus": ["base", "expanded"]})
