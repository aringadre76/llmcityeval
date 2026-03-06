from __future__ import annotations

import csv
import json
from pathlib import Path

from benchmark.aggregate_metrics import aggregate, write_per_run_metrics


def test_write_per_run_metrics_uses_scenario_from_runs_index(tmp_path: Path) -> None:
    result_path = tmp_path / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "agent": "m1",
                "seed": 7,
                "turns": [],
                "final_state": {"population": 0},
                "scores": {"population": 1.0, "efficiency": 2.0, "stability": 3.0, "resilience": 4.0, "composite": 5.0},
            }
        ),
        encoding="utf-8",
    )
    runs_index = tmp_path / "index.csv"
    with runs_index.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["run_id", "model", "seed", "scenario", "result_path"])
        writer.writerow(["exp1_m1_seed7_stress", "m1", 7, "stress", str(result_path)])

    per_run = tmp_path / "per_run_metrics.jsonl"
    write_per_run_metrics(runs_index, per_run, experiment="exp1")

    lines = per_run.read_text(encoding="utf-8").strip().splitlines()
    payload = json.loads(lines[0])
    assert payload["scenario"] == "stress"


def test_aggregate_writes_best_model_summary(tmp_path: Path) -> None:
    per_run = tmp_path / "per_run_metrics.jsonl"
    per_run.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "experiment": "exp1",
                        "model": "m1",
                        "scenario": "stress",
                        "metrics": {"final_score": 10.0, "hard_constraint_violations": 2, "avg_recovery_turns": 4.0},
                    }
                ),
                json.dumps(
                    {
                        "experiment": "exp1",
                        "model": "m2",
                        "scenario": "stress",
                        "metrics": {"final_score": 20.0, "hard_constraint_violations": 1, "avg_recovery_turns": 3.0},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary_csv = tmp_path / "summary_by_model.csv"
    summary_json = tmp_path / "summary_overall.json"
    aggregate(per_run, summary_csv, summary_json)

    overall = json.loads(summary_json.read_text(encoding="utf-8"))
    assert overall["best_model_by_final_score"]["stress"] == "m2"
