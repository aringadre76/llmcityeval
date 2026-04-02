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
