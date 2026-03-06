from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from run import _is_run_log, compare_results


def test_is_run_log_validation() -> None:
    assert _is_run_log({"scores": {}, "turns": []}) is True
    assert _is_run_log({"scores": [], "turns": []}) is False
    assert _is_run_log({"scores": {}, "turns": None}) is False
    assert _is_run_log({}) is False
    assert _is_run_log([]) is False


def test_compare_valid_files(tmp_path: Path) -> None:
    payload = {
        "agent": "test-model",
        "turns": [{"turn": 0}],
        "scores": {
            "population": 10.0,
            "efficiency": 20.0,
            "stability": 30.0,
            "resilience": 40.0,
            "composite": 25.0,
        },
    }
    (tmp_path / "run1.json").write_text(json.dumps(payload), encoding="utf-8")

    csv_path = compare_results(str(tmp_path))
    assert csv_path.exists()
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["model"] == "test-model"
    assert rows[0]["runs"] == "1"


def test_compare_skips_invalid_and_non_run_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], valid_run_log_payload: dict[str, Any]
) -> None:
    (tmp_path / "valid.json").write_text(json.dumps(valid_run_log_payload), encoding="utf-8")
    (tmp_path / "not_a_run.json").write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    (tmp_path / "broken.json").write_text("{not-json", encoding="utf-8")

    csv_path = compare_results(str(tmp_path))
    assert csv_path.exists()

    captured = capsys.readouterr()
    assert "skip not_a_run.json: not a run log" in captured.err
    assert "skip broken.json: failed to load" in captured.err


def test_compare_results_raises_when_no_valid_run_logs(
    tmp_path: Path, valid_run_log_payload: dict[str, Any]
) -> None:
    payload = dict(valid_run_log_payload)
    payload.pop("scores")
    (tmp_path / "invalid.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="No valid run logs"):
        compare_results(str(tmp_path))


def test_compare_empty_dir(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No JSON result files found"):
        compare_results(str(tmp_path))

