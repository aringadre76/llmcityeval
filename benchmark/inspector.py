from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from benchmark.metrics import load_result


def _count_rejected_actions(turn: dict[str, Any]) -> int:
    outcomes = turn.get("action_outcomes")
    if outcomes is None:
        outcomes = (turn.get("state") or {}).get("last_action_outcomes", [])
    return sum(1 for outcome in outcomes or [] if not bool(outcome.get("applied", False)))


def _has_repeated_insufficient_budget(turns: list[dict[str, Any]], threshold: float) -> bool:
    if not turns:
        return False
    flagged_turns = 0
    for turn in turns:
        outcomes = turn.get("action_outcomes")
        if outcomes is None:
            outcomes = (turn.get("state") or {}).get("last_action_outcomes", [])
        if any(outcome.get("reason") == "insufficient_budget" for outcome in outcomes or []):
            flagged_turns += 1
    return (flagged_turns / len(turns)) >= threshold


def _has_persistent_bankruptcy(turns: list[dict[str, Any]], lookback_turns: int = 3) -> bool:
    if not turns:
        return False
    recent = turns[-lookback_turns:]
    if len(recent) < lookback_turns:
        return False
    return all(float((turn.get("state") or {}).get("budget", 0.0)) < 0 for turn in recent)


def _short_turn_summary(turn: dict[str, Any]) -> dict[str, Any]:
    state = turn.get("state", {})
    return {
        "turn": int(turn.get("turn", 0)),
        "population": int(state.get("population", 0)),
        "budget": float(state.get("budget", 0.0)),
        "events": [str(event.get("event", "unknown")) for event in (turn.get("disaster_events") or [])],
        "rejected_actions": int(_count_rejected_actions(turn)),
    }


def inspect_failures(
    runs_index_path: str | Path,
    model: str,
    scenario: str,
    *,
    insufficient_budget_threshold: float = 0.5,
    tail_turns: int = 3,
) -> list[dict[str, Any]]:
    runs_index_path = Path(runs_index_path)
    records: list[dict[str, Any]] = []
    with runs_index_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("model") != model or row.get("scenario") != scenario:
                continue
            result_path = row.get("result_path")
            if not result_path:
                continue
            run_data = load_result(result_path)
            turns = run_data.get("turns", []) or []
            final_state = run_data.get("final_state") or {}
            scores = run_data.get("scores") or {}

            failure_flags: list[str] = []
            final_population = int(final_state.get("population", 0))
            final_budget = float(final_state.get("budget", 0.0))

            if final_population == 0:
                failure_flags.append("final_population_zero")
            if _has_repeated_insufficient_budget(turns, insufficient_budget_threshold):
                failure_flags.append("repeated_insufficient_budget")
            if _has_persistent_bankruptcy(turns):
                failure_flags.append("persistent_bankruptcy")
            if final_budget < 0:
                failure_flags.append("bankrupt_final_state")

            if not failure_flags:
                continue

            records.append(
                {
                    "run_id": row.get("run_id", ""),
                    "seed": int(row.get("seed", 0)),
                    "model": model,
                    "scenario": scenario,
                    "result_path": str(result_path),
                    "final_population": final_population,
                    "final_budget": final_budget,
                    "final_composite_score": float(scores.get("composite", 0.0)),
                    "failure_flags": failure_flags,
                    "tail_turns": [_short_turn_summary(turn) for turn in turns[-tail_turns:]],
                }
            )
    return sorted(records, key=lambda record: record["seed"])


def format_failure_report(records: list[dict[str, Any]]) -> str:
    if not records:
        return "No failing runs found."

    lines: list[str] = []
    for record in records:
        flags = ",".join(record["failure_flags"])
        lines.append(
            "seed="
            f"{record['seed']} pop={record['final_population']} budget={record['final_budget']:.1f} "
            f"score={record['final_composite_score']:.2f} flags=[{flags}]"
        )
        for turn in record["tail_turns"]:
            events = ",".join(turn["events"]) if turn["events"] else "-"
            lines.append(
                "  "
                f"turn={turn['turn']} pop={turn['population']} budget={turn['budget']:.1f} "
                f"events={events} rejected={turn['rejected_actions']}"
            )
    return "\n".join(lines)


def timeline(result_path: str | Path) -> str:
    run_data = load_result(result_path)
    turns = run_data.get("turns", []) or []

    lines = ["turn | pop | budget | rev | exp | poll | disasters | rejected"]
    for turn in turns:
        state = turn.get("state") or {}
        disasters = [str(event.get("event", "unknown")) for event in (turn.get("disaster_events") or [])]
        lines.append(
            f"{int(turn.get('turn', 0))} | "
            f"{int(state.get('population', 0))} | "
            f"{float(state.get('budget', 0.0)):.1f} | "
            f"{float(state.get('revenue_per_tick', 0.0)):.1f} | "
            f"{float(state.get('expenses_per_tick', 0.0)):.1f} | "
            f"{float(state.get('pollution_avg', 0.0)):.3f} | "
            f"{','.join(disasters) if disasters else '-'} | "
            f"{_count_rejected_actions(turn)}"
        )
    return "\n".join(lines)
