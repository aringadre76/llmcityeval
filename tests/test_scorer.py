from __future__ import annotations

from benchmark.scorer import _population_series, score_run


def test_population_series_normal() -> None:
    run_data = {
        "turns": [{"state": {"population": 10}}, {"state": {"population": 20}}],
        "final_state": {"population": 30},
    }
    assert _population_series(run_data) == [10.0, 20.0, 30.0]


def test_population_series_missing_state() -> None:
    run_data = {"turns": [{}, {"state": None}], "final_state": {}}
    assert _population_series(run_data) == [0.0, 0.0, 0.0]


def test_population_series_malformed_turns() -> None:
    run_data = {"turns": [None, "bad", 3, {"state": {"population": "7"}}], "final_state": {"population": "9"}}
    assert _population_series(run_data) == [0.0, 0.0, 0.0, 7.0, 9.0]


def test_score_run_empty() -> None:
    scores = score_run({})
    assert set(scores.keys()) == {"population", "efficiency", "stability", "resilience", "composite"}
    assert all(0.0 <= value <= 100.0 for value in scores.values())


def test_score_run_handles_malformed_turn_objects() -> None:
    run_data = {
        "turns": [None, {"turn": "x", "budget_spent": "bad", "disaster_events": "bad"}, {"turn": 1, "state": {}}],
        "final_state": {"population": 0},
    }
    scores = score_run(run_data)
    assert all(0.0 <= value <= 100.0 for value in scores.values())


def test_resilience_no_disasters_is_100() -> None:
    run_data = {
        "turns": [{"turn": 0, "state": {"population": 10}, "disaster_events": []}],
        "final_state": {"population": 10},
    }
    scores = score_run(run_data)
    assert scores["resilience"] == 100.0
