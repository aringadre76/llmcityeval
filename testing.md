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

## Current / example results

Runs performed with **llama3:8b** (Ollama):

| Run | Seed | Turns | Final population (raw) | Population score | Composite | Notes |
|-----|------|-------|-------------------------|------------------|-----------|--------|
| Smoke | 42 | 5 | 0 | 0–25 | 0–25 | Parse success may vary; no time for growth. |
| Full | 42 | 50 | 249 | 6.22 | 26.56 | Revenue from ~turn 18; 21 actions rejected (insufficient_budget). |

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
- **No unit tests yet:** The repo does not include `pytest` or `test_*.py` files. To add automated tests, you could add a `tests/` directory and run `pytest` for sim logic, scoring, and agent parsing.

---

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| `Connection refused` / request errors | Ollama is running (`ollama serve` or start the app) and nothing else is bound to port 11434. |
| `model not found` | Run `ollama pull <model>` for the model name you pass to `--model`. |
| `Provide --seed or --seeds, or use --compare` | You must pass at least one of `--seed`, `--seeds`, or `--compare`. |
| Empty or zero scores | Normal for very short runs (`--turns 5`) or if the model returns invalid JSON; try `--turns 50` and check logs for parse errors. |
