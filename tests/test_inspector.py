from __future__ import annotations

import csv
import json
from pathlib import Path

from benchmark.inspector import format_failure_report, inspect_failures, timeline


def test_inspect_failures_flags_population_budget_and_bankruptcy(tmp_path: Path) -> None:
    bad_run = tmp_path / "bad_run.json"
    bad_run.write_text(
        json.dumps(
            {
                "agent": "llama3:8b",
                "seed": 42,
                "turns": [
                    {
                        "turn": 0,
                        "state": {"population": 0, "budget": 10.0},
                        "action_outcomes": [{"applied": False, "reason": "insufficient_budget"}],
                        "disaster_events": [],
                    },
                    {
                        "turn": 1,
                        "state": {"population": 0, "budget": -5.0},
                        "action_outcomes": [{"applied": False, "reason": "insufficient_budget"}],
                        "disaster_events": [{"event": "recession"}],
                    },
                    {
                        "turn": 2,
                        "state": {"population": 0, "budget": -9.0},
                        "action_outcomes": [{"applied": False, "reason": "insufficient_budget"}],
                        "disaster_events": [],
                    },
                    {
                        "turn": 3,
                        "state": {"population": 0, "budget": -10.0},
                        "action_outcomes": [{"applied": False, "reason": "insufficient_budget"}],
                        "disaster_events": [],
                    },
                ],
                "final_state": {"population": 0, "budget": -10.0},
                "scores": {"composite": 25.0},
            }
        ),
        encoding="utf-8",
    )

    runs_index = tmp_path / "index.csv"
    with runs_index.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["run_id", "model", "seed", "scenario", "result_path"])
        writer.writerow(["exp_llama_seed42_default", "llama3:8b", 42, "default", str(bad_run)])

    records = inspect_failures(runs_index, model="llama3:8b", scenario="default")
    assert len(records) == 1

    flags = records[0]["failure_flags"]
    assert "final_population_zero" in flags
    assert "repeated_insufficient_budget" in flags
    assert "persistent_bankruptcy" in flags

    report = format_failure_report(records)
    assert "seed=42" in report
    assert "final_population_zero" in report


def test_timeline_outputs_compact_rows_with_rejected_counts(tmp_path: Path) -> None:
    run_path = tmp_path / "run.json"
    run_path.write_text(
        json.dumps(
            {
                "agent": "llama3:8b",
                "seed": 7,
                "turns": [
                    {
                        "turn": 0,
                        "state": {
                            "population": 10,
                            "budget": 100.0,
                            "revenue_per_tick": 5.0,
                            "expenses_per_tick": 2.0,
                            "pollution_avg": 0.1,
                        },
                        "action_outcomes": [{"applied": True}, {"applied": False, "reason": "invalid_zone"}],
                        "disaster_events": [],
                    },
                    {
                        "turn": 1,
                        "state": {
                            "population": 12,
                            "budget": 103.0,
                            "revenue_per_tick": 6.0,
                            "expenses_per_tick": 3.0,
                            "pollution_avg": 0.15,
                        },
                        "action_outcomes": [{"applied": False, "reason": "insufficient_budget"}],
                        "disaster_events": [{"event": "recession"}],
                    },
                ],
                "final_state": {"population": 12, "budget": 103.0},
                "scores": {"composite": 33.0},
            }
        ),
        encoding="utf-8",
    )

    table = timeline(run_path)

    assert "turn | pop | budget" in table
    assert "0 | 10 | 100.0" in table
    assert "1 | 12 | 103.0" in table
    assert "recession" in table
