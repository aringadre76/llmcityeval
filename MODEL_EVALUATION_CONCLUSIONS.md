# CityBench: Model Evaluation Conclusions

Conclusions from running the CityBench benchmark with **llama3:8b** (Ollama) across smoke, full 50-turn, and multi-seed 30-turn runs: reliability, planning quality, and suitability as an autonomous urban planner.

---

## Reliability and robustness

- **Protocol and constraint adherence are strong.** The model produced no invalid JSON, out-of-bounds actions, or invalid zone types in the runs executed. Rejections were limited to `insufficient_budget` when it proposed more spend than available in a single turn.
- **Pipeline stability.** Repeated calls over many turns and multiple seeds completed without HTTP/JSON failures or crashes, indicating that the model is a reliable, predictable decision engine in this setting.

---

## Planning quality

### Locally reasonable, globally weak

- The model consistently produces **valid, grid-aware actions**: roads and zones in-bounds, legal zone types, no nonsensical moves.
- Over 30–50 turns it **does not reliably drive toward high-population, high-score cities**. Composite scores cluster in a mediocre band (mid-20s to low-30s), with only occasional better seeds.

### Shallow strategy / weak long-horizon planning

- The model learns that building roads and zoning tiles is good, but **does not appear to follow a strong global strategy** (e.g., robust road networks, clear separation of industrial vs residential, systematic densification).
- Performance varies substantially by seed, suggesting **myopic reaction to the current state** rather than a stable long-term plan that is robust to stochastic differences.

### Budget and constraints: “safe but not smart”

- The model **respects constraints** (no illegal zones or geometry; only `insufficient_budget` rejections), so its representation of the rules is solid.
- It **does not appear to use budget as a strategic resource** (e.g., investing early to unlock later growth). Sporadic overspend attempts and no clear “invest now, harvest later” pattern.

### Seed sensitivity exposes policy fragility

- Some seeds achieve modest growth and okay composites; others stagnate near baseline despite the same environment and rules.
- This indicates a **brittle policy**: small perturbations in early turns can lead to qualitatively different, often worse, trajectories.

---

## Overall conclusions about the LLM

### Strengths

- **Strong protocol-following:** JSON output, schema adherence, and rule compliance are very reliable in this benchmark.
- **Good local reasoning:** The model can interpret “what is allowed here?” on the grid and produce sensible, constrained actions turn after turn.

### Limitations exposed by CityBench

- **Weak long-horizon credit assignment:** The model struggles to connect early zoning and road decisions with later population and score outcomes, leading to middling city outcomes.
- **Lack of strategic consistency:** It does not reliably converge to a single strong urban-planning pattern across seeds; behavior is sensitive to initial conditions.
- **Not yet competitive with tailored policy:** A well-designed heuristic agent built for this sim would likely outperform the model’s average behavior, especially on worst-case seeds.

### Practical takeaway

- **llama3:8b** is **reliable as a constrained decision engine** (it will not break the sim or violate the protocol) but **not yet a high-quality autonomous planner** on this benchmark.
- To get strong planning results would likely require: a more capable model, richer prompting or scaffolding (e.g., search/planning loops, self-critique, tool-augmented planning), or a hybrid that combines the LLM with learned or heuristic planning policies rather than a single forward pass per turn.

---

## Scope of these conclusions

- These conclusions apply to **llama3:8b** in the **CityBench** setting (grid size, turn limit, disaster and economic parameters as configured). Generalization to other models, benchmarks, or domains would require additional evaluation.
- The benchmark and runs that support this report are documented in [PROGRESS.md](PROGRESS.md) and [testing.md](testing.md).
