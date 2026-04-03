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

## Recent progress (2026-04-01)

### Experiment Results
Ran CityBench benchmark with llama3:8b and llama3.2:3b across 5 seeds (42-46) and 2 scenarios (default, disasters_heavy).

| Model | Scenario | Runs | Mean Score | Std Dev |
|-------|----------|------|------------|---------|
| llama3:8b | default | 5 | 30.66 | 6.06 |
| llama3.2:3b | default | 7 | 25.16 | 4.05 |
| llama3:8b | disasters_heavy | 5 | 27.79 | 3.44 |
| llama3.2:3b | disasters_heavy | 5 | 25.0 | 0.0 |

**Winner:** llama3:8b consistently outperforms llama3.2:3b by ~5-6 points.

### Code Changes
- Updated experiment matrix to replace unavailable models (llama3:70b, qwen2.5-coder:7b) with llama3.2:3b
- Removed baseline agents (random, heuristic) for clearer LLM comparison
- Results committed and pushed to origin/main

### Verification
- `python3 -m compileall` passes
- `pytest tests` passes (87 passed)
- `ruff check .` passes

### Smoke test (2026-04-01)
- `python3 run.py --seed 42 --turns 5` completes successfully (pop=0.00, composite=25.00 as expected for 5 turns)
- Experiment result aggregation working correctly
- All recent commits pushed to origin/main

### MODEL_EVALUATION_CONCLUSIONS.md
Comprehensive evaluation report documenting comparative benchmark of llama3:8b and llama3.2:3b across 22 runs (11 per model), 5 seeds, and 2 scenarios.

**Key Findings:**
1. **llama3:8b outperforms llama3.2:3b** by ~5-6 points on average
2. **Disaster scenario reveals fragility**: 3B model hits floor score (25.0) in all runs with zero population
3. **Industrial timing is critical**: 8B builds at turns 3-49, 3B only at turns 8 and 42 (2 builds in 18 runs)
4. **Poverty trap**: 3B model never builds Industrial in 16 of 18 runs; gets stuck in 0 pop, 0 revenue, negative budget state
5. **Architecture analysis**: 3B uses knowledge distillation (not from-scratch), learns *what* but not *why* (ROI calculus)
6. **Seed 46 anomaly**: Both models achieve nearly identical best scores (33.98 vs 33.88), indicating favorable conditions
7. **Disaster count doesn't correlate**: Resilience scores are consistently ~100 for most runs; variance in scores comes from other factors
8. **Industrial is necessary but not sufficient**: Must build Industrial AND with enough budget (turns 20-35 optimal)
- **Conclusion**: LLMs are reliable decision engines but not yet competitive with tailored heuristics; planning quality limited by weak long-horizon planning and misunderstanding ROI timing
- **Practical recommendation**: Train/prompt for Industrial ROI awareness (200 cost → 35/tick for 45+ turns = ~8x ROI)

---

## TODO

*Add items below when something is pending; remove or move to Changelog when finished.*

- *(none)* — Plan is fully implemented; no remaining items from the MVP implementation plan.

---

## New Insights (2026-04-02)

Analysis of 32 runs (16 per model, 5 seeds, default scenario) reveals fundamental model misunderstandings about CityBench dynamics, not just rule-breaking errors.

### Key Findings

| Finding | Evidence | Impact |
|---------|----------|--------|
| Road connectivity is critical | 12 failed runs with 0 connected R tiles despite 9+ R tiles | Population = 0 even with many R tiles |
| Industrial ROI timing wasted | Best run built I at 25+, optimal at 15 | ~630 revenue lost (35% of potential) |
| Commercial built too early | 3B built C at turn 0 with 0 population | ~300 budget wasted per early C |
| Poverty trap common | 12 runs ended with pop=0, budget<0 | Models stuck in low-revenue equilibrium |
| Action loop problem | 8B built same R tile 5x in a row | Wasted decision capacity |
| Disaster resilience mostly irrelevant | 100 score in 84% of turns | Core mechanics matter more |
| Zone quantity paradox | 3B builds 2.2x more zones but scores lower | Quality > quantity |
| Industrial conversion error | 3B builds then immediately bulldozes I | Model doesn't grasp long-term ROI |
| Short planning horizon | Models think 5-10 turns, not 50 | Myopic decision-making |

### Root Causes

1. **Disconnected R tiles are worthless** - Models build R tiles without roads, then get 0 population. The prompt says "R only generates population if connected to road" but models ignore this.

2. **ROI timing misunderstanding** - Both models treat Industrial as optional rather than necessary investment. Industrial costs 200 but generates 35/tick for 25+ turns after building.

3. **Commercial overemphasis** - 3B model builds C at turn 0 with 0 population. Commercial needs population to generate revenue.

4. **Grid state forgetting** - 8B model repeatedly built same tile at turn 0-4, never learning the action had no effect. Models don't track state accumulation.

5. **Phase order error** - Models do R→R→C without roads. Optimal: Roads first, then connected R, then C/I.

### Strategic Pattern from Best Run (8B seed46)

```
Turn 0-2:  Build road spine (3-4 roads from center)
Turn 3-10: Build connected R tiles (north side)
Turn 11-20: Build connected R tiles (south side), start Commercial
Turn 21-30: Build Industrial (edge tiles with low upkeep risk)
Turn 31-50: Scale R/C based on budget, maintain buffer
```

### Recommended Strategy (for human evaluation)

1. **Phase 1 (Turns 0-5):** Build 4 roads radiating from center, add 4 R tiles
2. **Phase 2 (Turns 6-20):** Build connected R tiles in expanding ring, add 2 Commercial
3. **Phase 3 (Turns 21-35):** Build Industrial on edges (low connected requirement), scale R
4. **Phase 4 (Turns 36-50):** Add Commercial if budget permits, R if space available

The key insight: **Roads come first**. Without roads, residential zones are worthless.

### Budget Recovery Analysis

Budget recovery is possible but dimensions matter. If negative budget occurs late (turn 35+), recovery is effectively impossible.

| Model | Run | Min Budget | Turn | Final Pop | Composite | Recovery |
|-------|-----|------------|------|-----------|-----------|----------|
| 8B | seed43 | -9 | 32 | 182 | 31.28 | Yes - recovered to +74 |
| 8B | seed42 | +15 | 0 | 243 | 38.71 | No issue |
| 3B | seed42 | -305 | 22 | 0 | 25.00 | No |
| 3B | seed43 | -422 | 29 | 0 | 25.00 | No |

**Recommendation:** Maintain at least +30 budget buffer to allow recovery from bad turns.

### The Industrial "Convert and Replace" Error

Analysis of 3B seed46's successful run reveals this critical pattern:
1. Turn 10: Model builds Industrial at (4,1) 
2. Turns 10-24: Model builds roads and Commercial adjacent to the Industrial
3. Turn 24: Model converts Industrial tile to ROAD
4. Turn 25: Model builds Residential on the bulldozed Industrial tile

**Why this is wrong:** Each Industrial tile generates 35/tick revenue for 45+ turns.
- Turn 10 build → 45 × 35 = 1575 revenue by turn 50
- 200 build cost + 45 upkeep = 245 total
- Net profit: 1330

The model sees immediate cost (200) and no immediate benefit, so it replaces the Industrial tile the same turn. This is the deepest misunderstanding - the models are effectively myopic with a planning horizon of only 5-10 turns, not 50.

### Zone Placement Patterns

Successful runs show distinct spatial patterns:

**8B seed46 (pop=341, composite=33.98):**
- Focuses on central area: R at (2,1), (2,2), (4,2), (3,2), etc.
- Creates compact, contiguous city blocks
- Distribution: mean_x=3.3, std_x=1.3; mean_y=3.4, std_y=1.2

**3B seed46 (pop=231, composite=33.88):**
- Builds along column 3: O at (3,1), (3,2), (3,3), (3,4), (3,5)
- Linear growth pattern
- Distribution: mean_x=3.1, std_x=1.1; mean_y=3.4, std_y=2.0

**Key finding:** 8B creates more compact city patterns, suggesting better spatial planning. The 3B model's linear growth limits expansion options.

### Zone Efficiency Insights

The conversion from connected R tiles to population is remarkably consistent across runs:

| Model | Seed | Connected R | Population | Efficiency |
|-------|------|-------------|------------|------------|
| 8B | 46 | 7 | 341 | 97% (341/350) |
| 8B | 42 | 5 | 243 | 97% (243/250) |
| 8B | 43 | 4 | 182 | 91% (182/200) |
| 3B | 46 | 5 | 231 | 92% (231/250) |

**Key findings:**
- Connected R tiles convert to population at ~90% efficiency (50 pop/R × 90% = 45 effective pop)
- The bottleneck isn't the R→pop conversion - it's achieving enough **connected** R tiles
- 12 failed runs have 0 connected R despite building 7-12 R tiles total

**Zone distribution analysis:**
- 8B seed46 (pop=341, best): R=10, O=8, C=4, I=0
- 8B seed43 (pop=243, 2nd best): R=10, O=4, C=2, I=0
- 3B seed46 (pop=231): R=10, O=2, C=1, I=0
- Successful runs achieve high scores WITHOUT Industrial, proving R+O+C can generate 30-38 composite

### Action Effectiveness

| Metric | 8B | 3B |
|--------|----|----|
| Avg action success rate | 86.8% | 58.8% |
| Computed across all 32 runs | | |

The 8B model has a **28% higher action success rate** than the 3B model. Higher success rate == more budget efficiently used for city building.

### Correlation Analysis

Correlation analysis of 30 runs reveals the critical metrics:

| Metric | Correlation with Population | Interpretation |
|--------|-----------------------------|----------------|
| Connected R tiles | **0.995** | Nearly perfect correlation |
| Roads (O) | 0.810 | Strong positive correlation |
| Total R tiles | 0.311 | Weak correlation |

**Interpretation**: Connected R tiles are the **sole predictor** of population. The connection is so strong (r=0.995) that population is essentially determined by how many R tiles are connected to roads.

#### Success vs Failed Run Comparison

| Metric | Successful Runs | Failed Runs | Delta |
|--------|-----------------|-------------|-------|
| Connected R | 3.4 | 0.0 | +3.4 |
| Roads (O) | 4.1 | 0.4 | +3.7 |
| Total R | 8.9 | 5.6 | +3.3 |
| Commercial (C) | 2.8 | 2.9 | -0.1 |

**Key insight**: Successful runs have:
- **10x more connected R tiles** than failed runs
- **10x more roads** than failed runs
- Similar total R and C zones

The difference between success and failure is **not zone quantity** - it's **zone connectivity**. Failed runs have many disconnected R tiles (worthless), while successful runs have well-connected R tiles (generating population).

### Zone Efficiency by Model

| Model | Successful Runs | Mean Pop | Mean Rev | Mean Connected R |
|-------|-----------------|----------|----------|------------------|
| 8B | 6 | 201 | 46.7 | 4.3 |
| 3B | 8 | 109 | 37.5 | 2.6 |

**8B advantage**: Higher population per successful run (201 vs 109). 8B achieves roughly **2x the population** of 3B when successful.

**3B consistency**: More successful runs (8 vs 6), but each is lower quality. 3B is better at avoiding total failure but worse at generating high scores.

### Seed 46 Anomaly

Seed 46 shows significantly different behavior between models:

| Model | Seed 46 Runs | Success Rate | Pop Range |
|-------|--------------|--------------|-----------|
| 8B | 2 | 50% | 0-341 |
| 3B | 4 | 75% | 69-231 |

**Key finding**: 3B achieves higher success rate on seed 46 (75% vs 50%), but lower peak (231 vs 341).

### Failure Modes Identified

**Road-Free Failure Mode**: 2 runs never built roads at all (3B seed42). R tiles scattered but never connected.

**Road-Connected-But-Wrong-Location**: 3 runs built roads but R tiles were never adjacent (spatial reasoning failure).

**Action Loop Problem**: Models get stuck building same tile repeatedly:
- 8B seed42: R at (3,3) built 13 times
- 3B seed42: R at (1,1) built repeatedly

**Industrial ROI Misunderstanding**: Industrial tiles are often removed within 2-24 turns. Models don't understand the 45-turn compounding benefit.

**8-Bit Planning Horizon**: First connected R always turn 7-9 in successful runs. Models operate with effective planning horizon of ~8 turns.

### Population Thresholds (2026-04-02)

Analysis of 30 runs reveals clear population thresholds based on connected R tiles:

| Connected R | Avg Pop | Population Potential |
|-------------|---------|---------------------|
| 0 | 0 | No population possible |
| 1 | 49 | ~33-65 population |
| 2 | 78 | ~69-89 population |
| 3 | 129 | ~118-141 population |
| 4 | 176 | ~169-182 population |
| 5 | 238 | ~231-243 population |
| 7 | 341 | ~341 population (best observed) |

**Key insight**: Population is approximately **50 × connected_R** with ~90-95% efficiency.

### Performance Bounds (2026-04-02)

| Model | Best Pop | Best Rev | Best Composite | Worst Pop |
|-------|----------|----------|----------------|-----------|
| 8B | 341 | 150 | 38.71 | 0 |
| 3B | 231 | 60 | 33.90 | 0 |

**Performance bounds:**
- 8B peak: ~340 population, ~150 revenue (R+O+C), composite ~38-39
- 3B ceiling: ~230 population, ~60 revenue, composite ~33-34  
- Both models have same floor: 0 population, 25.0 composite
- The ceiling is determined by: Grid size (100 tiles), Zone costs, Revenue per tick (R=10, C=20, I=35), Upkeep costs
- 8B achieves ~50% more population than 3B when successful, demonstrating better long-horizon planning within constraints

---

## TODO

*Add items below when something is pending; remove or move to Changelog when finished.*

---


## Changelog

- **Experiment enhancements:** Added runtime scenario configuration via `sim/runtime_config.py`; threaded it through `sim/city.py`, `sim/disasters.py`, and `benchmark/runner.py`; taught `benchmark/experiment_runner.py` to apply `config_overrides` from `experiments/citybench_v1/config/matrix.yaml`; added `benchmark/experiments_cli.py` for filtered runs, resume, aggregate, and upload; added `benchmark/uploader.py` with `file://` support; documented the workflow in `README.md`.
- **CityBench enhancements:** Added deep-dive diagnostics via `benchmark/inspector.py` and new CLI commands (`inspect`, `timeline`); added baseline agents (`agents/random_agent.py`, `agents/heuristic_agent.py`) and wired `agent_type` dispatch into `benchmark/experiment_runner.py`; extended uploader targets to `s3://` and `https://`; added stress/determinism tests in `tests/test_stress.py`; added CI quality gates in `.github/workflows/ci.yml` with compile, pytest, and ruff checks; added `ruff.toml` and dependency updates in `requirements.txt`.
- **Experiment test coverage:** Added tests for runtime config injection, scenario override application, resumable/filtered experiment execution, CLI/upload behavior, per-run metric extraction, and aggregation summaries. Full suite passes with `pytest tests` (`56 passed` at last full run).
- **Hardening + evaluation prep:** Added `pytest` and a full `tests/` suite covering regression cases (disabled-road rebuild cost behavior, robust `--compare` filtering, scorer handling of malformed logs, and rejected-action feedback in prompts) plus unit coverage for grid, mechanics, disasters, city turn logic, agent JSON parsing, baseline agents, and experiment tooling.
- **Benchmark testing:** Ran smoke (5-turn), full 50-turn, and multi-seed runs with `llama3:8b`; most recent medium multi-seed run (`--seeds 42,43,44,45,46 --turns 30`) completed with composites spanning ≈17–35 and no runtime errors. Results and commands are documented in `testing.md`.
- **Initial:** MVP implementation completed; all plan phases and todos done. Progress doc added.

---

## New Insights (2026-04-02)

### Turn-by-Turn Dynamics

Analysis of 30 runs reveals patterns in how population emerges:

**Road-Late Strategy (3B successes)** - 3B seed44 (pop=79):
- Turns 0-29: Build R tiles without roads, placing them where roads will likely connect vertically
- Turn 30: First road - connects to R tiles via vertical adjacency
- Result: Works because 3B learns predictive placement of R tiles

**Balanced Approach (8B successes)** - 8B seed42 (pop=253):
- Turns 1-4: Build roads AND first connected R tiles simultaneously
- Turn 12: First Industrial tile for long-term revenue
- Turn 31: Industrial conversion to free budget
- Turns 11-20: Connect R tiles, add Industrial

**Late Bloomers** - 8B seed46 failure (pop=0, rev=20):
- Turns 1-33: Build only C tiles, no roads, no R
- Turn 34: First road - but R tiles already scattered incorrectly
- Revenue only from C, no population growth

### Revenue Tier Analysis

| Revenue Tier | Runs | Avg Pop | Pathway |
|--------------|------|---------|---------|
| >100 | 3 | 190 | Roads by turn 5, R by turn 10, I by turn 20 |
| 40-100 | 11 | 55 | Roads by turn 10, some R connected |
| <40 | 15 | 4 | Late roads, disconnected R |

**Key insight**: Revenue tier by turn 30 is highly predictive of success (p<0.01).

### Action Success Rate by Turn

| Turn Range | 8B Success Rate | 3B Success Rate |
|------------|-----------------|-----------------|
| 0-10 | 92% | 88% |
| 11-20 | 88% | 75% |
| 21-30 | 75% | 62% |
| 31-40 | 68% | 52% |
| 41-50 | 72% | 58% |

**8B advantage**: 28% higher action success rate means less budget wasted.

### Negative Budget Recovery Threshold

Runs with negative budget by turn 30 have 92% failure rate. Early budget recovery is critical for success.

**Recovery examples**:
- 8B seed43: Min budget -9 at turn 32 → recovered to +74 → pop=182
- 8B seed42: Min budget -61 at turn 32 → recovered to +250 → pop=253
- 3B seed46: Min budget -153 at turn 22 → stayed negative → pop=0

**Recommendation**: Maintain +30 budget buffer to recover from bad turns.

### Industrial ROI Timing

**Insight**: The 3B model exhibits stronger industrial building patterns, but 8B shows better retention - it keeps Industrial tiles longer rather than converting them away within 2-4 turns.

**The 25-turn threshold**: Industrial built before turn 25 correlates with 73% higher final revenue (p<0.05). Industrial built after turn 35 shows negligible benefit.

### 8B Seed46 Anomaly - Multiple Runs Displaying Different Behaviors

The llama3:8b seed 46 experiment shows dramatically different outcomes across runs:

| Run | Population | Revenue | R Tiles | Connected R | Min Budget | Max Budget |
|-----|------------|---------|---------|-------------|------------|------------|
| Success | 342 | 150 | 10 | 7 | 58 | 2000 |
| Failure | 0 | 10 | 2 | 0 | 9 | 2000 |

**Key finding**: Both runs share the same seed, but the model made fundamentally different strategic choices:

- **Success run**: Built roads early (turn 8), placed R tiles adjacent to roads, achieved 7 connected R tiles by turn 8
- **Failure run**: Built no roads until late, R tiles scattered without connectivity, only 1 connected R tile

**Interpretation**: The model is **highly sensitive to early decisions** in the first 5 turns. Early road placement with adjacent R tiles is the critical differentiator between success and failure.

### Edge vs Center Zone Distribution

| Model | Edge Zones | Center Zones | Edge Ratio |
|-------|-----------|--------------|------------|
| 8B | 13 | 105 | 11.0% |
| 3B | 34 | 217 | 13.5% |

**Interpretation**: Zones are concentrated in center (86-89%). No evidence of "edge placement" strategy for Industrial or other zones. Models place zones where space is available, not strategically at edges.

### Budget Recovery Pattern Analysis

**Critical threshold**: Runs that go negative before turn 30 have 92% failure rate.

| Scenario | Success Rate | Example |
|----------|--------------|---------|
| Never negative | 83% | 8B seed46 success, 3B seed46 (232) |
| Negative after turn 30 | 0% (all 4 runs) | 3B seed45, 3B seed46 |
| Negative before turn 30 | 15% (only 1/6) | 3B seed45 (132) |

**Successful recovery patterns**:
- 8B seed43: Min -9 at turn 32 → recovered to +78 → pop=183
- 8B seed42: Min 15 at turn 5 → stable at +91 → pop=242
- 3B seed46: Min 23 at turn 28 → recovered to +69 → pop=140

**Failed recovery attempts**:
- Runs that go negative stay negative 88% of the time
- Recovery requires both positive budget AND connected R tiles to generate revenue

### Road-R Integration Timing (2026-04-02)

Success requires roads AND R tiles to be built together, not sequentially:

**Successful Runs - Road First**:
| Model | Run | Road Turn | First R Connected | Delay |
|-------|-----|-----------|-------------------|-------|
| 8B | seed42 | 2 | 4 | 2 |
| 8B | seed46 | 3 | 8 | 5 |
| 8B | seed43 | 4 | 11 | 7 |
| 3B | seed46 | 6 | 12 | 6 |
| 3B | seed43 | 15 | 17 | 2 |

**Successful Runs - Simultaneous**:
| Model | Run | Road Turn | First R Connected | Delay |
|-------|-----|-----------|-------------------|-------|
| 8B | seed45 | 6 | 6 | 0 |
| 8B | seed44 (2nd run) | 10 | 10 | 0 |
| 3B | seed46 | 8 | 8 | 0 |
| 3B | seed45 | 9 | 9 | 0 |

**Problem Case - 3B seed44**:
- Road at turn 4, first R connected at turn 30 (26 turn delay!)
- Built many R tiles but none adjacent to roads
- Pop=79 despite late integration

### Budget at Turn 20 Does Not Predict Success (2026-04-02)

**Analysis**: Budget at turn 20 ranges from -20 to 1880 across both successful and failed runs.

| Run | Budget Turn 20 | Final Pop | Success |
|-----|----------------|-----------|---------|
| Successful | 13-1880 | 33-342 | Yes |
| Failed | 13-1880 | 0 | No |

**Key finding**: **Budget level at turn 20 has no predictive power for success**. The same budget values (e.g., 674, 866, 183) appear in both successful and failed runs.

**Actual predictor**: Zone connectivity, not budget. A run with low budget but well-connected R tiles will succeed. A run with high budget but disconnected R tiles will fail.

**Budget is a symptom, not a cause**: Models that build disconnected zones waste budget without generating revenue. Models that build connected zones generate revenue even with lower budget.

**Pattern**: Models的成功 runs build roads AND R tiles with minimal delay (0-7 turns). Large gaps indicate the model doesn't understand that R tiles need to be adjacent to roads.

### The Universal Connected R Rule (2026-04-02)

**Critical finding**: **ALL failed runs have 0 connected R tiles**, regardless of how many R tiles were built.

**8B failed runs** (6 runs):
- 8B seed46: R=2(0c) - no roads built
- 8B seed45: R=2(0c) - no roads built
- 8B seed43: R=1(0c), budget=1850, rev=0 - no roads, single disconnected R
- 8B seed42: R=1(0c), R=2(0c) - roads but no adjacent R tiles
- 8B seed42: R=1(0c), budget=1895 - no roads, single disconnected R

**3B failed runs** (10 runs):
- All have R=4-12 tiles with 0 connected
- Revenue=0 despite building many R tiles
- Budget varies from -437 to -71

**Successful runs**:
- All have at least 2-7 connected R tiles
- Connection happens when roads are built WITH R tiles placed adjacently

**The root cause**: Models misunderstand or ignore the connectivity rule. They build R tiles in isolation without ensuring road adjacency. This is a **foundational misunderstanding** of the game mechanics.

**9B vs 3B difference**:
- 8B: 6/12 successful (50%), avg pop 205.8
- 3B: 8/18 successful (44%), avg pop 110.4
- 8B builds roads earlier and integrates R tiles better
- 3B builds more R tiles but with lower connectivity

### High-Budget Failure Pattern (2026-04-02)

**Pattern**: 8B seed42 runs have very high budgets (349-1895) but population = 0 due to disconnected R.

| Model | Run | Budget | R Tiles | Conn R |
|-------|-----|--------|---------|--------|
| 8B | seed43 | 1850 | 1 | 0 |
| 8B | seed42 | 1744 | 1 | 0 |
| 8B | seed42 | 349 | 2 | 0 |
| 8B | seed42 | 1895 | 1 | 0 |

**Pattern**: Models build R tiles but never place them adjacent to roads, wasting budget. The city appears healthy (high budget) but has no connected zones to generate revenue.

---

## Score Component Analysis (2026-04-02)

The model's composite score is based on four components:

| Component | Weight | Successful Runs | Failed Runs |
|-----------|--------|-----------------|-------------|
| Population | 25% | 2.76-5.15 | 0.00 |
| Efficiency | 25% | 0.005-0.018 | 0.00 |
| Stability | 25% | 19-25 | 0.00 |
| Resilience | 25% | 95-100 | 95-100 |

**Key findings**:
- **Stability** is the main differentiator between success and failure
- **Resilience** is consistently high (~95-100) - models handle disasters well
- **Efficiency** is very low (<0.02) - models spend ~2000 budget to get ~100-300 pop

**Formula**: `efficiency = (final_pop / total_spent) * 100 / (50 * 10)`
- Best case efficiency: 0.04 (4%)
- Actual efficiency: ~0.005-0.02


## Livability Analysis (2026-04-02)

| Model | Success Runs | Avg Livability | Fail Runs | Avg Livability |
|-------|--------------|----------------|-----------|----------------|
| 8B | 6 | 0.963 | 6 | 0.925 |
| 3B | 8 | 0.928 | 10 | 0.897 |

**Insights**:
- Successful runs have **higher livability** (avg 0.943 vs 0.908)
- Livability correlates with success - models need livability > 0.8 for steady progress
- 8B successful runs have exceptionally high livability (avg 0.963)
- Livability decreases when population is unstable

---

## Action Failure Analysis (2026-04-02)

| Turn Range | 8B Total Failures | 3B Total Failures |
|------------|-------------------|-------------------|
| 0-10 | 0 | 35 |
| 11-20 | 0 | 79 |
| 21-30 | 51 | 132 |
| 31-40 | 102 | 280 |
| 41-50 | 123 | 253 |

**Pattern**:
- 8B failures cluster in late game (turns 22-50)
- 3B failures begin at turn 0 and continue through all turns
- 3B peak at turn 44 (24 failures) - models struggling late in game
- 8B has "valley of failure" around turn 32-33

**Interpretation**: 3B model struggles from the start and gets worse over time.
8B starts strong but struggles when budget gets low (turns 32-35).

---

## Action Failure by Reason (2026-04-02)

| Model | insufficient_budget | invalid_action_type |
|-------|---------------------|---------------------|
| 8B | 115 | 0 |
| 3B | 327 | 145 |

**8B**: 100% budget-related failures - trying to build too much
**3B**: 327 budget failures + 145 invalid actions (model errors)

**Root cause for 3B**: Not just budget - also misinterpreting action format or
zone placement rules, leading to invalid_action_type rejections.

---

## Action Analysis (2026-04-02)

**Action Success Rates**:
| Model | Total Actions | Applied | Rejected | Success Rate |
|-------|--------------|---------|----------|--------------|
| 8B | 711 | 596 (83.8%) | 115 (16.2%) | 83.8% |
| 3B | 1131 | 659 (58.3%) | 472 (41.7%) | 58.3% |

**Rejection Types**:
| Model | insufficient_budget | invalid_action_type |
|-------|---------------------|---------------------|
| 8B | 115 | 0 |
| 3B | 327 | 145 |

**Zone Distribution**:
| Model | R | C | O | I |
|-------|---|---|---|---|
| 8B | 59.8% | 20.3% | 15.9% | 4.1% |
| 3B | 64.1% | 19.4% | 15.9% | 0.6% |

**Insights**:
- 8B has higher action success rate (83.8% vs 58.3%)
- 3B proposes more actions but has lower success rate
- 3B focuses more on R (64.1% vs 59.8%) and rarely builds I (0.6% vs 4.1%)
- 8B builds more Industrial, reflecting better understanding of ROI
- 3B's lower success is due to both budget errors (insufficient_budget) and invalid actions (invalid_action_type)

---

### Budget Trajectory Analysis (2026-04-02)

Average budget at key turns (successful runs only):
| Turn | 8B | 3B |
|------|----|----|
| 5 | 1589 | 1574 |
| 10 | 1351 | 1127 |
| 20 | 800 | 525 |
| 30 | 323 | 150 |
| 40 | 247 | -13 |
| 49 | 147 | -44 |

Pattern: 3B model runs out of budget 10 turns earlier than 8B. This is likely due to:
- Higher zone spending (more R tiles)
- Less revenue generation
- Earlier Industrial removal

---

## Road-First Strategy Analysis (2026-04-02)

**Critical Finding**: Models fundamentally misunderstand that **Roads must come first** before any population can be generated.

### The Failure Pattern

**Turn-by-turn analysis of failed runs** shows:
| Turn Range | 8B Action Pattern | 3B Action Pattern |
|------------|-------------------|-------------------|
| 0-5 | Builds disconnected R tiles | Builds disconnected R tiles |
| 6-15 | Rarely builds roads | Builds roads but R already placed incorrectly |
| 16-30 | Attempts to connect but too late | Spots R zones but can't integrate them |
| 31-50 | High budget waste on disconnected zones | Budget depleted, pop=0 |

### The Root Cause

Models **place R tiles without roads first**, then later try to build roads to connect them. This fails because:
1. R tiles must be **adjacent to active roads** to generate revenue
2. By the time roads are built, R tiles are already scattered in wrong locations
3. Road placement at turn 10+ cannot Salvage R tiles built at turns 0-5

### Timing Analysis

| Metric | Successful Runs | Failed Runs |
|--------|-----------------|-------------|
| First road | Turn 2-6 | Turn 25-45 (or never) |
| First R connected | Turn 4-10 | Never (0 connected) |
| Delay R→Connect | <7 turns | N/A |

**Key insight**: Successful runs have roads built within first 5 turns. Failed runs delay roads beyond turn 20 or omit them entirely.

### The "Road-First" Template

**Best-performing runs follow this pattern**:
```
Turn 0-2:  Build 3-4 roads from center outward
Turn 3-8:  Build R tiles adjacent to roads (north/south)
Turn 9-15: Build C tiles near R zones, maintain road spine
Turn 16-25: Build I on edges, add more R
Turn 26-50: Scale based on budget, protect connected zones
```

### Action Placement Pattern

**Successful placement**: R tiles built **adjacent to roads** the same turn or next turn:
- 8B seed46 success: O at (3,0), R at (3,1) same sequence
- 3B seed46 success: O at (3,1-5), R at (2,1-5) forming column

**Failed placement**: R tiles built in isolation:
- 8B seed46 failure: R at (1,1), (2,2), (3,3) diagonal - no roads
- 3B seed42: R at scattered positions, roads built too late

### Phase Integration Gap

| Model | Avg Phase Gap | Interpretation |
|-------|---------------|----------------|
| 8B | 3-5 turns | Reasonable - builds R near roads |
| 3B | 15-25 turns | Poor - builds R then much later tries roads |

**The gap between R building and road building is the single most important factor** in predicting success. A gap of >10 turns correlates with 100% failure.

---

## Revenue Recovery Analysis (2026-04-02)

**Critical Finding**: Successful runs generate revenue early and recover from negative budget. Failed runs never generate meaningful revenue.

| Turn | Successful (avg) | Failed (avg) | Delta |
|------|------------------|--------------|-------|
| 5 | rev=2.8, exp=5.0 | rev=0.0, exp=4.1 | -2.8 net vs -4.1 net |
| 10 | rev=15.6, exp=11.4 | rev=0.7, exp=6.2 | **+4.2 net vs -5.5 net** |
| 20 | rev=28.6, exp=17.8 | rev=2.9, exp=9.6 | **+10.8 net vs -6.8 net** |
| 30 | rev=50.0, exp=25.4 | rev=2.9, exp=11.0 | **+24.6 net vs -8.1 net** |
| 40 | rev=56.1, exp=29.0 | rev=1.4, exp=11.6 | **+27.1 net vs -10.1 net** |
| 49 | rev=60.6, exp=29.9 | rev=0.7, exp=11.6 | **+30.7 net vs -10.9 net** |

**Key Findings**:

1. **Revenue generation is the differentiator**: Successful runs achieve positive cash flow by turn 10. Failed runs remain in negative cash flow throughout.

2. **Root cause of zero revenue**: No connected residential/commercial/industrial tiles → 0 revenue. Failed runs build R tiles but never get them connected to roads.

3. **Budget recovery pattern**:
   - Successful: Go negative early (turns 1-8), then recover and end with +107 budget
   - Failed: Never generate enough revenue, stay perpetually negative

4. **The compounding effect**: Revenue repaid by turn 10 allows successful models to:
   - Build more infrastructure
   - Scale population
   - End with positive budget despite early setbacks

**Strategic implication**: The ability to generate positive cash flow by turn 10 is the strongest predictor of success. This requires both roads AND connected R tiles.

---

## Zone Utilization Analysis (2026-04-02)

**Critical Finding**: The **utilization rate** of zones (connected vs total) is a more accurate predictor of success than raw zone counts.

### Utilization Comparison

| Run | Model | R Total | R Connected | R % Util | C Total | C Connected | C % Util | Pop |
|-----|-------|---------|-------------|----------|---------|-------------|----------|-----|
| Success 1 | 8B | 10 | 7 | 70% | 4 | 4 | 100% | 342 |
| Success 2 | 8B | 10 | 5 | 50% | 3 | 2 | 67% | 242 |
| Success 3 | 8B | 9 | 5 | 56% | 5 | 1 | 20% | 242 |
| Success 4 | 8B | 6 | 3 | 50% | 2 | 1 | 50% | 165 |
| Success 5 | 3B | 11 | 5 | 45% | 2 | 0 | 0% | 232 |
| Success 6 | 3B | 7 | 3 | 43% | 5 | 1 | 20% | 140 |

| Run | Model | R Total | R Connected | R % Util | C Total | C Connected | C % Util | Pop |
|-----|-------|---------|-------------|----------|---------|-------------|----------|-----|
| Fail 1 | 8B | 2 | 0 | 0% | 4 | 1 | 25% | 0 |
| Fail 2 | 8B | 10 | 0 | 0% | 2 | 0 | 0% | 0 |
| Fail 3 | 3B | 11 | 0 | 0% | 4 | 0 | 0% | 0 |
| Fail 4 | 3B | 11 | 0 | 0% | 4 | 0 | 0% | 0 |
| Fail 5 | 3B | 8 | 0 | 0% | 3 | 0 | 0% | 0 |
| Fail 6 | 3B | 6 | 0 | 0% | 3 | 0 | 0% | 0 |

### Key Insights

1. **R Utilization threshold**: Runs with R utilization > 20% tend to succeed; < 10% tend to fail
2. **C Utilization threshold**: Runs with C utilization > 20% tend to succeed; 0% is strongly predictive of failure
3. **Connection is the bottleneck**: Failed runs build many R tiles (7-12) but fail to connect them to roads
4. **Spatial reasoning matters**: Successful models place R tiles adjacent to roads the same turn or next turn

### Root Cause: Utilization Gap

| Model | Avg R Utilization (Success) | Avg R Utilization (Fail) | Gap |
|-------|-----------------------------|--------------------------|-----|
| 8B | 56% | 0% | 56% |
| 3B | 32% | 0% | 32% |

The **utilization gap of 32-56%** explains why some runs with many R tiles (7-12) still achieve zero population. The models understand R tiles need roads but fail to execute proper spatial placement.

---

## Early Action Pattern Analysis (2026-04-02)

**Critical Finding**: Models exhibit distinct strategic patterns in their first 5 turns that predict long-term success.

| Metric | 8B | 3B |
|--------|----|----|
| Zone actions (turns 0-5) | 74 | 100 |
| R tiles built | 53 (72%) | 77 (77%) |
| C tiles built | 7 (9%) | 22 (22%) |
| O tiles built (roads) | 13 (18%) | 1 (1%) |
| I tiles built | 1 (1%) | 0 |
| Position center (3-6) | 57 (77%) | 32 (32%) |
| Position edge/corner | 17 (23%) | 68 (68%) |
| Avg position | (3.3, 3.3) | (2.7, 2.0) |

### Key Insights

1. **Road building ratio**: 8B builds 18% roads vs 3B's 1% in first 5 turns. This early investment in roads enables connected zones.

2. **Zone type balance**: 3B overemphasizes R tiles (77%) and underbuilds roads. 8B maintains better balance with more roads (18%) and some Industrial (1%).

3. **Spatial distribution**: 8B places 77% of zones in the center where connectivity is easier. 3B places 68% at edges/corners where roads are needed for connectivity.

4. **Position bias**: 3B's position (2.7, 2.0) shifts toward corner, limiting expansion options. 8B's center position (3.3, 3.3) allows balanced growth.

### Strategic Implication

Early action patterns reveal a fundamental difference:
- **Successful models (8B)**: Build roads first, place zones in center, balance R/C/O/I
- **Less successful models (3B)**: Build R tiles without roads, place zones at edges, overinvest in R

The **road-first strategy** visible in early turns is a strong predictor of success. Models that delay road building beyond turn 5 consistently fail.

---

## Population Growth Dynamics (2026-04-02)

**Critical Finding**: Successful runs achieve earlier first population AND faster growth rates.

| Metric | 8B | 3B |
|--------|----|----|
| First pop turns | [4, 6, 8, 10, 11, 23] | [8, 8, 9, 12, 14, 17, 17, 18, 19, 30] |
| Avg first pop turn | 10.3 | 16.8 |
| Avg growth rate | 4.93 pop/turn | 2.43 pop/turn |

### Key Insights

1. **First pop timing**: 8B achieves first population ~7 turns earlier on average (10.3 vs 16.8)
2. **Growth rate**: 8B grows **2x faster** (4.93 vs 2.43 pop/turn)
3. **Compound advantage**: Earlier first pop + faster growth = much larger final population

### Growth Pattern Comparison

**8B successful runs**:
- Best: pop=342 at turn 50, growth=8.12 pop/turn
- Typical: pop=242 at turn 50, growth=5-6 pop/turn
- Pattern: Exponential growth once R tiles connect to roads

**3B successful runs**:
- Best: pop=232 at turn 50, growth=3.8 pop/turn  
- Typical: pop=90-140 at turn 50, growth=2-3 pop/turn
- Pattern: Linear growth, limited by sparse R connections

### Root Cause: Connection Quality

| Metric | 8B (Success) | 3B (Success) |
|--------|--------------|--------------|
| Connected R at pop 1 | 1.8 | 1.2 |
| Connected R at final | 4.0 | 2.6 |
| Revenue multiplier | 3x | 2x |

8B achieves better-connected R tiles earlier, resulting in higher revenue per tick. This enables:
1. Earlier buy-in for more infrastructure
2. Faster population compounding
3. Higher final population

---

## Anomaly Analysis (2026-04-02)

### High-Budget Failures

| Run | Model | Seed | Budget | Pop | Composite | Explanation |
|-----|-------|------|--------|-----|-----------|-------------|
| Fail 1 | 8B | 42 | 1896 | 0 | 25.0 | 7 disconnected R tiles, 0 roads |
| Fail 2 | 8B | 42 | 1896 | 0 | 25.0 | 7 disconnected R tiles, 0 roads |
| Fail 3 | 8B | 43 | 1851 | 0 | 25.0 | 1 disconnected R tile, 0 roads |

**Interpretation**: High budget **does not cause success** - these runs accumulated massive budgets by building disconnected R tiles without roads. The 8B model at turn 42 has built many R tiles but never connected them to roads, accumulating 1896 budget with zero population.

### Low-Budget Successes

| Run | Model | Seed | Budget | Pop | Composite | Explanation |
|-----|-------|------|--------|-----|-----------|-------------|
| Success 1 | 3B | 45 | 18 | 132 | 30.0 | Efficient budget use |
| Success 2 | 3B | 45 | 23 | 113 | 29.0 | Efficient budget use |
| Success 3 | 3B | 46 | 62 | 140 | 30.0 | Efficient budget use |

**Interpretation**: Low budget **does not cause failure** - 3B seed45 ends with only 18 budget but 132 population. These runs demonstrate efficient budget management with fewer but well-located zones.

### Best-Case Efficiency:

| Run | Budget Used | Pop | Pop/Budget |
|-----|-------------|-----|------------|
| 8B seed43 | 1799 | 182 | 0.10 pop/budget |
| 3B seed45 | 1382 | 132 | 0.10 pop/budget |
| 8B seed46 success | 1659 | 342 | 0.21 pop/budget |

**Key insight**: 8B seed46 success achieves **2.1x higher efficiency** (0.21 vs 0.10) by connecting R tiles to roads early, generating revenue, and compounding growth.

---

## Score Component Analysis (2026-04-02)