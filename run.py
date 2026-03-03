from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from statistics import mean, pstdev

from agents.ollama import OllamaAgent
from benchmark.runner import run
from config import DEFAULT_MODEL, TURNS


def _parse_seed_list(value: str) -> list[int]:
    seeds: list[int] = []
    for chunk in value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        seeds.append(int(chunk))
    return seeds


def _format_mean_std(values: list[float]) -> tuple[str, float, float]:
    avg = mean(values)
    std = pstdev(values) if len(values) > 1 else 0.0
    if len(values) == 1:
        return f"{avg:.2f} (single-run)", avg, std
    return f"{avg:.2f} +/- {std:.2f}", avg, std


def _is_run_log(payload: object) -> bool:
    """Return True if payload looks like a run log (dict with scores and turns)."""
    if not isinstance(payload, dict):
        return False
    scores = payload.get("scores")
    turns = payload.get("turns")
    return (
        isinstance(scores, dict)
        and turns is not None
    )


def compare_results(results_dir: str) -> Path:
    directory = Path(results_dir)
    files = sorted(directory.glob("*.json"))
    if not files:
        raise ValueError(f"No JSON result files found in {results_dir}.")

    by_model: dict[str, dict[str, list[float]]] = {}
    for file_path in files:
        try:
            raw = file_path.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Warning: skip {file_path.name}: failed to load ({e})", file=sys.stderr)
            continue
        if not _is_run_log(payload):
            print(f"Warning: skip {file_path.name}: not a run log (missing 'scores' dict or 'turns')", file=sys.stderr)
            continue
        model = str(payload.get("agent", "unknown"))
        scores = payload.get("scores", {})
        model_scores = by_model.setdefault(
            model,
            {
                "population": [],
                "efficiency": [],
                "stability": [],
                "resilience": [],
                "composite": [],
            },
        )
        for key in model_scores.keys():
            model_scores[key].append(float(scores.get(key, 0.0)))

    if not by_model:
        raise ValueError(
            f"No valid run logs in {results_dir}. "
            "Run logs must be JSON objects with 'scores' (dict) and 'turns'."
        )

    headers = ["model", "population", "efficiency", "stability", "resilience", "composite", "runs"]
    rows: list[list[str]] = []
    csv_rows: list[dict[str, str | float | int]] = []
    for model, scores in sorted(by_model.items()):
        row = [model]
        numeric_means: dict[str, float] = {}
        numeric_stds: dict[str, float] = {}
        for key in ("population", "efficiency", "stability", "resilience", "composite"):
            summary, avg, std = _format_mean_std(scores[key])
            numeric_means[key] = avg
            numeric_stds[key] = std
            row.append(summary)
        run_count = len(scores["composite"])
        row.append(str(run_count))
        rows.append(row)

        csv_row: dict[str, str | float | int] = {"model": model, "runs": run_count}
        for key in ("population", "efficiency", "stability", "resilience", "composite"):
            csv_row[f"{key}_mean"] = numeric_means[key]
            csv_row[f"{key}_std"] = numeric_stds[key]
        csv_rows.append(csv_row)

    widths = [len(header) for header in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(values: list[str]) -> str:
        return " | ".join(val.ljust(widths[i]) for i, val in enumerate(values))

    separator = "-+-".join("-" * w for w in widths)
    print(fmt_row(headers))
    print(separator)
    for row in rows:
        print(fmt_row(row))

    csv_path = directory / "comparison_summary.csv"
    csv_headers = [
        "model",
        "runs",
        "population_mean",
        "population_std",
        "efficiency_mean",
        "efficiency_std",
        "stability_mean",
        "stability_std",
        "resilience_mean",
        "resilience_std",
        "composite_mean",
        "composite_std",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(csv_rows)
    return csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CityBench MVP benchmark.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--seed", type=int, help="Single run seed")
    parser.add_argument("--seeds", type=str, help="Comma-separated seeds")
    parser.add_argument("--turns", type=int, default=TURNS, help="Number of turns")
    parser.add_argument("--verbose", action="store_true", help="Print per-turn state summary")
    parser.add_argument("--compare", type=str, help="Compare all result files in directory")
    args = parser.parse_args()

    if args.compare:
        csv_path = compare_results(args.compare)
        print(f"Saved CSV summary to {csv_path}")
        return

    seeds: list[int] = []
    if args.seed is not None:
        seeds.append(args.seed)
    if args.seeds:
        seeds.extend(_parse_seed_list(args.seeds))
    if not seeds:
        parser.error("Provide --seed or --seeds, or use --compare.")

    for seed in seeds:
        agent = OllamaAgent(model=args.model)
        log = run(agent=agent, seed=seed, turns=args.turns, verbose=args.verbose)
        print(
            f"Completed model={args.model} seed={seed} "
            f"pop={log.scores.get('population', 0.0):.2f} "
            f"composite={log.scores.get('composite', 0.0):.2f}"
        )


if __name__ == "__main__":
    main()
