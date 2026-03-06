from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmark import scorer


def load_result(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw)


def _count_hard_violations(run_data: dict[str, Any]) -> int:
    """Count non-applied action outcomes across all turns."""
    count = 0
    for turn in run_data.get("turns", []):
        outcomes = turn.get("action_outcomes") or turn.get("state", {}).get("last_action_outcomes") or []
        for o in outcomes:
            if not bool(o.get("applied", False)):
                count += 1
    return count


def _compute_avg_recovery_turns(run_data: dict[str, Any]) -> float:
    """Estimate recovery time after disasters by scanning populations around disaster turns."""
    populations: list[float] = []
    turns = run_data.get("turns", []) or []
    for t in turns:
        state = t.get("state") or {}
        populations.append(float(state.get("population", 0.0)))

    event_indices: list[int] = []
    for t in turns:
        if t.get("disaster_events"):
            event_indices.append(int(t.get("turn", 0)))

    if not event_indices:
        return 0.0

    n = len(populations)
    recovery_spans: list[int] = []
    for idx in event_indices:
        pre = populations[idx] if idx < n else populations[-1] if populations else 0.0
        # find next turn where population >= pre (simple recovery heuristic)
        rec_turn = None
        for j in range(idx + 1, n):
            if populations[j] >= pre:
                rec_turn = j
                break
        if rec_turn is None:
            rec_turn = n - 1
        recovery_spans.append(max(0, rec_turn - idx))

    if not recovery_spans:
        return 0.0
    return sum(recovery_spans) / len(recovery_spans)


def extract_per_run_metrics(
    result_path: str | Path,
    experiment: str = "citybench_v1",
    scenario: str = "default",
    run_id: str | None = None,
) -> dict[str, Any]:
    run_data = load_result(result_path)

    agent = str(run_data.get("agent", "unknown"))
    seed = int(run_data.get("seed", 0))
    filename = Path(result_path).stem
    metric_run_id = run_id or f"{experiment}_{filename}"

    # Use existing scorer for canonical population/efficiency/stability/resilience/composite metrics.
    try:
        computed_scores = scorer.score_run(run_data)
    except Exception:
        computed_scores = dict(run_data.get("scores", {}))

    metrics: dict[str, Any] = {
        "final_score": float(computed_scores.get("composite", 0.0)),
        "population_score": float(computed_scores.get("population", 0.0)),
        "efficiency_score": float(computed_scores.get("efficiency", 0.0)),
        "stability_score": float(computed_scores.get("stability", 0.0)),
        "resilience_score": float(computed_scores.get("resilience", 0.0)),
        "hard_constraint_violations": int(_count_hard_violations(run_data)),
        "num_disasters": int(sum(len(t.get("disaster_events", [])) for t in run_data.get("turns", []))),
        "avg_recovery_turns": float(_compute_avg_recovery_turns(run_data)),
    }

    return {
        "run_id": metric_run_id,
        "experiment": experiment,
        "model": agent,
        "seed": seed,
        "scenario": scenario,
        "metrics": metrics,
        "meta": {
            "source_path": str(result_path),
        },
    }

