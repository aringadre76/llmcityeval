from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

import yaml

from agents.ollama import OllamaAgent
from benchmark.runner import run as run_benchmark
from sim.runtime_config import SimConfig

ROOT = Path(__file__).resolve().parents[1]


def _safe_agent_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def load_matrix(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def find_result_for_run(agent: str, seed: int, results_dir: Path = None) -> Path | None:
    results_dir = results_dir or (ROOT / "results")
    safe = _safe_agent_name(agent)
    candidates = sorted(results_dir.glob(f"{safe}_{seed}_*.json"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        return None
    return candidates[-1]


def _load_completed_runs(index_path: Path) -> set[tuple[str, int, str]]:
    if not index_path.exists():
        return set()

    completed: set[tuple[str, int, str]] = set()
    with index_path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            result_path = row.get("result_path", "")
            if not result_path:
                continue
            completed.add((str(row.get("model", "")), int(row.get("seed", 0)), str(row.get("scenario", ""))))
    return completed


def build_sim_config_for_scenario(base_config: SimConfig, scenario: dict[str, Any]) -> SimConfig:
    overrides = dict(scenario.get("config_overrides") or {})
    updated: dict[str, float | int] = {}

    frequency_multiplier = float(overrides.get("disaster_frequency_multiplier", 1.0))
    severity_multiplier = float(overrides.get("disaster_severity_multiplier", 1.0))

    if "starting_budget" in overrides:
        updated["starting_budget"] = float(overrides["starting_budget"])
    if "starting_population" in overrides:
        updated["starting_population"] = int(overrides["starting_population"])

    def clamp_probability(value: float) -> float:
        return max(0.0, min(1.0, value))

    updated["disaster_recession_prob"] = clamp_probability(base_config.disaster_recession_prob * frequency_multiplier)
    updated["disaster_demand_surge_prob"] = clamp_probability(base_config.disaster_demand_surge_prob * frequency_multiplier)
    updated["disaster_infra_fail_prob"] = clamp_probability(base_config.disaster_infra_fail_prob * frequency_multiplier)
    updated["disaster_pollution_prob"] = clamp_probability(base_config.disaster_pollution_prob * frequency_multiplier)

    updated["disaster_recession_duration"] = max(1, int(round(base_config.disaster_recession_duration * severity_multiplier)))
    updated["disaster_demand_surge_duration"] = max(1, int(round(base_config.disaster_demand_surge_duration * severity_multiplier)))
    updated["disaster_infra_fail_duration"] = max(1, int(round(base_config.disaster_infra_fail_duration * severity_multiplier)))
    updated["pollution_event_increment"] = base_config.pollution_event_increment * severity_multiplier

    return base_config.with_updates(**updated)


def run_experiment(
    matrix_path: str | Path,
    experiment_name: str = "citybench_v1",
    turns: int = 50,
    results_dir: str | Path | None = None,
    model_filter: set[str] | None = None,
    seed_filter: set[int] | None = None,
    scenario_filter: set[str] | None = None,
    resume: bool = False,
):
    matrix = load_matrix(matrix_path)
    models = [m["id"] for m in matrix.get("models", [])]
    seeds = matrix.get("seeds", [])
    scenarios = matrix.get("scenarios", [])
    base_config = SimConfig.from_module()
    results_dir_path = Path(results_dir) if results_dir is not None else ROOT / "results"

    runs_dir = ROOT / "experiments" / experiment_name / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    index_path = runs_dir / "index.csv"
    # Ensure header exists
    if not index_path.exists():
        with index_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["run_id", "model", "seed", "scenario", "result_path"])
    completed_runs = _load_completed_runs(index_path) if resume else set()

    for model in models:
        if model_filter is not None and model not in model_filter:
            continue
        for seed in seeds:
            if seed_filter is not None and seed not in seed_filter:
                continue
            for scenario in scenarios:
                scenario_id = scenario.get("id", "default")
                if scenario_filter is not None and scenario_id not in scenario_filter:
                    continue
                if (model, int(seed), scenario_id) in completed_runs:
                    print(f"Skipping completed run model={model} seed={seed} scenario={scenario_id}")
                    continue
                print(f"Running model={model} seed={seed} scenario={scenario_id}")
                sim_config = build_sim_config_for_scenario(base_config, scenario)
                agent = OllamaAgent(model=model)
                run_benchmark(
                    agent=agent,
                    seed=seed,
                    turns=turns,
                    results_dir=str(results_dir_path),
                    sim_config=sim_config,
                )

                result = find_result_for_run(model, seed, results_dir=results_dir_path)
                run_id = f"{experiment_name}_{_safe_agent_name(model)}_seed{seed}_{scenario_id}"
                with index_path.open("a", newline="", encoding="utf-8") as fh:
                    writer = csv.writer(fh)
                    writer.writerow([run_id, model, seed, scenario_id, str(result) if result else ""])
                print(f"Recorded run {run_id} -> {result}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python benchmark/experiment_runner.py experiments/citybench_v1/config/matrix.yaml")
        raise SystemExit(2)
    run_experiment(sys.argv[1])

