# CityBench MVP

CityBench is a city-building benchmark where an LLM acts as an urban planner.  
Each turn, the model receives structured city state JSON and returns zoning actions.  
The simulator advances deterministically (given a seed), logs every turn, and computes final scores.

## Current evaluation takeaways

Current benchmark results for `llama3:8b` show a clear split between reliability and planning quality:

- It is a strong constrained decision engine: outputs stayed valid, schema adherence was reliable, and executed runs completed without HTTP/JSON failures or simulator crashes.
- It makes locally sensible, grid-aware moves, but long-horizon planning is weak. Over 30-50 turns, scores tend to cluster in a middling range rather than consistently producing strong cities.
- Performance is sensitive to seed, which suggests a brittle policy that reacts myopically to early conditions instead of following a robust global strategy.
- It respects rules better than it optimizes for long-term growth: the common failure mode is not illegal actions, but mediocre city development.

Practical takeaway: `llama3:8b` is useful for testing protocol adherence and benchmarking constrained decision-making, but it is not yet a high-quality autonomous urban planner in CityBench. A stronger planner will likely require a better model, richer scaffolding such as planning/search loops, or a hybrid LLM-plus-heuristic approach.

These conclusions apply to `llama3:8b` under the current CityBench settings. Supporting notes and run history are documented in `MODEL_EVALUATION_CONCLUSIONS.md`, `PROGRESS.md`, and `testing.md`.

## Requirements

- Python 3.10+
- Local Ollama instance at `http://localhost:11434`
- Dependency: `requests`

Install:

```bash
pip install -r requirements.txt
```

## Run benchmark

Single seed:

```bash
python run.py --model llama3:8b --seed 42 --turns 50
```

Multiple seeds:

```bash
python run.py --model llama3:8b --seeds 42,43,44,45,46 --turns 50
```

Verbose per-turn output:

```bash
python run.py --model llama3:8b --seed 42 --verbose
```

## Compare existing results

```bash
python run.py --compare results/
```

This prints an ASCII table and writes `results/comparison_summary.csv`.

## Project layout

- `sim/`: simulation state, mechanics, grid, disasters
- `agents/`: base agent interface and Ollama-backed agent
- `benchmark/`: run loop, scoring, and logging
- `prompts/system.txt`: system prompt passed to the model
- `config.py`: all tunable constants
- `results/`: generated per-run JSON logs
## Experiments & metrics

We provide a lightweight experiments layout to run reproducible multi-model, multi-seed evaluations and to aggregate results.

Run definitions are stored under `experiments/<name>/config/`. The canonical example is:

- `experiments/citybench_v1/config/matrix.yaml` — experiment matrix (models, seeds, scenarios).
- `experiments/citybench_v1/config/metrics.yaml` — which metrics to compute and how to aggregate them.

Scenario `config_overrides` are applied at runtime through a `SimConfig` object. They do not edit `config.py`. Supported override keys are:

- `starting_budget`
- `starting_population`
- `disaster_frequency_multiplier`
- `disaster_severity_multiplier`

The recommended workflow uses the experiments CLI.

Run the full matrix:

```bash
python -m benchmark.experiments_cli run \
  --matrix experiments/citybench_v1/config/matrix.yaml \
  --experiment citybench_v1
```

Run a filtered subset and resume previously completed work:

```bash
python -m benchmark.experiments_cli run \
  --matrix experiments/citybench_v1/config/matrix.yaml \
  --experiment citybench_v1 \
  --model llama3:8b \
  --seed 42 \
  --scenario disasters_heavy \
  --resume
```

Aggregate per-run metrics into summaries:

```bash
python -m benchmark.experiments_cli aggregate --experiment citybench_v1
```

Inspect recurring failures for a specific model/scenario:

```bash
python -m benchmark.experiments_cli inspect \
  --experiment citybench_v1 \
  --model llama3:8b \
  --scenario default
```

Print a compact timeline for a single run JSON:

```bash
python -m benchmark.experiments_cli timeline --result results/llama3_8b_42_*.json
```

Upload summaries to a central filesystem location:

```bash
python -m benchmark.experiments_cli upload \
  --experiment citybench_v1 \
  --target file:///tmp/citybench-results
```

Additional upload targets:

- `s3://<bucket>/<prefix>` (uploads summary files with boto3)
- `https://<host>/<path>` (multipart POST to `<target>/<experiment>/`)

Output files:
- `experiments/citybench_v1/runs/index.csv` — mapping of logical runs to result JSON paths.
- `experiments/citybench_v1/metrics/per_run_metrics.jsonl` — one JSON object per run with normalized metrics.
- `experiments/citybench_v1/metrics/summary_by_model.csv` — aggregated table by (model, scenario).
- `experiments/citybench_v1/metrics/summary_overall.json` — machine-readable summary including the best model per scenario.

Interpretation notes:

- `per_run_metrics.jsonl` keeps one normalized metric record per run and preserves the scenario from `runs/index.csv`.
- `summary_by_model.csv` is the easiest human-readable comparison table.
- `summary_overall.json` is the best file to consume programmatically or upload to another system.

See `experiments/citybench_v1/config/*.yaml` for an example matrix and selected metrics.

## Baseline agents

In addition to Ollama-backed models, the benchmark includes non-LLM baselines:

- `random_baseline` (`agent_type: random`) — random bounded zoning actions.
- `heuristic_baseline` (`agent_type: heuristic`) — fixed phased pattern (road spine, stripes, industrial edge, road-adjacent fill).

These are included in the default experiment matrix and show up in `summary_by_model.csv` and `summary_overall.json` like any other model.

## Quality gates

Project CI now enforces:

- `python -m compileall . -q`
- `pytest tests -v`
- `ruff check .`
