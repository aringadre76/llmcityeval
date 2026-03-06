from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from benchmark.metrics import extract_per_run_metrics

ROOT = Path(__file__).resolve().parents[1]


def read_runs_index(index_path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with open(index_path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            rows.append(r)
    return rows


def write_per_run_metrics(runs_index_path: str | Path, out_path: str | Path, experiment: str = "citybench_v1"):
    runs = read_runs_index(runs_index_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for r in runs:
            result_path = r.get("result_path")
            if not result_path:
                continue
            try:
                metrics = extract_per_run_metrics(
                    result_path,
                    experiment=experiment,
                    scenario=str(r.get("scenario", "default")),
                    run_id=str(r.get("run_id", "")) or None,
                )
            except Exception:
                continue
            fh.write(json.dumps(metrics) + "\n")


def aggregate(per_run_jsonl: str | Path, summary_csv: str | Path, summary_json: str | Path):
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    with open(per_run_jsonl, "r", encoding="utf-8") as fh:
        for line in fh:
            obj = json.loads(line)
            model = obj.get("model", "unknown")
            scenario = obj.get("scenario", "default")
            groups[(model, scenario)].append(obj)

    # write csv
    with open(summary_csv, "w", newline="", encoding="utf-8") as fh:
        fieldnames = [
            "model",
            "scenario",
            "num_runs",
            "final_score_mean",
            "final_score_std",
            "final_score_min",
            "final_score_max",
            "hard_constraint_violations_mean",
            "avg_recovery_turns_mean",
        ]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        overall: dict[str, Any] = {
            "experiment": Path(per_run_jsonl).parents[1].name,
            "metrics": {},
            "baseline_model": None,
            "best_model_by_final_score": {},
        }
        best_by_scenario: dict[str, tuple[str, float]] = {}
        for (model, scenario), items in sorted(groups.items()):
            final_scores = [it["metrics"]["final_score"] for it in items]
            hard_viol = [it["metrics"].get("hard_constraint_violations", 0) for it in items]
            recovery = [it["metrics"].get("avg_recovery_turns", 0.0) for it in items]

            row = {
                "model": model,
                "scenario": scenario,
                "num_runs": len(items),
                "final_score_mean": mean(final_scores) if final_scores else 0.0,
                "final_score_std": pstdev(final_scores) if len(final_scores) > 1 else 0.0,
                "final_score_min": min(final_scores) if final_scores else 0.0,
                "final_score_max": max(final_scores) if final_scores else 0.0,
                "hard_constraint_violations_mean": mean(hard_viol) if hard_viol else 0.0,
                "avg_recovery_turns_mean": mean(recovery) if recovery else 0.0,
            }
            writer.writerow(row)

            overall["metrics"].setdefault(scenario, {})[model] = {
                "num_runs": len(items),
                "final_score": {
                    "mean": row["final_score_mean"],
                    "std": row["final_score_std"],
                    "min": row["final_score_min"],
                    "max": row["final_score_max"],
                },
                "hard_constraint_violations": {"mean": row["hard_constraint_violations_mean"]},
                "avg_recovery_turns": {"mean": row["avg_recovery_turns_mean"]},
            }
            best = best_by_scenario.get(scenario)
            if best is None or row["final_score_mean"] > best[1]:
                best_by_scenario[scenario] = (model, row["final_score_mean"])

        overall["best_model_by_final_score"] = {
            scenario: model for scenario, (model, _score) in sorted(best_by_scenario.items())
        }
        with open(summary_json, "w", encoding="utf-8") as oh:
            json.dump(overall, oh, indent=2)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 4:
        print("Usage: python benchmark/aggregate_metrics.py <runs/index.csv> <per_run_metrics.jsonl> <summary_dir>")
        raise SystemExit(2)
    runs_index = sys.argv[1]
    per_run = sys.argv[2]
    summary_dir = Path(sys.argv[3])
    summary_dir.mkdir(parents=True, exist_ok=True)
    write_per_run_metrics(runs_index, per_run)
    aggregate(per_run, summary_dir / "summary_by_model.csv", summary_dir / "summary_overall.json")

