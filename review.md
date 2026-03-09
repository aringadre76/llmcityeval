## Overall summary

- **Baseline agents have been significantly strengthened**: the new budget- and connectivity-aware heuristic and random agents are structured, deterministic, and well-covered by tests, improving the quality of non-LLM baselines.
- **Experiment wiring and metrics outputs are coherent with docs**: the `citybench_v1` matrix, experiment runner, and metrics artifacts line up with the usage described in `README.md` and `testing.md`.
- **A few subtle correctness and robustness risks remain**: notably around handling jagged grids in connectivity utilities, more aggressive validation of model output/zone costs, and limited testing of some edge cases and experiment failure modes.

---

## Per-file comments

### `README.md`

- **Clarity / consistency (L7–L18, L68–L152)**  
  - The additions describing experiments (`experiments_cli`, metrics files, and artifacts) are consistent with the actual paths and filenames in `benchmark/experiment_runner.py`, `experiments/citybench_v1/config/matrix.yaml`, and the metrics outputs.  
  - The baseline descriptions at L154–L161 correctly reflect the new agents: `random_baseline` and `heuristic_baseline` both exist and are wired via `agent_type` in the matrix.
- **Minor doc gap**  
  - The README calls out `experiments/citybench_v1/config/metrics.yaml` but that file is not part of this diff; ensure it exists and stays in sync with how metrics are actually computed/aggregated.

**Overall rating**: ✅ Clear and accurate; only minor cross-reference maintenance needed.

---

### `testing.md`

- **Experiment workflow docs (L40–L90)**  
  - The document accurately describes the `benchmark.experiments_cli` workflow, including `run`, `aggregate`, and `upload` commands, and the generated artifacts under `experiments/citybench_v1`. This matches the current behavior of `benchmark/experiment_runner.py` and the metrics files in this diff.
- **Coverage description (L172–L181)**  
  - The narrative claims coverage for “runtime scenario config injection, scenario override application, resumable and filtered experiment execution, experiment CLI/upload behavior, per-run metric extraction, aggregation summaries, baseline agents, and experiment runner behavior.” This generally aligns with the current test suite, but there are still a few untested edge cases (see “Potential bugs and test gaps”).

**Overall rating**: ✅ Good high-level documentation; keep in sync as experiments grow more complex.

---

### `agents/utils.py`

```12:79:agents/utils.py
def get_connectivity_info(state: CityState) -> dict[str, int | list[tuple[int, int]]]:
    height = len(state.grid)
    if height == 0:
        return {
            "empty_with_road": [],
            "empty_without_road": [],
            "connected_residential": 0,
            "connected_commercial": 0,
            "connected_industrial": 0,
            "total_empty": 0,
        }
    # Compute width per row to handle jagged grids safely
    width = max(len(row) for row in state.grid)

    ...

    for y in range(height):
        row_width = len(state.grid[y])
        for x in range(row_width):
            tile = state.grid[y][x]
            if tile.zone == ZONE_EMPTY:
                ...
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        neighbor = state.grid[ny][nx]
                        if neighbor.zone == ZONE_ROAD and not neighbor.disabled:
                            has_road_neighbor = True
                            break
```

- **Potential jagged-grid bug (L23–L25, L32–L43)**  
  - You compute a global `width = max(len(row) for row in state.grid)` but use it in the neighbor bounds check for all rows. If the grid is ever jagged (some rows shorter than `width`), the check `0 <= nx < width` can allow an index `nx` that is valid for the maximum-width row but out of range for the current row `ny`, leading to a possible `IndexError`.  
  - The comment “Compute width per row to handle jagged grids safely” suggests the intent was safety, but the current implementation still assumes rectangularity when reading neighbors.
  - **Recommendation**: Either (a) enforce rectangular grids and remove the “jagged” implication, or (b) make the neighbor check row-specific, e.g.:
    - Check `0 <= ny < height` first, then `0 <= nx < len(state.grid[ny])` before indexing.
    - Alternatively, derive `row_width` for the neighbor row instead of using a global `width`.

- **Return contract / typing (L59–L66)**  
  - The dictionary mixes `list[tuple[int, int]]` and `int` values behind `dict[str, int | list[tuple[int, int]]]`, which is fine but loosely typed. The exported helpers are heavily used by agents; consider introducing a `TypedDict` or dataclass to make consumer code less error-prone.

```69:79:agents/utils.py
def get_zone_cost(zone: str) -> int:
    if zone == ZONE_ROAD:
        return COST_ROAD
    if zone == ZONE_RESIDENTIAL:
        return COST_RESIDENTIAL
    if zone == ZONE_COMMERCIAL:
        return COST_COMMERCIAL
    if zone == ZONE_INDUSTRIAL:
        return COST_INDUSTRIAL
    return 0
```

- **Silent fallback for unknown zones (L69–L78)**  
  - Returning `0` for unknown zones is permissive but could hide misconfigurations or model-output errors. In practice, `VALID_ZONES` is used elsewhere to guard zone values, but tying `get_zone_cost`’s behavior more explicitly to `VALID_ZONES` would be safer.
  - **Recommendation**: Either:
    - Raise a `ValueError` for invalid zones (and adapt callers/tests), or  
    - Log a warning for unexpected zones, or  
    - Explicitly document that `0` is a sentinel “unknown zone” value and ensure call sites test `> 0` rather than assuming any int is valid.

**Overall rating**: ⚠️ Correct on rectangular grids but fragile on jagged grids; cost helper could be stricter.

---

### `agents/random_agent.py`

```1:75:agents/random_agent.py
class RandomAgent(BaseAgent):
    ...
    def decide(self, state: CityState) -> list[Action]:
        grid_size = len(state.grid)
        if grid_size <= 0:
            return []
        action_count = self._rng.randint(1, 5)
        ...


class BudgetAwareRandomAgent(BaseAgent):
    ...
    def decide(self, state: CityState) -> list[Action]:
        grid_size = len(state.grid)
        if grid_size <= 0:
            return []
        ...
        for _ in range(max_actions):
            if remaining_budget <= 0:
                break
            ...
            cost = get_zone_cost(zone)

            if remaining_budget >= cost:
                actions.append(Action(type="zone", x=x, y=y, zone=zone))
                remaining_budget -= cost
```

- **Correctness / budget handling**  
  - The budget-aware logic is straightforward and respects the current `remaining_budget`, with a clean early-exit when budget is exhausted.  
  - The number of actions is bounded by both a random upper cap (`1–5`) and effective budget, which is also validated by `tests/test_baseline_agents.py`.

```78:141:agents/random_agent.py
class ConnectivityAwareRandomAgent(BaseAgent):
    ...
    def decide(self, state: CityState) -> list[Action]:
        if len(state.grid) <= 0:
            return []

        remaining_budget = state.budget
        zones = (ZONE_RESIDENTIAL, ZONE_COMMERCIAL, ZONE_INDUSTRIAL, ZONE_ROAD)
        actions: list[Action] = []
        targeted_tiles: set[tuple[int, int]] = set()
        connectivity = get_connectivity_info(state)
        empty_with_road = connectivity["empty_with_road"]
        empty_without_road = connectivity["empty_without_road"]

        for _ in range(self._rng.randint(1, 5)):
            if remaining_budget <= 0:
                break

            empty_with_road = [
                tile for tile in empty_with_road if tile not in targeted_tiles
            ]
            empty_without_road = [
                tile for tile in empty_without_road if tile not in targeted_tiles
            ]
            all_empty = empty_with_road + empty_without_road
            ...
```

- **Clarity: in-place filtering of `empty_with_road` (L103–L108)**  
  - Reassigning `empty_with_road` and `empty_without_road` inside the loop is logically fine and avoids retargeting tiles within a single decide call, but it slightly obscures the origin of these lists (they start as `connectivity[...]` values).  
  - **Suggestion**: Introduce explicit “working” lists:
    - `remaining_empty_with_road`, `remaining_empty_without_road` initialized from connectivity before the loop, then mutate those in the loop. This reads more clearly and avoids confusion between the original connectivity data and the filtered working sets.

- **Budget and zone selection (L114–L135)**  
  - The logic around `_MIN_ZONE_COST` and `COST_ROAD` is sound: when no zones are affordable but roads are, the agent preferentially builds roads adjacent to existing roads; otherwise it chooses between connected and unconnected empties with a 0.7 bias toward connected tiles.  
  - `affordable_zones` is recomputed per-iteration based on `remaining_budget`, which correctly prevents overspending.

**Overall rating**: ✅ Correct and robust for rectangular grids; minor readability improvements possible.

---

### `agents/heuristic_agent.py`

```17:47:agents/heuristic_agent.py
_ZONE_PRIORITY = (ZONE_RESIDENTIAL, ZONE_COMMERCIAL, ZONE_INDUSTRIAL)


def _road_spine_x(grid_size: int) -> int:
    return min(1, grid_size - 1)
...
def _fill_connected_tiles(
    actions: list[Action],
    targeted_tiles: set[tuple[int, int]],
    remaining_budget: float,
    candidate_tiles: list[tuple[int, int]],
    zone_priority: list[str] | tuple[str, ...],
    max_actions: int,
) -> float:
    for x, y in candidate_tiles:
        if len(actions) >= max_actions:
            break
        for zone in zone_priority:
            updated_budget = _add_action(
                actions,
                targeted_tiles,
                remaining_budget,
                x,
                y,
                zone,
            )
            if updated_budget != remaining_budget:
                remaining_budget = updated_budget
                break
    return remaining_budget
```

- **Design / reuse**  
  - The shared helpers `_available_connected_tiles`, `_add_action`, and `_fill_connected_tiles` significantly reduce duplication across the three heuristic agents, and they’re covered by tests indirectly.
  - `_road_spine_x`’s use of `min(1, grid_size - 1)` behaves well for grid sizes of 1 (x=0) and ≥2 (x=1), aligning with tests expecting the spine at `x == 1` for the default grid.

```75:141:agents/heuristic_agent.py
class BudgetAwareHeuristicAgent(BaseAgent):
    def __init__(
        self,
        seed: int = 0,
        name: str = "budget_aware_baseline",
    ) -> None:
        super().__init__(name=name)
        self._rng = Random(seed)

    def decide(self, state: CityState) -> list[Action]:
        ...
        max_actions = min(5, len(state.grid))
        connectivity = get_connectivity_info(state)

        if turn < 6:
            ...
        elif turn < 11:
            ...
        elif turn < 26 and connectivity["empty_with_road"]:
            ...
        elif connectivity["empty_with_road"]:
            zone_options = list(_ZONE_PRIORITY)
            self._rng.shuffle(zone_options)
            remaining_budget = _fill_connected_tiles(
                ...,
            )
        return actions
```

- **Correctness / backward compatibility**  
  - The constructor now has a default `seed: int = 0`, which matches tests that call `HeuristicAgent()` with no seed and the alias `HeuristicAgent = BudgetAwareHeuristicAgent`.  
  - The phased strategy (early road spine, then alternative spine, then connected fill with or without shuffle) is simple and deterministic; budget handling is consistently delegated through `_add_action` and `_fill_connected_tiles`, so budget overruns are unlikely.

```144:249:agents/heuristic_agent.py
class ConnectivityAwareHeuristicAgent(BaseAgent):
    ...
    def decide(self, state: CityState) -> list[Action]:
        ...
        if turn < 6:
            ...
        elif turn < 21 and connectivity["empty_with_road"]:
            candidate_tiles = _available_connected_tiles(connectivity, targeted_tiles)
            self._rng.shuffle(candidate_tiles)
            for x, y in candidate_tiles:
                if len(actions) >= max_actions:
                    break
                updated_budget = _add_action(..., ZONE_ROAD)
                if updated_budget != remaining_budget:
                    remaining_budget = updated_budget
                    continue
                remaining_budget = _add_action(..., ZONE_RESIDENTIAL)
        elif turn < 36 and connectivity["empty_with_road"]:
            zone_priority = list(_ZONE_PRIORITY)
            self._rng.shuffle(zone_priority)
            remaining_budget = _fill_connected_tiles(...)
        elif turn < 40 and connectivity["empty_with_road"]:
            ...
        elif connectivity["empty_with_road"]:
            ...
        return actions
```

- **Correctness**  
  - The agent cleanly prefers roads in mid-game when affordable, otherwise falls back to residential, and later phases use shuffled zone priorities.  
  - `targeted_tiles` prevents multiple actions on the same tile within a single call, and budget is updated on every `_add_action` that succeeds.

```252:350:agents/heuristic_agent.py
class HybridBudgetConnectivityAgent(BaseAgent):
    ...
    def decide(self, state: CityState) -> list[Action]:
        ...
        elif turn < 31 and connectivity["empty_with_road"]:
            scored_tiles: list[tuple[float, int, int, str]] = []

            candidate_tiles = _available_connected_tiles(connectivity, targeted_tiles)
            for x, y in candidate_tiles:
                base_score = 1.0
                if turn < 20:
                    base_score = 1.5

                best_zone = None
                best_cost = float("inf")
                for zone in _ZONE_PRIORITY:
                    cost = get_zone_cost(zone)
                    if remaining_budget >= cost and cost < best_cost:
                        best_zone = zone
                        best_cost = cost

                if best_zone:
                    score = base_score * (100 / best_cost)
                    scored_tiles.append((score, x, y, best_zone))

            scored_tiles = nlargest(max_actions, scored_tiles, key=lambda t: t[0])

            for _, x, y, zone in scored_tiles:
                if len(actions) >= max_actions:
                    break
                cost = get_zone_cost(zone)
                if remaining_budget >= cost:
                    actions.append(Action(type="zone", x=x, y=y, zone=zone))
                    targeted_tiles.add((x, y))
                    remaining_budget -= cost
```

- **Correctness / budget handling**  
  - The selection logic uses `remaining_budget` at the time of scoring, which could mean some tiles become unaffordable after earlier picks. However, the second loop rechecks `remaining_budget >= cost` and only applies actions when affordable, updating `remaining_budget` per action. This is safe and prevents overspending.
- **Potential improvement: stronger influence of connectivity metrics**  
  - Currently, the score only depends on `base_score` and `1 / cost`. If you intend this to be “connectivity-aware,” consider incorporating `connectivity` features (e.g., number of connected residential tiles nearby) into the scoring function.
- **Readability**  
  - The scoring logic is more complex than the other agents but still manageable. A named helper (e.g., `_score_candidate_tile`) could make the intent clearer, especially if more heuristics are added later.

**Overall rating**: ✅ Well-structured and reasonably tested; only minor potential enhancements and clarifications.

---

### `agents/__init__.py`

```1:16:agents/__init__.py
from agents.base import BaseAgent as BaseAgent
from agents.heuristic_agent import (
    BudgetAwareHeuristicAgent as BudgetAwareHeuristicAgent,
    ConnectivityAwareHeuristicAgent as ConnectivityAwareHeuristicAgent,
    HeuristicAgent as HeuristicAgent,
    HybridBudgetConnectivityAgent as HybridBudgetConnectivityAgent,
)
from agents.ollama import OllamaAgent as OllamaAgent
from agents.random_agent import (
    BudgetAwareRandomAgent as BudgetAwareRandomAgent,
    ConnectivityAwareRandomAgent as ConnectivityAwareRandomAgent,
    RandomAgent as RandomAgent,
)
from agents.utils import get_connectivity_info as get_connectivity_info
from agents.utils import get_zone_cost as get_zone_cost
```

- **Pattern / ergonomics**  
  - This makes the `agents` package a convenient, curated surface (re-exporting BaseAgent, all baseline agents, and the key utilities). It is consistent with typical Python package practices.  
  - The explicit `as` imports keep the public API clear while avoiding accidental exposure of internals.

**Overall rating**: ✅ Simple and effective aggregation module.

---

### `agents/ollama.py`

```20:41:agents/ollama.py
def _agent_debug_log(hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
    """Append a single NDJSON debug log line for this debug session."""
    try:
        payload: dict[str, Any] = {
            "sessionId": "160aa6",
            "id": f"log_{int(time.time() * 1000)}_{hypothesis_id}",
            "timestamp": int(time.time() * 1000),
            "location": location,
            "message": message,
            "data": data,
            "runId": "pre-fix-1",
            "hypothesisId": hypothesis_id,
        }
        log_path = Path(__file__).resolve().parents[1] / ".cursor" / "debug-160aa6.log"
        ...
    except Exception:
        # Debug logging must never interfere with the main flow.
        pass
```

- **Robustness / observability**  
  - The debug logging helper is robust against failures and correctly treated as non-critical. The hard-coded session/run IDs are fine for local instrumentation but might be worth parameterizing if you expect multiple sessions or tools to use the same logger.

```99:156:agents/ollama.py
class OllamaAgent(BaseAgent):
    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        super().__init__(name=model)
        self.model = model
        self.last_raw_response = ""
        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "system.txt"
        self.system_prompt = prompt_path.read_text(encoding="utf-8")

    def decide(self, state: CityState) -> list[Action]:
        self.last_parse_success = True
        try:
            state_payload = asdict(state)
            raw_outcomes = state_payload.pop("last_action_outcomes", [])
            last_action_outcomes = (
                raw_outcomes
                if isinstance(raw_outcomes, list)
                else []
            )
            # region agent log
            _agent_debug_log(
                "H2",
                "agents/ollama.py:OllamaAgent.decide",
                "Preparing Ollama call",
                {
                    "model": self.model,
                    "budget": state_payload.get("budget"),
                    "population": state_payload.get("population"),
                    "turn": state_payload.get("turn"),
                    "last_action_outcomes_count": len(last_action_outcomes),
                },
            )
            ...
            payload = {
                "model": self.model,
                "prompt": (
                    f"{self.system_prompt}\n\n"
                    f"{feedback_section}"
                    f"{json.dumps(state_payload, separators=(',', ':'))}"
                ),
                "stream": False,
            }
            response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
            ...
            model_text = response_payload.get("response", "")
            self.last_raw_response = str(model_text)
        except requests.RequestException as exc:
            ...
        except (ValueError, TypeError) as exc:
            ...
```

- **Correctness / robustness**  
  - All network and JSON parsing errors from the Ollama endpoint are caught, logged, and result in an empty action list, which is appropriate for a planner: the sim can treat “no actions” as a safe fallback.  
  - `last_parse_success` is updated in all failure paths, and truncated logging of raw responses uses the configured `LOG_RAW_RESPONSE_MAX_CHARS`.
- **Minor logging mismatch**  
  - The debug data uses `"turn": state_payload.get("turn")`, but the `CityState` dataclass elsewhere in the codebase uses `tick` as the turn field. This is a harmless null entry but could be confusing when analyzing logs.

```189:231:agents/ollama.py
        extracted = _extract_first_json_object(self.last_raw_response)
        if extracted is None:
            self.last_parse_success = False
            logger.error(
                "Failed to extract JSON object from model output: %s",
                self.last_raw_response[:LOG_RAW_RESPONSE_MAX_CHARS],
            )
            return []

        try:
            data = json.loads(extracted)
        except json.JSONDecodeError:
            self.last_parse_success = False
            logger.error(
                "Failed to parse model JSON output: %s",
                self.last_raw_response[:LOG_RAW_RESPONSE_MAX_CHARS],
            )
            return []

        return self._parse_actions(data)
```

- **Performance / resilience**  
  - `_extract_first_json_object` is a reasonable streaming-safe parser for language-model-esque text. It avoids quadratic behavior and correctly handles nested braces and strings.  
  - The approach is defensive enough for typical LM responses, but extremely long outputs could still incur overhead; that’s mitigated by the `LOG_RAW_RESPONSE_MAX_CHARS` truncation in logs.

```210:231:agents/ollama.py
    def _parse_actions(self, data: dict[str, Any]) -> list[Action]:
        raw_actions = data.get("actions")
        if not isinstance(raw_actions, list):
            self.last_parse_success = False
            logger.error("Model JSON missing list field 'actions'.")
            return []

        parsed: list[Action] = []
        for item in raw_actions:
            if not isinstance(item, dict):
                continue
            try:
                action_type = str(item["type"])
                x = int(item["x"])
                y = int(item["y"])
                zone = str(item["zone"])
            except (KeyError, TypeError, ValueError):
                continue
            if zone not in VALID_ZONES:
                continue
            parsed.append(Action(type=action_type, x=x, y=y, zone=zone))
        return parsed
```

- **Correctness / validation**  
  - The parser rejects any entries missing required fields or with invalid types, and it also ensures `zone` is in `VALID_ZONES`. That’s a solid safety net.  
  - There’s no hard cap on action count here; the cap is presumably enforced by the simulator (`MAX_ACTIONS_PER_TURN`). This is fine from an agent perspective, but see “Test gaps” for potential coverage to ensure the cap is always respected.

**Overall rating**: ✅ Robust and defensive LLM integration; only minor logging field naming and potential configurability improvements.

---

### `benchmark/experiment_runner.py`

```1:76:benchmark/experiment_runner.py
from agents.heuristic_agent import HeuristicAgent
from agents.ollama import OllamaAgent
from agents.random_agent import RandomAgent
from benchmark.runner import run as run_benchmark
from sim.runtime_config import SimConfig
ROOT = Path(__file__).resolve().parents[1]
...
def load_matrix(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def find_result_for_run(agent: str, seed: int, results_dir: Path = None) -> Path | None:
    results_dir = results_dir or (ROOT / "results")
    safe = _safe_agent_name(agent)
    candidates = sorted(results_dir.glob(f"{safe}_{seed}_*.json"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        return None
    return candidates[-1]
```

- **Correctness**  
  - `find_result_for_run` is robust against missing files and relies on sorted modification times to pick the latest result; this is simple and effective for a single-writer workflow.  
  - `load_matrix` uses `yaml.safe_load` with explicit UTF-8 encoding, which is correct and safe.

```79:147:benchmark/experiment_runner.py
def _load_completed_runs(index_path: Path) -> set[tuple[str, int, str]]:
    if not index_path.exists():
        return set()

    completed: set[tuple[str, int, str]] = set()
    with index_path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            result_path = row.get("result_path", "")
            if not result_path:
                continue
            completed.add((str(row.get("model", "")), int(row.get("seed", 0)), str(row.get("scenario", ""))))
    return completed
```

- **Robustness**  
  - The loader tolerates partially populated rows and skips ones without `result_path`. This pairs well with the `resume` flag semantics.

```121:212:benchmark/experiment_runner.py
def run_experiment(
    matrix_path: str | Path,
    experiment_name: str = "citybench_v1",
    turns: int = 50,
    results_dir: str | Path | None = None,
    model_filter: set[str] | None = None,
    seed_filter: set[int] | None = None,
    scenario_filter: set[str] | None = None,
    resume: bool = False,
):
    ...
    completed_runs = _load_completed_runs(index_path) if resume else set()

    for model_entry in models:
        model = str(model_entry["id"])
        agent_type = str(model_entry.get("agent_type", "ollama"))
        if model_filter is not None and model not in model_filter:
            continue
        for seed in seeds:
            if seed_filter is not None and seed not in seed_filter:
                continue
            for scenario in scenarios:
                scenario_id = scenario.get("id", "default")
                if scenario_filter is not None and scenario_id not in scenario_filter:
                    continue
                if (model, int(seed), scenario_id) in completed_runs:
                    print(f"Skipping completed run model={model} seed={seed} scenario={scenario_id}")
                    continue
                print(f"Running model={model} seed={seed} scenario={scenario_id}")
                sim_config = build_sim_config_for_scenario(base_config, scenario)
                if agent_type == "random":
                    agent = RandomAgent(seed=int(seed))
                elif agent_type == "heuristic":
                    agent = HeuristicAgent()
                else:
                    agent = OllamaAgent(model=model)
                ...
                run_benchmark(
                    agent=agent,
                    seed=seed,
                    turns=turns,
                    results_dir=str(results_dir_path),
                    sim_config=sim_config,
                )
                ...
                result = find_result_for_run(model, seed, results_dir=results_dir_path)
                run_id = f"{experiment_name}_{_safe_agent_name(model)}_seed{seed}_{scenario_id}"
                with index_path.open("a", newline="", encoding="utf-8") as fh:
                    writer = csv.writer(fh)
                    writer.writerow([run_id, model, seed, scenario_id, str(result) if result else ""])
                print(f"Recorded run {run_id} -> {result}")
```

- **Correctness / wiring**  
  - The mapping from `agent_type` to concrete agent class (`random` → `RandomAgent`, `heuristic` → `HeuristicAgent`, else → `OllamaAgent`) is clean and aligns with `experiments/citybench_v1/config/matrix.yaml`.  
  - `SimConfig.from_module()` plus `build_sim_config_for_scenario` ensures scenario overrides stay runtime-only and don’t mutate global config, aligning with docs.
- **Potential behavior caveat**  
  - `find_result_for_run` is called *after* `run_benchmark`, presumably when exactly one new result exists per run. If multiple result files with the same agent and seed are created by other tooling, the “latest mtime” heuristic could pick an unintended file. For the current workflow this is acceptable, but worth noting in docs if you later add concurrent or re-run behaviors.

**Overall rating**: ✅ Solid and readable experiments runner with correct resume/filter semantics.

---

### `experiments/citybench_v1/config/matrix.yaml`

```1:39:experiments/citybench_v1/config/matrix.yaml
name: citybench_v1
baseline_model: llama3:8b
...
models:
  - id: llama3:8b
    label: LLaMA 3 8B
    agent_type: ollama
  - id: llama3:70b
    label: LLaMA 3 70B
    agent_type: ollama
  - id: qwen2.5-coder:7b
    label: Qwen2.5 Coder 7B
    agent_type: ollama
  - id: random_baseline
    label: Random Baseline
    agent_type: random
  - id: heuristic_baseline
    label: Heuristic Baseline
    agent_type: heuristic

seeds: [42, 43, 44, 45, 46]

scenarios:
  - id: default
    description: "Default CityBench configuration"
    config_overrides: {}

  - id: disasters_heavy
    description: "Increased disaster frequency and severity"
    config_overrides:
      disaster_frequency_multiplier: 2.0
      disaster_severity_multiplier: 1.5
```

- **Correctness / consistency**  
  - The model IDs and `agent_type` values exactly match the wiring in `benchmark/experiment_runner.py`.  
  - Seeds and scenario IDs align with the runs recorded in `experiments/citybench_v1/runs/index.csv`, and the metrics files show exactly 10 runs per (model, scenario), which is consistent with 5 seeds × 2 scenarios.
- **Extensibility**  
  - The `config_overrides` keys are a subset of what `build_sim_config_for_scenario` supports (`starting_budget`, `starting_population`, `disaster_frequency_multiplier`, `disaster_severity_multiplier`), leaving room to add more scenarios later.

**Overall rating**: ✅ Clean and minimal experiment matrix.

---

### `experiments/citybench_v1/runs/index.csv`

```1:40:experiments/citybench_v1/runs/index.csv
run_id,model,seed,scenario,result_path
...
citybench_v1_llama3_8b_seed42_default,llama3:8b,42,default,/home/robot/llmcityeval/results/llama3_8b_42_20260309T201834Z.json
...
citybench_v1_random_baseline_seed46_disasters_heavy,random_baseline,46,disasters_heavy,/home/robot/llmcityeval/results/random_baseline_46_20260309T201837Z.json
...
citybench_v1_heuristic_baseline_seed45_disasters_heavy,heuristic_baseline,45,disasters_heavy,/home/robot/llmcityeval/results/heuristic_baseline_45_20260309T201837Z.json
...
```

- **Correctness**  
  - The index appears internally consistent: every combination of model ∈ {llama3:8b, llama3:70b, random_baseline, heuristic_baseline}, seed ∈ {42–46}, scenario ∈ {default, disasters_heavy} is present exactly once, and result paths match the naming convention used by `run_benchmark`.  
  - The header row is present, and there’s no malformed row without `result_path` in the excerpt shown.

**Overall rating**: ✅ Looks correct and machine-consumable.

---

### `experiments/citybench_v1/metrics/per_run_metrics.jsonl`

```1:20:experiments/citybench_v1/metrics/per_run_metrics.jsonl
{"run_id": "citybench_v1_llama3_8b_seed42_default", "experiment": "citybench_v1", "model": "llama3:8b", "seed": 42, "scenario": "default", "metrics": {...}, "meta": {"source_path": "/home/robot/llmcityeval/results/llama3_8b_42_20260309T201834Z.json"}}
{"run_id": "citybench_v1_llama3_8b_seed42_disasters_heavy", ...}
...
{"run_id": "citybench_v1_llama3_70b_seed46_disasters_heavy", ...}
```

- **Correctness / schema**  
  - Each JSON line includes `run_id`, `experiment`, `model`, `seed`, `scenario`, `metrics`, and `meta.source_path`, which matches the expectations implied by `README.md` and `testing.md`.  
  - Metric values (final_score, population_score, etc.) look numerically plausible and are consistent across default and disasters_heavy scenarios for the shown models.

**Overall rating**: ✅ Well-structured metrics log; no code-level concerns.

---

### `experiments/citybench_v1/metrics/summary_by_model.csv`

```1:9:experiments/citybench_v1/metrics/summary_by_model.csv
model,scenario,num_runs,final_score_mean,final_score_std,final_score_min,final_score_max,hard_constraint_violations_mean,avg_recovery_turns_mean
heuristic_baseline,default,10,37.866074766084935,0.2852476971079961,37.53849300748779,38.256408375551906,7.2,2.6014743589743587
heuristic_baseline,disasters_heavy,10,37.866074766084935,0.2852476971079961,37.53849300748779,38.256408375551906,7.2,2.6014743589743587
llama3:70b,default,10,25.0,0.0,25.0,25.0,0,0.9703296703296703
llama3:70b,disasters_heavy,10,25.0,0.0,25.0,25.0,0,0.9703296703296703
llama3:8b,default,10,28.648084362352765,6.1019710545837835,25.0,42.061697336611516,10.2,1.3946886446886446
llama3:8b,disasters_heavy,10,25.03688855971496,3.7325817619292,16.379114145658264,32.96926934959628,8.9,2.0635113660848954
random_baseline,default,10,32.248431821442956,6.790461565441429,25.0,41.32581440898201,128.2,2.388717948717949
random_baseline,disasters_heavy,10,32.05534669524388,6.552899353753767,25.0,39.8199777993972,128.2,2.704102564102564
```

- **Correctness / plausibility**  
  - Summary statistics are consistent with a 10-run experiment per (model, scenario). The trends (heuristic baseline best final score, random baseline many constraint violations, LLaMA models lower scores but zero hard violations) align with expectations and the README’s narrative.

**Overall rating**: ✅ No structural issues.

---

### `experiments/citybench_v1/metrics/summary_overall.json`

```1:80:experiments/citybench_v1/metrics/summary_overall.json
{
  "experiment": "citybench_v1",
  "metrics": {
    "default": {
      "heuristic_baseline": {
        "num_runs": 10,
        "final_score": { "mean": 37.8660..., "std": 0.2852..., ... },
        "hard_constraint_violations": { "mean": 7.2 },
        "avg_recovery_turns": { "mean": 2.6014... }
      },
      "llama3:70b": { ... },
      "llama3:8b": { ... },
      "random_baseline": { ... }
    },
    "disasters_heavy": {
      ...
    }
  }
}
```

- **Correctness / structure**  
  - Nested dictionaries by `(scenario → model → metric)` align with what’s described in README/testing as the machine-readable summary.  
  - Values match those in `summary_by_model.csv`, so consumers can choose whichever format is more convenient without divergence.

**Overall rating**: ✅ Well-structured aggregated metrics; no code changes implied.

---

### `tests/test_baseline_agents.py`

```34:48:tests/test_baseline_agents.py
def _empty_state(tick: int, budget: float = 2000.0, size: int = 10) -> CityState:
    grid = [[TileState(x=x, y=y) for x in range(size)] for y in range(size)]
    return CityState(
        tick=tick,
        budget=budget,
        population=0,
        revenue_per_tick=0.0,
        expenses_per_tick=0.0,
        livability=1.0,
        pollution_avg=0.0,
        grid=grid,
        recent_events=[],
        metrics_delta={},
        last_action_outcomes=[],
    )
```

- **Correctness**  
  - Helper builds a simple, rectangular, all-empty grid city state with no disabled tiles or prior outcomes, which is ideal for baseline tests.

```58:67:tests/test_baseline_agents.py
def test_random_agent_generates_bounded_valid_actions() -> None:
    agent = RandomAgent(seed=123)
    actions = agent.decide(_empty_state(tick=0))

    assert 1 <= len(actions) <= 5
    for action in actions:
        assert action.type == "zone"
        assert 0 <= action.x < 10
        assert 0 <= action.y < 10
        assert action.zone in (VALID_ZONES - {"E"})
```

- **Coverage for `RandomAgent`**  
  - Confirms both count bounds and zone/type validity. This is a good smoke test for basic behavior.

```70:87:tests/test_baseline_agents.py
def test_heuristic_agent_starts_with_road_spine() -> None:
    agent = HeuristicAgent(seed=42)
    actions = agent.decide(_empty_state(tick=0))
    ...

def test_heuristic_agent_keeps_default_seed_constructor() -> None:
    agent = HeuristicAgent()
    actions = agent.decide(_empty_state(tick=0))
    ...
```

- **Backward-compat behavior**  
  - These tests verify both explicit and default seeding for `HeuristicAgent`, ensuring the alias and constructor default remain stable.

```89:127:tests/test_baseline_agents.py
@pytest.mark.parametrize(
    ("agent_factory", "tick"),
    [
        (lambda: BudgetAwareRandomAgent(seed=1), 0),
        (lambda: ConnectivityAwareRandomAgent(seed=1), 0),
        (lambda: HeuristicAgent(), 0),
        (lambda: ConnectivityAwareHeuristicAgent(seed=1), 0),
        (lambda: HybridBudgetConnectivityAgent(seed=1), 0),
    ],
)
def test_affordability_aware_agents_return_no_actions_with_zero_budget(
    agent_factory, tick: int
) -> None:
    state = _empty_state(tick=tick, budget=0.0)
    actions = agent_factory().decide(state)
    assert actions == []
```

- **Coverage of affordability behavior**  
  - This and the following parametrized tests (L109–127) ensure all “affordability-aware” agents return no actions either with zero budget or when budget is below `COST_ROAD`. This is an important invariant.

```129:140:tests/test_baseline_agents.py
def test_connectivity_aware_random_agent_builds_road_when_zone_is_unaffordable() -> None:
    state = _state_with_active_road(tick=8, budget=float(COST_ROAD), size=5)
    agent = ConnectivityAwareRandomAgent(seed=7)
    actions = agent.decide(state)
    ...
```

- **Connectivity behavior**  
  - Verifies that the agent builds a road in a legal connected tile when only roads are affordable, and that the chosen tile is indeed in `empty_with_road`. Combined with later tests, this gives decent coverage of connectivity-based decisions.

```151:161:tests/test_baseline_agents.py
@pytest.mark.parametrize(
    ("zone", "expected_cost"),
    [
        (ZONE_ROAD, COST_ROAD),
        (ZONE_RESIDENTIAL, COST_RESIDENTIAL),
        (ZONE_COMMERCIAL, COST_COMMERCIAL),
        (ZONE_INDUSTRIAL, COST_INDUSTRIAL),
    ],
)
def test_get_zone_cost_returns_shared_zone_prices(zone: str, expected_cost: int) -> None:
    assert get_zone_cost(zone) == expected_cost
```

- **Coverage of `get_zone_cost`**  
  - Confirms shared pricing across zones; does not test invalid zone behavior (see “Test gaps”).

```177:185:tests/test_baseline_agents.py
def test_hybrid_agent_does_not_target_same_tile_twice_in_late_game() -> None:
    state = _state_with_active_road(tick=45, budget=1000.0, size=5)
    agent = HybridBudgetConnectivityAgent(seed=3)

    actions = agent.decide(state)

    targeted_tiles = [(action.x, action.y) for action in actions]
    assert len(targeted_tiles) == len(set(targeted_tiles))
```

- **Coverage for hybrid agent**  
  - Directly validates that no tile is targeted twice in a high-budget, late-game scenario. Combined with action-limit tests (L187–203), this gives good confidence in the hybrid agent’s core behavior.

**Overall rating**: ✅ Strong targeted coverage for baseline agents and utilities; some edge cases still untested.

---

## Potential bugs and test gaps

- **Jagged grid neighbor access in `get_connectivity_info` (agents/utils.py L23–L25, L32–L43)**  
  - If `CityState.grid` is ever non-rectangular, the neighbor bounds check can allow indices that are out-of-range for the current row, causing `IndexError`.  
  - **Test gap**: No test currently constructs a jagged grid to validate this behavior.

- **Silent handling of unknown zones in `get_zone_cost` (agents/utils.py L69–L78)**  
  - Returning `0` for unknown zones might quietly mask errors.  
  - **Test gap**: No tests exercise invalid zone values to confirm desired behavior.

- **Logging field mismatch in `OllamaAgent` (agents/ollama.py L123–L127)**  
  - Logs reference `"turn"` in the payload, but `CityState` uses `tick`. This is not a runtime bug but could confuse debugging or downstream tools that rely on logs.

- **LLM action volume and simulator caps**  
  - `_parse_actions` does not enforce an explicit action limit; enforcement is left to the simulator via `MAX_ACTIONS_PER_TURN`.  
  - **Test gap**: No direct test currently verifies that very large `actions` lists from the LLM are safely truncated or rejected by the sim loop for all agent types.

- **Experiment runner resilience to partial or corrupted index files**  
  - `_load_completed_runs` skips rows without `result_path`, but there are no tests ensuring the experiment runner behaves well when `index.csv` is partially corrupt or missing columns.  

---

## De-slopping and simplification suggestions

- **Clarify jagged vs rectangular grids in `agents/utils.py`**  
  - Either explicitly enforce rectangular grids (simplifying bounds checks and documenting the invariant) or fully support jagged grids with row-specific bounds checking. The current halfway approach (global `width` with a “jagged” comment) is confusing.

- **Refine variable naming in `ConnectivityAwareRandomAgent` (agents/random_agent.py L103–L108)**  
  - Rename filtered lists inside the loop to `remaining_empty_with_road` / `remaining_empty_without_road` to distinguish them from the original connectivity data and improve readability.

- **Factor out scoring helper in `HybridBudgetConnectivityAgent`**  
  - Moving the scoring logic into a helper (e.g., `_score_candidate_tile`) would make it easier to tune heuristics without growing a monolithic method.

- **Align logging field names in `OllamaAgent`**  
  - Change the logged key from `"turn"` to `"tick"`, or log both, to avoid confusion and align with the `CityState` schema.

- **Harden `get_zone_cost` behavior**  
  - Instead of returning `0` silently, consider using a small helper dict and either raising for unknown zones or logging a warning. This will make misconfigurations or unexpected model outputs more visible.

---

## Actionable recommendations

1. **Fix jagged-grid safety in `get_connectivity_info`**  
   - Update neighbor bounds checks to use `len(state.grid[ny])` for the x-dimension, or enforce rectangular grids explicitly and document the invariant.  
   - Add tests that construct a jagged grid and confirm no `IndexError` and correct classification of empty tiles.

2. **Clarify and possibly tighten `get_zone_cost` behavior**  
   - Decide whether unknown zones should be treated as a hard error or a logged warning; adjust `get_zone_cost` and add a test case for an invalid zone.

3. **Improve readability in `ConnectivityAwareRandomAgent`**  
   - Rename the in-loop filtered lists and consider extracting the “pick next tile under budget” logic into a helper for clarity.

4. **Align logging with `CityState` semantics in `OllamaAgent`**  
   - Change the logged key `"turn"` to `"tick"` (or add `"tick"` alongside `"turn"`) in the debug payload to avoid confusion when correlating logs with state.

5. **Add stress tests around action volume and simulator limits**  
   - Create tests that feed an `OllamaAgent`-like action list with far more than `MAX_ACTIONS_PER_TURN` entries into the simulator and verify that the cap is reliably enforced and logged.

6. **Add robustness tests for experiment runner index handling**  
   - Introduce tests where `experiments/citybench_v1/runs/index.csv` is missing rows, missing `result_path`, or partially corrupted, and confirm that `resume` mode behaves gracefully (skipping only truly completed runs).

---

*Review generated on 2026-03-09 based on current working tree state.* 
