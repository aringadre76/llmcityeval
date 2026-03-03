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
| **Packaging** | Done | `requirements.txt` (requests), package `__init__.py`s, README. |

### Verification

- `python3 -m compileall` passes.
- Smoke run with dummy agent (5 turns) completes and produces scores.
- No in-code `TODO`/`FIXME` markers at last check.

### Benchmark runs (llama3:8b)

| Run | Command | Result |
|-----|--------|--------|
| Smoke | `python3 run.py --seed 42 --turns 5` | Completes; pop/composite low (0–25) as expected for 5 turns. Parse success can vary run-to-run. |
| Full 50-turn | `python3 run.py --seed 42 --verbose` | Completes; model builds roads + zones, revenue and population appear by ~turn 18; final pop 249, composite 26.56, population score 6.22. |

**Findings:** All 50 turns had valid JSON (`action_parse_success: true`). Some actions rejected for `insufficient_budget` (21 in one run) when the model proposed more spend than available. No `out_of_bounds` / `invalid_zone` / `exceeded_max_actions` in that run. See [testing.md](testing.md) for details.

### Code issues identified

| Issue | Location | Severity |
|-------|----------|----------|
| Placing road on a disabled road tile does not set `disabled = False`; only the disaster expiry re-enables it. | `sim/grid.py` `set_zone()` | Bug or intentional (can't "rebuild" out of infra failure). |
| `--compare` includes every `*.json` in the directory; non-run files can cause crashes or garbage rows. | `run.py` `compare_results()` | Robustness. |
| Scorer assumes every turn has `state.population`; malformed logs can raise `KeyError`. | `benchmark/scorer.py` `_population_series()` | Robustness. |
| Action failure reasons (e.g. `insufficient_budget`) are not included in the next prompt; model infers from state only. | Runner / prompt | Design limitation. |

---

## TODO

*Add items below when something is pending; remove or move to Changelog when finished.*

- *(none)* — Plan is fully implemented; no remaining items from the MVP implementation plan.

---

## Changelog

- **Benchmark testing:** Ran smoke (5-turn) and full 50-turn runs with llama3:8b; documented results in testing.md; reviewed code and documented four issues (grid disabled road, compare robustness, scorer robustness, action outcomes not in prompt).
- **Initial:** MVP implementation completed; all plan phases and todos done. Progress doc added.
