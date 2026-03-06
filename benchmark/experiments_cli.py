from __future__ import annotations

import argparse

from benchmark.aggregate_metrics import aggregate, write_per_run_metrics
from benchmark.experiment_runner import ROOT, run_experiment
from benchmark.inspector import format_failure_report, inspect_failures, timeline
from benchmark.uploader import upload


def _optional_set(values: list[str] | None) -> set[str] | None:
    if not values:
        return None
    return set(values)


def _optional_int_set(values: list[int] | None) -> set[int] | None:
    if not values:
        return None
    return set(values)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Manage CityBench experiments.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run an experiment matrix")
    run_parser.add_argument("--matrix", required=True, help="Path to matrix.yaml")
    run_parser.add_argument("--experiment", required=True, help="Experiment name")
    run_parser.add_argument("--turns", type=int, default=50, help="Turns per run")
    run_parser.add_argument("--model", action="append", help="Filter to one or more models")
    run_parser.add_argument("--seed", action="append", type=int, help="Filter to one or more seeds")
    run_parser.add_argument("--scenario", action="append", help="Filter to one or more scenarios")
    run_parser.add_argument("--resume", action="store_true", help="Skip completed runs in runs/index.csv")

    aggregate_parser = subparsers.add_parser("aggregate", help="Aggregate experiment metrics")
    aggregate_parser.add_argument("--experiment", required=True, help="Experiment name")

    upload_parser = subparsers.add_parser("upload", help="Upload aggregated summaries")
    upload_parser.add_argument("--experiment", required=True, help="Experiment name")
    upload_parser.add_argument("--target", required=True, help="Upload target, e.g. file:///tmp/results")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect failing runs by model and scenario")
    inspect_parser.add_argument("--experiment", required=True, help="Experiment name")
    inspect_parser.add_argument("--model", required=True, help="Model id to inspect")
    inspect_parser.add_argument("--scenario", required=True, help="Scenario id to inspect")

    timeline_parser = subparsers.add_parser("timeline", help="Print compact turn timeline for one run JSON")
    timeline_parser.add_argument("--result", required=True, help="Path to result JSON file")

    args = parser.parse_args(argv)

    if args.command == "run":
        run_experiment(
            args.matrix,
            experiment_name=args.experiment,
            turns=args.turns,
            model_filter=_optional_set(args.model),
            seed_filter=_optional_int_set(args.seed),
            scenario_filter=_optional_set(args.scenario),
            resume=args.resume,
        )
        return

    if args.command == "aggregate":
        metrics_dir = ROOT / "experiments" / args.experiment / "metrics"
        runs_index = ROOT / "experiments" / args.experiment / "runs" / "index.csv"
        per_run = metrics_dir / "per_run_metrics.jsonl"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        write_per_run_metrics(runs_index, per_run, experiment=args.experiment)
        aggregate(per_run, metrics_dir / "summary_by_model.csv", metrics_dir / "summary_overall.json")
        return

    if args.command == "inspect":
        runs_index = ROOT / "experiments" / args.experiment / "runs" / "index.csv"
        records = inspect_failures(runs_index, model=args.model, scenario=args.scenario)
        print(format_failure_report(records))
        return

    if args.command == "timeline":
        print(timeline(args.result))
        return

    metrics_dir = ROOT / "experiments" / args.experiment / "metrics"
    upload(args.experiment, metrics_dir, args.target)


if __name__ == "__main__":
    main()

