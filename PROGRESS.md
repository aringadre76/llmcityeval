# CityBench MVP — Progress

*Update this file whenever there are new TODOs or completed work.*

---

## Current status

**MVP plan:** Implemented end-to-end per the [MVP spec](MVP.md) and [implementation plan](.cursor/plans/citybench_mvp_implementation_351b2ae4.plan.md).

### Done

| Area | Status | Notes |
|------|--------|--------|
| **Foundation** | Done | `config.py` with all constants; `sim/grid.py` (TileState, Grid, connectivity, neighbors); `sim/mechanics.py` (revenue, expenses, livability, population, pollution); `sim/disasters.py` (DisasterManager, 4 disaster types, seeded RNG). |
| **Simulation** | Done | `sim/city.py`: CityState, Action, City with `apply_actions()` and canonical tick pipeline, metrics_delta. |
| **Agents** | Done | `agents/base.py` (BaseAgent); `agents/ollama.py` (OllamaAgent, JSON extraction, timeout/error handling). |
| **Prompts** | Done | `prompts/system.txt` per spec. |
| **Benchmark** | Done | `benchmark/logger.py` (RunLog, JSON save); `benchmark/scorer.py` (population, efficiency, stability, resilience, composite); `benchmark/runner.py` (run loop, scoring, save). |
| **CLI** | Done | `run.py`: `--model`, `--seed`, `--seeds`, `--turns`, `--verbose`, `--compare` with ASCII table + CSV. |
| **Experiments** | Done | `sim/runtime_config.py` for runtime scenario overrides; `benchmark/experiment_runner.py` applies `config_overrides` per scenario and supports `agent_type` dispatch (`ollama`, `random`, `heuristic`); `benchmark/experiments_cli.py` supports filtered runs, resume, aggregation, uploads, failure inspection, and timelines. |
| **Packaging** | Done | `requirements.txt` (`requests`, `pytest`), package `__init__.py`s, README. |

### Verification

- `python3 -m compileall` passes.
- `pytest tests` passes (`56 passed` at last full run).
- `ruff check .` passes with minimal enforced rules (`E`, `F`, `W`).
- Smoke run with dummy agent (5 turns) completes and produces scores.
- Multi-seed smoke/medium runs with `llama3:8b` complete without errors (see below).
- No in-code `TODO`/`FIXME` markers at last check.

### Benchmark runs (llama3:8b)

| Run | Command | Result |
|-----|--------|--------|
| Smoke | `python3 run.py --seed 42 --turns 5` | Completes; pop/composite low (0–25) as expected for 5 turns. Parse success can vary run-to-run. |
| Full 50-turn | `python3 run.py --seed 42 --verbose` | Completes; model builds roads + zones, revenue and population appear by ~turn 18; final pop 249, composite 26.56, population score 6.22. |
| Medium multi-seed | `python3 run.py --model llama3:8b --seeds 42,43,44,45,46 --turns 30` | All five runs complete via local Ollama; normalized population ranges from ≈0.00–1.80 with composites between ≈17–35, confirming stability over longer horizons and multiple seeds. |

**Findings:** All 50 turns had valid JSON (`action_parse_success: true`). Some actions rejected for `insufficient_budget` (21 in one run) when the model proposed more spend than available. No `out_of_bounds` / `invalid_zone` / `exceeded_max_actions` in that run. See [testing.md](testing.md) for details.

**Multi-seed run:** `python3 run.py --seeds 42,123,456` produced two runs with small but functioning cities (population scores ≈0.9 and composite ≈36–40) and one failure case (seed 456: composite 25.0 with zero population due to never having any connected residential tiles). `python3 run.py --compare results/` summarizes these in `results/comparison_summary.csv`.

### Code issues identified

| Issue | Location | Status |
|-------|----------|--------|
| Rebuilding a disabled road should not be free (same-zone action previously cost 0). | `sim/city.py` `apply_actions()` | Resolved: rebuilding disabled same-zone tiles now charges normal build cost and clears `disabled`; covered by regression tests. |
| `--compare` includes every `*.json` in the directory; non-run files can cause crashes or garbage rows. | `run.py` `compare_results()` | Resolved in current code; covered by regression tests. |
| Scorer assumes every turn has `state.population`; malformed logs can raise `KeyError`. | `benchmark/scorer.py` `_population_series()` | Resolved in current code; covered by regression tests. |
| Action failure reasons (e.g. `insufficient_budget`) are not included in the next prompt; model infers from state only. | Runner / prompt | Resolved in current code; covered by regression tests. |
| Experiment scenarios required manual config edits and could not safely vary disaster/economy settings per run. | Experiments / config flow | Resolved: added `SimConfig` runtime injection and per-scenario `config_overrides` handling in the experiment runner. |
| Experiment runs could not be filtered/resumed, and aggregated summaries had no simple upload path. | Experiment tooling | Resolved: added `benchmark.experiments_cli` with subset filters, resume support, aggregation, and `file://` uploads. |
| Aggregated experiment output lost scenario information and did not record the best model per scenario. | `benchmark/metrics.py`, `benchmark/aggregate_metrics.py` | Resolved: scenario now propagates from `runs/index.csv` into `per_run_metrics.jsonl`; `summary_overall.json` now includes `best_model_by_final_score`. |

### Post-MVP priorities

1. Expand benchmark evaluation coverage across more seeds and more models.
2. Expand baseline agent policies (for example, budget-aware or connectivity-aware heuristics) for stronger non-LLM references.
3. Decide and standardize the production upload target contract for HTTPS/S3 (auth, payload shape, retries).
4. Continue hardening with additional negative-path and malformed-input tests.
5. Optionally wire `metrics.yaml` into runtime aggregation (currently static aggregation code).

---

## TODO

*Add items below when something is pending; remove or move to Changelog when finished.*

- *(none)* — Plan is fully implemented; no remaining items from the MVP implementation plan.

---


## Changelog

- **Experiment enhancements:** Added runtime scenario configuration via `sim/runtime_config.py`; threaded it through `sim/city.py`, `sim/disasters.py`, and `benchmark/runner.py`; taught `benchmark/experiment_runner.py` to apply `config_overrides` from `experiments/citybench_v1/config/matrix.yaml`; added `benchmark/experiments_cli.py` for filtered runs, resume, aggregate, and upload; added `benchmark/uploader.py` with `file://` support; documented the workflow in `README.md`.
- **CityBench enhancements:** Added deep-dive diagnostics via `benchmark/inspector.py` and new CLI commands (`inspect`, `timeline`); added baseline agents (`agents/random_agent.py`, `agents/heuristic_agent.py`) and wired `agent_type` dispatch into `benchmark/experiment_runner.py`; extended uploader targets to `s3://` and `https://`; added stress/determinism tests in `tests/test_stress.py`; added CI quality gates in `.github/workflows/ci.yml` with compile, pytest, and ruff checks; added `ruff.toml` and dependency updates in `requirements.txt`.
- **Experiment test coverage:** Added tests for runtime config injection, scenario override application, resumable/filtered experiment execution, CLI/upload behavior, per-run metric extraction, and aggregation summaries. Full suite passes with `pytest tests` (`56 passed` at last full run).
- **Hardening + evaluation prep:** Added `pytest` and a full `tests/` suite covering regression cases (disabled-road rebuild cost behavior, robust `--compare` filtering, scorer handling of malformed logs, and rejected-action feedback in prompts) plus unit coverage for grid, mechanics, disasters, city turn logic, agent JSON parsing, baseline agents, and experiment tooling.
- **Benchmark testing:** Ran smoke (5-turn), full 50-turn, and multi-seed runs with `llama3:8b`; most recent medium multi-seed run (`--seeds 42,43,44,45,46 --turns 30`) completed with composites spanning ≈17–35 and no runtime errors. Results and commands are documented in `testing.md`.
- **Initial:** MVP implementation completed; all plan phases and todos done. Progress doc added.
