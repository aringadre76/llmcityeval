# Testing the Project

This document describes how to run and test the CityBench MVP benchmark.

## Prerequisites

1. **Python 3** with dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

2. **Ollama** running locally. The benchmark talks to `http://localhost:11434/api/generate`.
   - Install from [ollama.ai](https://ollama.ai) and start the server.
   - Pull a model (default is `llama3:8b`):
     ```bash
     ollama pull llama3:8b
     ```
   - You can use any other model by passing `--model <name>` to the runner.

---

## Quick smoke test (short run)

Run a single seed with fewer turns to verify the pipeline without waiting for a full run:

```bash
python3 run.py --seed 42 --turns 5
```

You should see one line of output per run, e.g.:

```
Completed model=llama3:8b seed=42 pop=0.00 composite=0.00
```

Results are written to the `results/` directory as JSON files (e.g. `llama3_8b_42_20250302T120000Z.json`).

---

## Experiment workflow

CityBench now has a lightweight experiment runner that supports scenario-specific runtime overrides without editing `config.py`.

**Run the full experiment matrix:**

```bash
python -m benchmark.experiments_cli run \
  --matrix experiments/citybench_v1/config/matrix.yaml \
  --experiment citybench_v1
```

**Run a filtered subset and skip completed runs:**

```bash
python -m benchmark.experiments_cli run \
  --matrix experiments/citybench_v1/config/matrix.yaml \
  --experiment citybench_v1 \
  --model llama3:8b \
  --seed 42 \
  --scenario disasters_heavy \
  --resume
```

**Aggregate normalized per-run metrics and summaries:**

```bash
python -m benchmark.experiments_cli aggregate --experiment citybench_v1
```

**Upload summaries to a shared filesystem location:**

```bash
python -m benchmark.experiments_cli upload \
  --experiment citybench_v1 \
  --target file:///tmp/citybench-results
```

Scenario overrides are read from `experiments/citybench_v1/config/matrix.yaml`. Supported keys are:

- `starting_budget`
- `starting_population`
- `disaster_frequency_multiplier`
- `disaster_severity_multiplier`

Generated experiment artifacts:

- `experiments/<name>/runs/index.csv`
- `experiments/<name>/metrics/per_run_metrics.jsonl`
- `experiments/<name>/metrics/summary_by_model.csv`
- `experiments/<name>/metrics/summary_overall.json`

---

## Current / example results

Runs performed with **llama3:8b** (Ollama):

| Run | Seed(s) | Turns | Final population (raw) | Population score | Composite | Notes |
|-----|---------|-------|-------------------------|------------------|-----------|--------|
| Smoke | 42 | 5 | 0 | 0–25 | 0–25 | Parse success may vary; no time for growth. |
| Full | 42 | 50 | 249 | 6.22 | 26.56 | Revenue from ~turn 18; 21 actions rejected (insufficient_budget). |
| Multi-seed (full) | 42,123,456 | 50 | - | 0.59 ± 0.42 | 33.69 ± 6.32 | Aggregated over three runs; seeds 42 and 123 grew small cities, seed 456 never grew population (no connected residential); see `results/comparison_summary.csv`. |
| Multi-seed (medium) | 42,43,44,45,46 | 30 | - | ≈0.0–1.8 (per-run) | ≈17–35 (per-run) | `python3 run.py --model llama3:8b --seeds 42,43,44,45,46 --turns 30`; all seeds completed without runtime errors via local Ollama, exercising longer horizons and multiple seeds. |

**In the 50-turn run:** All turns had `action_parse_success: true`. Rejections were only `insufficient_budget` (model proposed more spend than available in a single turn). No parse failures, no `out_of_bounds` or `invalid_zone`. See result JSONs in `results/` for per-turn `actions`, `action_outcomes`, and `state`.

---

## Full benchmark run

Run one or more seeds with the default 50 turns:

**Single seed:**
```bash
python3 run.py --seed 42
```

**Multiple seeds (comma-separated):**
```bash
python3 run.py --seeds 1,2,3
```

**Different model:**
```bash
python3 run.py --model llama3.2:3b --seed 42
```

**Verbose mode** (print per-turn state: population, budget, revenue, expenses, livability, pollution):
```bash
python3 run.py --seed 42 --verbose
```

---

## Comparing results

After running multiple models or seeds, aggregate and compare scores:

```bash
python3 run.py --compare results/
```

This prints a table of mean ± std for population, efficiency, stability, resilience, and composite scores, and writes `results/comparison_summary.csv`.

---

## What gets tested

- **End-to-end:** The runner loads the sim, creates an `OllamaAgent`, runs the turn loop, scores the run, and saves a log. A successful short run confirms the stack works (Ollama, prompts, sim, scorer, logger).
- **Current results:** See "Current / example results" above; full details and code issues are in [PROGRESS.md](PROGRESS.md).
- **Automated tests:** Run the full suite with:
  ```bash
  pytest tests
  ```
- **Current automated coverage:** `tests/` now covers grid/scorer behavior, prompt feedback formatting, runtime scenario config injection, scenario override application, resumable and filtered experiment execution, experiment CLI/upload behavior, per-run metric extraction, aggregation summaries, baseline agents, and experiment runner behavior.
- **Latest full suite result:** `pytest tests` passed with `56 passed` at last check.

---

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| `Connection refused` / request errors | Ollama is running (`ollama serve` or start the app) and nothing else is bound to port 11434. |
| `model not found` | Run `ollama pull <model>` for the model name you pass to `--model`. |
| `Provide --seed or --seeds, or use --compare` | You must pass at least one of `--seed`, `--seeds`, or `--compare`. |
| Empty or zero scores | Normal for very short runs (`--turns 5`) or if the model returns invalid JSON; try `--turns 50` and check logs for parse errors. |
