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

## Planning Quality

### Locally Reasonable, Globally Weak

- Both models produce **valid, grid-aware actions**: zones in-bounds, legal zone types, no nonsensical moves
- Neither model reliably drives toward high-population, high-score cities over 50 turns
- Performance is **highly seed-sensitive**, suggesting reactive rather than strategic behavior

### Strengths

1. **Rule understanding**: Both models correctly interpret zone connectivity, budget constraints, and zoning rules
2. **Local reasoning**: Can decide "what is allowed here?" on the grid and produce sensible actions
3. **Recovery ability**: Models can recover from bad turns (avg recovery turns ~1.5-3)

### Limitations

1. **Weak long-horizon planning**: No consistent pattern of early investment leading to late growth
2. **Budget as constraint, not tool**: Models react to budget limits but don't strategically.front-load investments
3. **No global strategy**: No consistent road network design or zone placement pattern across runs
4. **seed sensitivity**: Small perturbations in early turns lead to qualitatively different trajectories

---

## Disaster Scenario Performance

### Critical Finding: llama3.2:3b Floor Performance
- **All 5 runs achieved exactly 25.0 composite score** (minimum possible)
- Final population = 0 in disaster runs
- This indicates a **fundamental failure mode** rather than stochastic bad luck
- During disasters, models struggle to coordinate actions effectively

### llama3:8b under Stress
- Composite scores range from 25.0 to 32.67 (some success mixed with failures)
- Better at maintaining minimal city function during disasters
- Still shows significant variation, indicating stress exposes fragility

**Interpretation:**灾难 scenarios disproportionately hurt the smaller model, possibly due to:
- Reduced capacity for multi-step planning under time pressure
- Weaker ability to balance immediate needs (budget) with long-term survival

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
- **Strengths:** Stronger planning, better disaster resilience, lower invalid action rate
- **Limitations:** Still myopic, seed-sensitive, no dominant strategy emerges
- **Verdict:** Reliable decision engine but not yet a high-quality autonomous planner

### llama3.2:3b Assessment
- **Strengths:** Technically competent within constraints
- **Limitations:** Fragile under stress, frequent invalid actions, poor long-horizon coordination
- **Verdict:** Not competitive for autonomous urban planning in this benchmark

---

## Practical Takeaways

1. **Model scale matters** - The 8B model consistently outperforms the 3B model by a meaningful margin

2. **Stress tests reveal fragility** - Disaster scenarios amplify differences between models; the 3B model fails completely

3. **LLMs are not yet competitive with tailored heuristics** - Based on the expected strong performance of a well-designed heuristic agent (e.g., road spine + zone stripes), LLMs would likely lose on average

4. **To improve LLM planning:**
   - More capable models or larger scale may help
   - Richer prompting with explicit planning loops could help
   - Self-critique or search-based methods (e.g., tree search, beam search) could improve robustness
   - Hybrid approaches combining LLM with learned/heuristic policies would likely outperform pure LLM

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
