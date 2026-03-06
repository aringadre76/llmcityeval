from __future__ import annotations

from pathlib import Path

import benchmark.experiments_cli as experiments_cli
from benchmark.uploader import upload


def test_cli_run_forwards_filters_and_resume(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_experiment(*args, **kwargs) -> None:
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(experiments_cli, "run_experiment", fake_run_experiment)

    experiments_cli.main(
        [
            "run",
            "--matrix",
            "experiments/citybench_v1/config/matrix.yaml",
            "--experiment",
            "citybench_v1",
            "--model",
            "llama3:8b",
            "--seed",
            "42",
            "--scenario",
            "stress",
            "--resume",
        ]
    )

    kwargs = captured["kwargs"]
    assert kwargs["model_filter"] == {"llama3:8b"}
    assert kwargs["seed_filter"] == {42}
    assert kwargs["scenario_filter"] == {"stress"}
    assert kwargs["resume"] is True


def test_upload_copies_metrics_summaries_for_file_target(tmp_path: Path) -> None:
    experiment_root = tmp_path / "experiments" / "citybench_v1" / "metrics"
    experiment_root.mkdir(parents=True)
    (experiment_root / "summary_overall.json").write_text('{"ok": true}', encoding="utf-8")
    (experiment_root / "summary_by_model.csv").write_text("model\nllama3:8b\n", encoding="utf-8")

    target_dir = tmp_path / "central-store"
    upload("citybench_v1", experiment_root, f"file://{target_dir}")

    assert (target_dir / "citybench_v1" / "summary_overall.json").exists()
    assert (target_dir / "citybench_v1" / "summary_by_model.csv").exists()
