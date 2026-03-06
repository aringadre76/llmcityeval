# CityBench MVP

CityBench is a city-building benchmark where an LLM acts as an urban planner.  
Each turn, the model receives structured city state JSON and returns zoning actions.  
The simulator advances deterministically (given a seed), logs every turn, and computes final scores.

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

Upload summaries to a central filesystem location:

```bash
python -m benchmark.experiments_cli upload \
  --experiment citybench_v1 \
  --target file:///tmp/citybench-results
```

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
