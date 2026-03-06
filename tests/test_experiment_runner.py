from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

import benchmark.experiment_runner as experiment_runner
from benchmark.experiment_runner import build_sim_config_for_scenario
from sim.runtime_config import SimConfig


def test_build_sim_config_for_scenario_applies_supported_overrides() -> None:
    base_config = SimConfig(
        starting_budget=2000.0,
        disaster_recession_prob=0.10,
        disaster_demand_surge_prob=0.20,
        disaster_infra_fail_prob=0.30,
        disaster_pollution_prob=0.40,
        disaster_recession_duration=3,
        disaster_demand_surge_duration=2,
        disaster_infra_fail_duration=1,
        pollution_event_increment=0.4,
    )

    scenario = {
        "id": "stress",
        "config_overrides": {
            "starting_budget": 2500.0,
            "disaster_frequency_multiplier": 2.0,
            "disaster_severity_multiplier": 2.0,
        },
    }

    sim_config = build_sim_config_for_scenario(base_config, scenario)

    assert sim_config.starting_budget == 2500.0
    assert sim_config.disaster_recession_prob == 0.20
    assert sim_config.disaster_demand_surge_prob == 0.40
    assert sim_config.disaster_infra_fail_prob == 0.60
    assert sim_config.disaster_pollution_prob == 0.80
    assert sim_config.disaster_recession_duration == 6
    assert sim_config.disaster_demand_surge_duration == 4
    assert sim_config.disaster_infra_fail_duration == 2
    assert sim_config.pollution_event_increment == 0.8


def test_build_sim_config_for_scenario_clamps_probabilities() -> None:
    base_config = SimConfig(
        disaster_recession_prob=0.7,
        disaster_demand_surge_prob=0.8,
        disaster_infra_fail_prob=0.9,
        disaster_pollution_prob=1.0,
    )

    scenario = {
        "id": "maxed",
        "config_overrides": {
            "disaster_frequency_multiplier": 2.0,
        },
    }

    sim_config = build_sim_config_for_scenario(base_config, scenario)

    assert sim_config.disaster_recession_prob == 1.0
    assert sim_config.disaster_demand_surge_prob == 1.0
    assert sim_config.disaster_infra_fail_prob == 1.0
    assert sim_config.disaster_pollution_prob == 1.0


def test_run_experiment_filters_and_resumes_completed_runs(tmp_path: Path, monkeypatch) -> None:
    matrix_path = tmp_path / "matrix.yaml"
    matrix_path.write_text(
        yaml.safe_dump(
            {
                "name": "exp1",
                "models": [{"id": "m1"}, {"id": "m2"}],
                "seeds": [1, 2],
                "scenarios": [
                    {"id": "default", "config_overrides": {}},
                    {"id": "stress", "config_overrides": {"starting_budget": 3000.0}},
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(experiment_runner, "ROOT", tmp_path)

    runs_dir = tmp_path / "experiments" / "exp1" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    index_path = runs_dir / "index.csv"
    with index_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["run_id", "model", "seed", "scenario", "result_path"])
        writer.writerow(["exp1_m1_seed1_default", "m1", 1, "default", "/tmp/already.json"])

    calls: list[tuple[str, int, float]] = []

    class FakeAgent:
        def __init__(self, model: str) -> None:
            self.name = model

    def fake_run_benchmark(*, agent, seed, turns, results_dir, sim_config, verbose=False):
        _ = turns
        _ = verbose
        calls.append((agent.name, seed, sim_config.starting_budget))
        result_path = Path(results_dir) / f"{agent.name}_{seed}_fake.json"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps({"agent": agent.name, "seed": seed, "turns": [], "scores": {}}), encoding="utf-8")
        return object()

    monkeypatch.setattr(experiment_runner, "OllamaAgent", FakeAgent)
    monkeypatch.setattr(experiment_runner, "run_benchmark", fake_run_benchmark)

    experiment_runner.run_experiment(
        matrix_path,
        experiment_name="exp1",
        turns=5,
        model_filter={"m1"},
        seed_filter={1, 2},
        scenario_filter={"default", "stress"},
        resume=True,
    )

    assert calls == [("m1", 1, 3000.0), ("m1", 2, 2000.0), ("m1", 2, 3000.0)]
