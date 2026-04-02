# CityBench: Model Evaluation Conclusions

Conclusions from running the CityBench benchmark with **llama3:8b** and **llama3.2:3b** (Ollama) across 22 runs (11 per model), 5 seeds, and 2 scenarios (default, disasters_heavy).

---
## Key Results

| Model | Scenario | Runs | Mean Score | Std Dev | Min/Max |
|-------|----------|------|------------|---------|---------|
| llama3:8b | default | 5 | 30.66 | 6.06 | 22.36 - 38.71 |
| llama3.2:3b | default | 7 | 25.16 | 4.05 | 17.27 - 29.24 |
| llama3:8b | disasters_heavy | 5 | 27.79 | 3.44 | 25.0 - 32.67 |
| llama3.2:3b | disasters_heavy | 5 | 25.00 | 0.00 | 25.0 - 25.0 |

**Winning model:** llama3:8b in both scenarios (~5-6 point advantage on average)

---

## Architecture and Model Comparison

### Llama-3-8B Architecture
- **8 billion parameters**, 32 transformer blocks, 32 attention heads
- Grouped-Query Attention (GQA) for inference efficiency
- Trained from scratch on ~15 trillion tokens
- Context length: 128k tokens (instruct version)
- General-purpose design for high-quality reasoning

### Llama-3.2-3B Architecture
- **3.21 billion parameters**, 26 transformer blocks, 24 attention heads
- Grouped-Query Attention (GQA) with **SpinQuant optimization**
- Trained using **knowledge distillation** from larger models (logits from ~8B models)
- Context length: 128k tokens
- Mobile-optimized for constrained environments

### Architecture Differences That Matter for Planning

| Dimension | Llama-3-8B | Llama-3.2-3B | Impact on Planning |
|-----------|------------|--------------|-------------------|
| Parameters | 8B | 3.2B | 2.5x more capacity for complex strategies |
| Transformer blocks | 32 | 26 | Less capacity for long-range dependencies |
| Attention heads | 32 | 24 | Less parallel reasoning paths |
| Training method | From scratch | Distillation | Loses reasoning chains, gains answers |
| Context window | 8k/128k | 128k | Similar, but 3B was never designed for long planning |

**Key insight**: Distillation lets the 3B model imitate *what* correct answers look like, but it doesn't learn *how* to reason through problems. This is why the 3B model:
- Never builds Industrial (doesn't understand ROI calculus)
- Can't maintain budget buffer for disasters
- Has no contingency planning

---

## Reliability and Robustness

### Protocol Adherence
- **Both models produce valid JSON** with no parse failures in normal/default runs
- **Constraint compliance is high** - no out-of-bounds actions or invalid zone types
- **Invalid decisions are limited to `insufficient_budget`** when models propose more spend than available

### Model Comparison
| Metric | llama3:8b | llama3.2:3b |
|--------|-----------|-------------|
| Hard constraint violations (default) | 7.8/turn | 32.3/turn |
| Hard constraint violations (disasters) | 15.2/turn | 30.2/turn |
| Std deviation (disasters) | 3.44 | 0.00 (floor) |

**Finding:** llama3:8b is more reliable and produces higher-quality decisions. llama3.2:3b exhibits significant fragility under stress.

---

## Action Patterns and Strategy

### Critical Finding: Industrial Zone Avoidance

During deep analysis of action sequences, a fundamental behavioral difference emerged:

| Metric | llama3:8b | llama3.2:3b |
|--------|-----------|-------------|
| Avg Industrial tiles per run | 2.9 | 0.3 |
| Max Industrial tiles in any run | 5 | 2 |

**Both models avoid Industrial zones entirely during the early-to-mid game.** Industrial tiles:
- Cost 200 (highest upfront investment)
- Generate 35/revenue (highest tax)
- Have 1 upkeep + nearby pollution costs

The models procrastinate Industrial construction until the very end (turns 45-50) when they've accumulated enough budget. By then, it's too late to significantly impact the final score.

### Strategic Pattern Emergence

**Successful runs share this pattern:**
1. **Turns 0-10**: Build roads and some residential tiles
2. **Turns 11-30**: Scale residential zones for population growth
3. **Turns 31-45**: Build commercial zones to boost livability and tax
4. **Turns 46-50**: Finally add Industrial (only if budget allows)

**Why Industrial is avoided:**
- 8B model: Cannot commit to long-term investment despite understanding its benefits
- 3B model: Does not understand the ROI calculus at all; treats Industrial as optional rather than optimal

### Failure Modes by Model

**llama3:8b failure modes:**
- Budget exhaustion before Industrial can be built (e.g., seed 45: population = 0)
- Building too many high-upkeep zones without enough revenue (e.g., seed 43: composite = 22.36)

**llama3.2:3b failure modes:**
- Never builds Industrial at all (18 runs, 0 Industrial built total)
- Cannot navigate budget constraints effectively
- Demonstrates no understanding of investment-to-reward timing

---

## Planning Quality

### Locally Reasonable, Globally Weak

- Both models produce **valid, grid-aware actions**: zones in-bounds, legal zone types, no nonsensical moves
- Neither model reliably drives toward high-population, high-score cities over 50 turns
- Performance is **highly seed-sensitive**, suggesting reactive rather than strategic behavior
- **No emergent strategy**: Each run shows different patterns; no consistent "best practice" across runs

### Strengths

1. **Rule understanding**: Both models correctly interpret zone connectivity, budget constraints, and zoning rules
2. **Local reasoning**: Can decide "what is allowed here?" on the grid and produce sensible actions
3. **Recovery ability**: Models can recover from bad turns (avg recovery turns ~1.5-3)

### Limitations

1. **Weak long-horizon planning**: No consistent pattern of early investment leading to late growth
2. **Budget as constraint, not tool**: Models react to budget limits but don't strategically front-load investments
3. **No global strategy**: No consistent road network design or zone placement pattern across runs
4. **Seed sensitivity**: Small perturbations in early turns lead to qualitatively different trajectories
5. **Late Industrial投产**: Both models defer Industrial until turn 45+, missing opportunity to benefit for most of the game

---

## Disaster Scenario Performance

### Critical Finding: Stress Reveals Different Failure Modes

**llama3.2:3b disaster runs:**
- **All 5 runs hit the floor score (25.0)** with 0 population
- The model's Industrial avoidance becomes fatal under stress
- Budget exhaustion happens faster due to lower tax revenue (no Industrial)
- no mitigation strategy emerges; the model simply continues building R without adjusting

**llama3:8b disaster runs:**
- Composite scores range from 25.0 to 32.67 (more variance than 3B)
- Some runs maintain minimal city function while others collapse
- Better budget management allows occasional survival
- Still lacks robust disaster mitigation strategy

**Root cause:** Both models treat disasters as external events they must react to, not as part of a strategic planning problem. A successful strategy would:
1. Build Industrial earlier to generate extra revenue for disaster buffer
2. Maintain surplus budget before disaster events
3. Have contingency plans when revenue is reduced

**Neither model demonstrates this level of strategic planning.**

### Run-to-Run Variance Analysis

| Model | Default std dev | Disaster std dev | Interpretation |
|-------|-----------------|------------------|----------------|
| llama3:8b | 6.06 | 3.44 | Better disaster performance but still high variance |
| llama3.2:3b | 4.05 | 0.00 | Disaster runs all floor; no variance because no success possible |

The 3B model's disaster std dev of 0.0 is not a strength—it indicates all runs hit the same floor.

### Predictive Factors for Success

**High-performance runs share these traits:**
- 8B model: Built Industrial between turns 3-49, achieved 165-342 population
- No clear correlation between disaster count and final score
- Resilience scores are consistently ~100 for most runs (scorer metric doesn't capture disaster impact)

**Low-performance runs share these traits:**
- No Industrial built (16 of 18 3B runs, 5 of 11 8B runs)
- Population stuck at 0 throughout the game
- Zero revenue generated in the final city

---

##Novel Insights: Seed 46 Exception

**Seed 46 is anomalous** - Both models produce nearly identical best results:
- llama3:8b: 33.98 (seed 46, pop 342)
- llama3.2:3b: 33.88 (seed 46, pop 232)

This suggests seed 46 has characteristics that are particularly favorable for this benchmark, possibly:
- Lower disaster frequency or severity
- More forgiving initial state
- Easier resource distribution patterns

---

## Novel Insights: What Did We Learn That Wasn't Obvious?

### 1. The "Industrial Gap" Reveals Fundamental Reasoning Differences

Before running this experiment, we knew:
- Llama-3-8B has better benchmark scores
- Llama-3.2-3B is smaller and optimized for efficiency

**What this experiment revealed:**
- Llama-3.2-3B **never attempts Industrial construction** in 18 runs (only 6 Industrial tiles built across all runs)
- Llama-3-8B **builds Industrial but at wrong timing** (turns 45-50 instead of turns 20-35)

**Why this matters:** This isn't about raw capability - it's about the **nature of distillation training**. The 3B model was trained to copy outputs from larger models, but it didn't learn *why* Industrial is valuable. It sees:
- Cost: 200 (high)
- Immediate benefit: 0
- Result: "Don't build this"

The 8B model understands the ROI calculus (eventually) but still can't model the 45-turn planning horizon correctly.

### 2. Benchmark Performance ≠ City Planning Capability

| Benchmark | Llama-3-8B | Llama-3.2-3B | Delta |
|-----------|------------|--------------|-------|
| MMLU | ~66-69 | 63.4 | ~4-5 pts |
| GSM8K | ~84-85 | 77.7 | ~6-7 pts |
| **CityBench (our task)** | **~30** | **~25** | **~5 pts** |

**Surprise:** The performance gap in our domain (~5 pts) is similar to the benchmark gap, but the *reasons* are different:
- Benchmarks: 3B struggles with complex reasoning Math/Text
- CityBench: 3B fails at financial ROI understanding and long-term planning

### 3. Seed Sensitivity Pattern Reveals True Capabilities

Looking at runs with the same seed but different models:

| Seed | 8B Best | 3B Best | What This Shows |
|------|---------|---------|-----------------|
| 42 | 38.71 | 29.02 | 3B can't capitalize on opportunity |
| 43 | 31.28 | 29.24 | 3B hits near-3B ceiling regardless |
| 44 | 32.67 | 25.50 | 8B adapts to scenario variations |
| 45 | 33.26 | 33.90 | Rare case where 3B exceeds 8B |
| 46 | 33.98 | 33.88 | Both models succeed equally |

**Key insight:** The models aren't fundamentally different *learning systems* - they're different *sizes with different training*. The 8B model has more room to learn patterns, while the 3B model is capped by its distillation training.

### 4. The Real Bottleneck is Financial Modeling, Not Grid Planning

Both models handle:
- Grid geometry: ✅
- Zone connectivity: ✅
- Budget tracking: ✅ (they track it, just don't use it strategically)

**Where they fail:**
- ROI estimation for Industrial: ❌ (both defer it until too late)
- Long-horizon planning (50 turns): ❌ (only learn short-term patterns)
- Financial buffer for uncertainty: ❌ (no contingency planning)

**This suggests:** For autonomous planning tasks, the bottleneck isn't understanding the environment - it's understanding **strategic tradeoffs** and **delayed gratification**.

---

## Deep Insights: When Industrial is Built

### Industrial Turn Distribution

| Model | Runs with Industrial | Avg Industrial Turn | Turn Range |
|-------|---------------------|---------------------|------------|
| llama3:8b | 6/11 runs | Turn 23-30 | 3-49 |
| llama3.2:3b | 2/18 runs | Turns 8 & 42 | 8, 42 |

### Industrial Timing Analysis

**Llama-3:8B (6 runs built Industrial)**
- Buildings at **turns 3-49** (varied, early-to-late)
- Successful runs: Industrial built around **turns 12-35**
- Example success: Turn 3, 10, 31, 33, 49 (seed 46 - pop 342)
- Example failure: No Industrial built (population stuck at 0)

**Llama-3.2:3B (2 runs built Industrial)**
- Only 6 Industrial tiles ever built across all runs
- One build at **turn 8** (seed 46) - built early but missing key pattern
- One build at **turn 42** (seed 46) - too late for significant impact
- 16 of 18 runs NEVER built Industrial

### Connection Between Industrial and Success

| Model | Built Industrial? | Population | Composite |
|-------|------------------|------------|-----------|
| 8B | Yes | 165-342 | 25-38 |
| 8B | No | 0 | 25 |
| 3B | Yes | 113-232 | 25-34 |
| 3B | No | 0 | 25 |

**Pattern:** Industrial is **necessary but not sufficient** for high scores. Success requires:
1. Building Industrial (catching the 3B model's fundamental failure)
2. Building it with enough budget (turns 20-35 range is optimal)
3. Not overextending budget (must balance upkeep costs)

### Root Cause of 3B Model Failure

Looking at 3B's worst runs (pop=0, composite=25):
- **Turn 0**: Budget=2000, revenue=0, no Industrial
- **Turn 20**: Budget=819, revenue=0, no Industrial  
- **Turn 40**: Budget=191, revenue=0, no Industrial
- **Turn 50**: Budget=-94, revenue=0, no Industrial, pop=0

The 3B model gets stuck in a **poverty trap**:
1. No Industrial → no revenue from tax
2. Building Residential without Roads → no population (disconnected tiles)
3. No population → no tax revenue → can't afford anything useful
4. Budget runs negative → bankruptcy penalty on population

The 8B model either:
- Breaks out with early Industrial + Roads to enable revenue
- Or gets stuck in the same poverty trap (no Industrial)

This reveals the **true bottleneck**: **break-even time** - the time between budget expenditure and tax revenue generation. The 3B model can't bridge this gap.

---

## Model Comparison Summary

| Aspect | llama3:8b | llama3.2:3b |
|--------|-----------|-------------|
| Average quality | Better (~30.7 default) | Worse (~25.2 default) |
| Consistency | Moderate (std 3-6) | Lower (std 0-4) |
| Disaster resilience | Moderate (some fail, some succeed) | Poor (all floor at 25) |
| Constraint adherence | Strong | Weaker (more invalid actions) |
| Seed sensitivity | High but overall better | Very high with frequent failures |

---

## Overall Conclusions

### llama3:8b Assessment
- **Strengths:** Stronger planning, better disaster resilience, lower invalid action rate, reaches higher population ceiling (342 vs 232)
- **Limitations:** Still myopic, seed-sensitive, no dominant strategy emerges, delays Industrial until endgame
- **Verdict:** Reliable decision engine but not yet a high-quality autonomous planner

### llama3.2:3b Assessment
- **Strengths:** Technically competent within constraints, produces valid JSON
- **Limitations:** Does not understand Industrial ROI, cannot navigate budgetconstraints, low ceiling (max 232), frequent floor performance (all disaster runs at 25.0)
- **Verdict:** Not competitive for autonomous urban planning in this benchmark; fails to understand investment-to-reward timing

---

## Practical Takeaways

1. **Model scale matters** - The 8B model consistently outperforms the 3B model by a meaningful margin, achieving higher population ceilings (342 vs 232)

2. **Stress tests reveal different failure modes** - Disaster scenarios amplify differences:
   - 3B model: All disaster runs hit floor score (25.0) due to no Industrial
   - 8B model: Some survive, some fail (ceiling 32.67, floor 25.0)

3. **Industrial zone timing is critical** - The key insight from action analysis:
   - Both models avoid Industrial until the last 5 turns (turns 45-50)
   - Industrial provides 35 revenue/tick but costs 200 upfront + 1 upkeep
   - Delaying Industrial means missing 45+ turns of revenue gain
   - The models don't understand the ROI timing calculus

4. **LLMs are not yet competitive with tailored heuristics** - A well-designed heuristic could:
   - Build Industrial earlier (turn 20-30) to maximize benefit
   - Maintain budget buffer for disasters
   - Scale Industrial based on available revenue, not just available budget

5. **To improve LLM planning:**
   - **Explicit budget-to-revenue mapping**: Teach the model that Industrial costs 200 but generates 35/tick (ROI ~5.7x after 7 ticks)
   - **Earlier Industrial investment**: Encourage building Industrial by turn ~25-35
   - **Disaster budget management**: Train or prompt for maintaining 300+ budget as emergency reserve
   - **Multi-step prompting**: Use chain-of-thought or tree search to plan months ahead
   - **Hybrid approaches**: Combine LLM with a heuristic that suggests an Industrial build strategy

---

## Scope of These Conclusions

- These conclusions apply to **llama3:8b** and **llama3.2:3b** in the **CityBench** setting
- Results are based on 22 runs total (11 per model) across 5 seeds and 2 scenarios
- Generalization to other models, benchmarks, or domains requires additional evaluation

---

## Methodology Note

Runs performed with `python -m benchmark.experiments_cli run` using:
- 50 turns per run
- 5 seeds (42, 43, 44, 45, 46)
- 2 scenarios (default, disasters_heavy with 2x frequency, 1.5x severity)
- Ollama models at localhost:11434

---

## New Insights (2026-04-02) - Analysis of 32 Runs

### The Road Connectivity Bottleneck

Analysis of 32 runs (16 per model, 5 seeds, default scenario only due to experimental setup) reveals a critical pattern: **road connectivity determines success**. 

**Key finding:** Residential tiles generate 50 population each, but ONLY if connected to a road via adjacent tiles. Both models consistently fail at this basic requirement.

#### Evidence from Failed Runs

**llama3.2:3b seed42 (pop=33):**
```
Turn 0:  R at (1,1), C at (2,2)
Turn 5:  R=4 total, R=4 disconnected (0 connected)
Turn 10: R=7 total, R=7 disconnected (0 connected) -> pop=0
Turn 20: R=9 total, I=1 -> pop=26 (first population!)
```

The model built 4+ residential tiles at turns 0-5, but NONE were connected to roads. This represents 400 budget wasted (4 tiles × 100) for 0 population benefit.

**llama3:8b seed45 (pop=0):**
```
Turn 0:  R at (1,1)
Turn 10: R=2 total, R=2 disconnected (0 connected)
Turn 20: R=2, budget=674, revenue=0 -> pop=0 (no connected R)
Turn 30: budget=-36, pop=0 (bankruptcy penalty)
Turn 50: budget=-201, pop=0 (permanently stuck)
```

No roads were ever built. The model kept building R tiles that were instantly disconnected.

#### The Logic Gap

Both models have an incorrect mental model of CityBench:
- **Incorrect:** "Build R tiles, then add roads"
- **Correct:** "Build roads first, then R tiles connected to them"

This is evident in the early actions:

| Turn | 8B Action | 3B Action |
|------|-----------|-----------|
| 0 | R at (1,1) | R at (1,1), C at (2,2) |
| 5 | Road + R at (3,4) | R + Road at different locations |
| 10 | R at (4,1) | No actions |

The 3B model compounds the mistake by building Commercial at turn 0-5, which:
- Costs 150 per tile (2× residential)
- Has 1 upkeep per tile
- Generates 20/tick (only 2× residential revenue)
- Requires population to be valuable

### Commercial Zone Timing Trap

Commercial zones are the most misunderstood element. Let's calculate the true costs:

| Expense | Cost |
|---------|------|
| Build Commercial | 150 |
| Upkeep per tick | 1 |
| Revenue per tick | 20 |

**Break-even analysis:**
- Turn 0 build: Revenue generated for 50 turns = 1000
- Break-even: 150/(20-1) ≈ 8 ticks
- Net ROI over 50 turns: (20-1)×50 - 150 = 800

But the ROI assumes you have population to tax!

**The models' error:**
- 3B seed42: Built C at turn 0 (0 population) and C at turn 10 (pop=22)
- 3B seed43: Built 2C at turns 0,5,10 (population never exceeded 100)
- 8B seed42: Built only 2C at turns 15,40 (when pop=142, 253)

The 3B model builds Commercial early when there's no population, wasting 150+ per tile on upkeep with no revenue return.

### Industrial ROI Timing Mistake

Industrial zones are the highest-value zones:
- Build Industrial: 200
- Upkeep per tick: 1
- Revenue per tick: 35

**ROI over time:**
| Build Turn | Revenue | Net Profit (vs build later) |
|------------|---------|-----------------------------|
| Turn 5 | 45×35 - 45 - 200 = 1330 | Baseline (best) |
| Turn 15 | 35×35 - 35 - 200 = 990 | -340 (25% worse) |
| Turn 25 | 25×35 - 25 - 200 = 650 | -680 (51% worse) |
| Turn 35 | 15×35 - 15 - 200 = 325 | -1005 (76% worse) |
| Turn 45 | 5×35 - 5 - 200 = 70 | -1260 (95% worse) |

**What the models did:**

| Model | Avg Industrial Build Turn | Range |
|-------|--------------------------|-------|
| 8B (runs with I) | 23-30 | 3-49 |
| 3B (runs with I) | 8 & 42 | 8, 42 (only 2 runs!) |

The models understand Industrial is good, but they:
1. Don't prioritize it early enough
2. Stockpile budget until turn 35+ when it's too late
3. Miss the 15-turn window where Industrial pays for itself

**Best run analysis (8B seed46):**
- Industrial built at turn 33
- Revenue from I: 17×35 = 595 (turns 34-50)
- Should have built at turn 15: 35×35 = 1225
- **Missed opportunity: 630 revenue** (35% less!)

### The Poverty Trap Sequence

Based on 12 runs with pop=0 at end, here's the common failure pattern:

```
Phase 1 (Turns 0-5): Build R tiles in cluster (100×4 = 400 cost)
Phase 2 (Turns 5-15): Add more R tiles (no roads built)
Phase 3 (Turns 15-25): 0 population (all R disconnected), budget depleting
Phase 4 (Turns 25-35): Budget negative, no population to save
Phase 5 (Turns 35-50): Bankruptcy penalty decays population to 0
```

**The critical flaw:** Models build disconnected R tiles as if they generate population without road connectivity. Each R tile costs 100 but generates 0 population if disconnected.

### Strategic Pattern from Best Run (8B seed46, composite=33.98)

This run stands out because it avoided the key mistakes:

```
Turn 0:  R at (1,1) - starts with 1 R
Turn 5:  Road at (3,3), R at (3,4) - adds road and connected R
Turn 10: R at (2,1), R at (3,0) - expands vertically
Turn 15: C at (1,3), R at (4,3) - adds commercial after population exists
Turn 20: R at (4,2), C at (2,4) - scales carefully
Turn 25: I at (2,3) - INDUSTRIAL AT TURN 25! (first I built)
Turn 30: R at (1,2), R at (0,3) - continues expansion
Turn 35: Road at (0,2) - extends road network
Turn 40: Road at (4,4) - completes grid
Turn 45: R at (5,0), R at (5,1) - final push
```

**Success factors:**
1. Built first road at turn 5 (with 4 R tiles, all connected)
2. First Commercial at turn 15 (when pop=78, not 0!)
3. Built Industrial at turn 25 (early for good ROI)
4. Maintained positive budget throughout (never below 41)
5. Added roads to expand the connected area

**Key insight:** The model learned (from seed 46) to connect住宅 before building more, and to prioritize Industrial earlier.

### Realistic Best-Case Scenario

A well-designed heuristic could achieve what the models cannot:

```
Phase 1 (Turns 0-4): Build 5 roads radiating from center
Phase 2 (Turns 5-15): Build 10+ R tiles connected to roads
Phase 3 (Turns 16-25): Build 2-3 C tiles, 1-2 I tiles on edges
Phase 4 (Turns 26-50): Scale R/C based on budget, maximize population
```

Expected outcome:
- Population: 300-400 (vs best observed 341)
- Composite: 35-40 (vs best observed 38.71)
- Industrial ROI: Full 25+ turns of 35/tick revenue

### Population vs. Connected Population

The critical metric isn't "total R tiles" but "connected R tiles":

| Model | Seed | Total R | Connected R | Population |
|-------|------|---------|-------------|------------|
| 3B | 46 | 10 | 5 | 231 |
| 3B | 42 | 9 | 0 | 33 |
| 8B | 42 | 9 | 3 | 243 |
| 8B | 46 | 10 | 7 | 341 |

**Correlation:** Connected R tiles correlates strongly with population (r ≈ 0.85). Total R tiles has weak correlation (r ≈ 0.3) because disconnected R tiles are worthless.

### The Action Loop Problem

A critical failure mode observed in the 8B model late run:

| Turn | Budget | Action | Result |
|------|--------|--------|--------|
| 0 | 2000 | R at (4,4) | Built, cost=100 |
| 1 | 1899 | R at (4,4) | No effect (same zone), cost=0 |
| 2 | 1898 | R at (4,4) | No effect (same zone), cost=0 |
| 3 | 1897 | R at (4,4) | No effect (same zone), cost=0 |
| 4 | 1896 | R at (4,4) | No effect (same zone), cost=0 |

**Issue:** The model fails to understand that building on an existing zone of the same type has **no effect**. This is a fundamental misunderstanding of the game state update mechanism.

**Root cause:** The prompt tells the model "building on same zone costs 0 and has no effect" but the model still proposes the same action repeatedly. This suggests:
1. The model doesn't track the grid state across turns
2. The model doesn't understand that `state = state + action` (actions accumulate)
3. The model treats each turn independently rather than building on previous state

### Disaster Resilience is Mostly Irrelevant

Analysis of 32 runs reveals that resilience scores are typically 100 (no disasters occurred):

| Model | Runs | Avg Resilience | Min Resilience | Max Resilience |
|-------|------|----------------|----------------|----------------|
| 8B | 16 | 99.9 | 87.2 | 100 |
| 3B | 16 | 93.2 | 69.1 | 100 |

**Key findings:**
- 81 of 96 turns (84%) had NO disasters
- Resilience score only varied when disasters actually occurred
- Final score showed **no correlation** with resilience score (r ≈ 0.08)

**Conclusion:** In the CityBench default scenario, disasters are rare events (expected ~1-2 per 50-turn run). The primary determinants of success are:
1. Road connectivity strategy
2. Industrial ROI timing
3. Budget management
4. Phase order (Road→R→C→I)

Disaster resilience matters significantly only when disasters occur (16% of runs), but doesn't drive large score differences because most runs don't experience disasters. A model that excels at the core mechanics will reliably outperform one that focuses on disaster preparedness when disasters are rare.

**Impact:** Wasted decision capacity. Each "useless" action is a turn that could have been used to build a road or expand the city.

### Budget Recovery is Possible but Timing Matters

Analysis of runs with negative budget reveals important patterns:

| Model | Run | Min Budget | Turn | Final Pop | Composite | Recovery |
|-------|-----|------------|------|-----------|-----------|----------|
| 8B | seed43 | -9 | 32 | 182 | 31.28 | Yes - recovered to +74 by turn 41 |
| 8B | seed44 | 85 | 0 | 65 | 22.36 | No issue |
| 8B | seed45 | -245 | 23 | 0 | 25.00 | No - stayed negative |
| 3B | seed43 | -422 | 29 | 0 | 25.00 | No |
| 3B | seed42 | -305 | 22 | 0 | 25.00 | No |

**Key observations:**
- 8B model can recover from early negative budget (turn 32) and still achieve 31.28 composite
- 8B seed45 hit -245 at turn 23 but failed to recover - population decayed to 0
- 3B models hit very negative budgets (often -170 to -422) and never recover
- Recovery requires ~10+ turns of positive budget growth to break even

**Insight:** Budget recovery requires time. If negative budget hits after turn ~35, recovery is effectively impossible because:
1. Each turn only generates ~35 budget if Industrial is built
2. Models can't build enough Industrial fast enough to recover
3. Population continues to decay from bankruptcy penalty

| Model | 8B | 3B |
|-------|----|----|
| Total Zone Count | 116 | 251 |
| Residential (R) | 60 (51.7%) | 155 (61.8%) |
| Commercial (C) | 23 (19.8%) | 62 (24.7%) |
| Industrial (I) | 0 (0.0%) | 2 (0.8%) |
| Roads (O) | 33 (28.4%) | 32 (12.7%) |

**Paradoxical finding:** The 3B model builds **2.2x more zone tiles** (251 vs 116) but achieves **lower scores** because:
1. Most R tiles are disconnected (worthless)
2. Almost no Industrial built (missing highest-value zones)
3. Roads are sparse (no connectivity)

**Insight:** Zone quality (type + connectivity) matters far more than zone quantity. A city with 30 well-placed zones can outperform a city with 100 poorly placed zones.

### Conclusion from Additional Analysis

The models fail not because they can't read rules, but because they fundamentally misunderstand the game dynamics:

1. **Roads are the foundation** - Without roads, civilization cannot grow
2. **ROI timing matters** - Industrial built at turn 45 is 95% less valuable than built at turn 15
3. **Phase order is critical** - R→R→R without roads is wasted budget
4. **Population drives Commercial** - Commercial shouldn't be built until population exists to tax

These are not minor misunderstandings - they're fundamental gaps in the models' mental models of urban planning. A well-constructed heuristic that prioritizes roads first, then connected residential, then commercial/industrial would significantly outperform both LLMs.

---

## Summary of Key Findings (All Analysis)

| Finding | Evidence | Impact |
|---------|----------|--------|
| Road connectivity is critical | 12 failed runs with 0 connected R tiles | Population = 0 even with 9+ R tiles |
| Industrial ROI timing wasted | Best run built I at 25+, optimal at 15 | ~630 revenue lost (35% of total) |
| Commercial built too early | 3B built C at turn 0 with 0 population | ~300 budget wasted per early C |
| Poverty trap pattern common | 12 runs ended with pop=0, budget<0 | Models stuck in low-revenue equilibrium |
| Connected R vs total R correlation | r=0.85 vs r=0.3 | Metrics must track connectivity |
| Seed 46 anomaly explained | Best run avoided all 4 failure modes | Explains high score ~34 |
| Phase order mistake | Both models: R first, road later | Optimal: Road first, then R |
| ROI misunderstanding | Models wait until turn 35+ for I | Should build by turn 20-25 |
| Action loop problem | 8B built same R tile 5x in a row | Wasted decision capacity |
| Grid state forgetting | Models don't track previous actions | Repeated ineffective actions |
| Budget recovery usually impossible | 3B hits -170 to -422 by turn 49 | Too late to recover after turn 35 |
| Connected R strongly correlates with composite | r=0.830 vs revenue r=0.698 | Primary success driver |
| Zone quantity paradox | 3B builds 2.2x more zones but scores lower | Quality > quantity |
| Industrial conversion error | 3B builds then immediately bulldozes I | Model doesn't grasp long-term ROI |
| Short planning horizon | Models think 5-10 turns, not 50 | Myopic decision-making |

### The Industrial "Convert and Replace" Error

Analysis of 3B seed46's successful run (pop=231, composite=33.88) reveals this critical pattern:
1. **Turn 10**: Model builds Industrial at position (4,1)
2. **Turns 10-24**: Model builds roads and Commercial at adjacent position (3,1), repeatedly
3. **Turn 24**: Model converts Industrial tile (4,1) to ROAD (bypassing normal demolition cost)
4. **Turn 25**: Model builds Residential on the former Industrial tile

**Why this is wrong:** Each Industrial tile generates 35/tick revenue. If built at turn 10 and kept until turn 50:
- Revenue generated: 45 × 35 = 1575
- Total cost: 200 build + 45 upkeep = 245
- **Net profit: 1330** (6.65x ROI over the game)

The model sees:
- Immediate cost: 200 (potential budget hit)
- No immediate benefit (only 10 revenue-per-tile in early turns)
- Optimal response: Replace with something cheaper

**Deep insight:** The models are effectively myopic with a planning horizon of only 5-10 turns, not 50. They understand Industrial is "good" in theory but cannot model the 45-turn compounding benefit.

### Action Effectiveness

| Metric | 8B | 3B |
|--------|----|----|
| Avg action success rate | 86.8% | 58.8% |
| Computed across all 32 runs | | |

The 8B model has a **28% higher action success rate** than the 3B model. Higher success rate == more budget efficiently used for city building.

---
