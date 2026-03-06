from __future__ import annotations

import json
from pathlib import Path

from benchmark.metrics import extract_per_run_metrics


def test_extract_per_run_metrics_counts_disasters_and_recovery(tmp_path: Path) -> None:
    result_path = tmp_path / "run.json"
    result_path.write_text(
        json.dumps(
            {
                "agent": "test-model",
                "seed": 42,
                "turns": [
                    {
                        "turn": 0,
                        "state": {"population": 10},
                        "action_outcomes": [{"applied": False, "reason": "insufficient_budget"}],
                        "budget_spent": 50.0,
                        "disaster_events": [{"event": "recession", "outcome": "applied"}],
                    },
                    {
                        "turn": 1,
                        "state": {"population": 8},
                        "action_outcomes": [],
                        "budget_spent": 0.0,
                        "disaster_events": [],
                    },
                    {
                        "turn": 2,
                        "state": {"population": 10},
                        "action_outcomes": [],
                        "budget_spent": 0.0,
                        "disaster_events": [],
                    },
                ],
                "final_state": {"population": 12},
                "scores": {"composite": 25.0},
            }
        ),
        encoding="utf-8",
    )

    metrics = extract_per_run_metrics(result_path, experiment="exp1")

    assert metrics["model"] == "test-model"
    assert metrics["seed"] == 42
    assert metrics["metrics"]["hard_constraint_violations"] == 1
    assert metrics["metrics"]["num_disasters"] == 1
    assert metrics["metrics"]["avg_recovery_turns"] == 2.0
