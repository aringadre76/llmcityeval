# CityBench MVP — Agent Specification

## Overview

Build a city-building simulation where LLMs act as autonomous urban planners. The model receives structured city state data and outputs a set of actions each turn. The simulation advances, the model sees what changed, and submits the next set of actions. This loop runs for a fixed number of turns. Final cities are scored and compared across models.

The goal is to benchmark **systems-level planning intelligence** — not game knowledge.

---

## Project Structure

```
citybench/
├── sim/
│   ├── __init__.py
│   ├── grid.py          # Land grid and zone management
│   ├── city.py          # City state, tick logic, metrics
│   ├── mechanics.py     # Population, budget, pollution, livability formulas
│   └── disasters.py     # Random disaster events
├── agents/
│   ├── __init__.py
│   ├── base.py          # Abstract agent interface
│   └── ollama.py        # Ollama-backed LLM agent
├── benchmark/
│   ├── __init__.py
│   ├── runner.py        # Run loop: agent ↔ sim
│   ├── scorer.py        # Final city scoring
│   └── logger.py        # Per-turn state + action logging
├── prompts/
│   └── system.txt       # System prompt for the agent
├── config.py            # All tunable constants in one place
├── run.py               # CLI entry point
└── results/             # Auto-created, stores run logs as JSON
```

---

## Simulation

### Grid

- **Size:** 10×10 tiles
- **Each tile** has a zone type and a pollution level (float 0.0–1.0)
- **Zone types:**

| Code | Name | Description |
|------|------|-------------|
| `E` | Empty | Undeveloped land |
| `R` | Residential | Housing; generates population and tax revenue |
| `C` | Commercial | Jobs and services; boosts livability near residential |
| `I` | Industrial | Jobs and high tax revenue; generates pollution |
| `O` | Road | Infrastructure; required for zones to function |

- A zone tile is **connected** if it has at least one adjacent Road tile (orthogonal). Disconnected zones do not contribute to population, revenue, or jobs.
- Pollution from Industrial tiles spreads to the 8 surrounding tiles each tick (Moore neighborhood), decaying with distance.

### City State

```python
@dataclass
class CityState:
    tick: int
    budget: float          # Current funds
    population: int
    revenue_per_tick: float
    expenses_per_tick: float
    livability: float      # 0.0–1.0, affects population growth
    pollution_avg: float   # City-wide average pollution
    grid: list[list[TileState]]   # 10x10
    recent_events: list[str]      # Disaster/event messages from last tick
    metrics_delta: dict           # Fixed numeric deltas vs previous tick
```

`metrics_delta` has a fixed schema with six keys, always present and always numeric (0 if unchanged):
`budget`, `population`, `revenue_per_tick`, `expenses_per_tick`, `livability`, `pollution_avg`.

Each `TileState`:
```python
@dataclass
class TileState:
    x: int
    y: int
    zone: str              # E, R, C, I, O
    pollution: float       # 0.0–1.0
    connected: bool        # Has adjacent road?
    disabled: bool         # True if road tile is disabled by infrastructure failure
```

### Mechanics

**Revenue per tick:**
- Each connected R tile: +`REVENUE_RESIDENTIAL` (default 10)
- Each connected C tile: +`REVENUE_COMMERCIAL` (default 20)
- Each connected I tile: +`REVENUE_INDUSTRIAL` (default 35)

**Expenses per tick:**
- Each Road tile: +`EXPENSE_ROAD` (default 3) maintenance
- Each non-Empty tile: +`EXPENSE_ZONE` (default 1) upkeep
- Disabled roads still count as Road tiles for maintenance cost.

**Livability (0.0–1.0):**

Livability starts at 1.0 (perfect) and degrades based on city conditions.

```
livability = 1.0
  - (pollution_avg * POLLUTION_PENALTY)        # default weight: 0.5
  + (commercial_ratio * COMMERCIAL_BONUS)      # weight: 0.3
  - (congestion_penalty)                       # weight: 0.2
```
Clamp to [0.0, 1.0].

- **`commercial_ratio`**: proportion of *land-use tiles* (R + C + I only) that are Commercial. Roads and Empty tiles are excluded from the denominator. If there are no land-use tiles, commercial_ratio = 0.
- **`congestion_penalty`**: `max(0, 1 - (road_tiles / developed_tiles)) * CONGESTION_WEIGHT`. Fewer roads relative to developed tiles (R + C + I) = higher congestion. If there are 0 developed tiles, congestion_penalty = 0.
- `road_tiles` includes disabled road tiles. Disabled roads exist physically but do not provide connectivity.

**Population (stored value model):**

Population is a **stored value** that trends toward a formula-calculated target each tick. Decisions have lasting weight — you can't instantly undo bad zoning.

Each tick:

1. Compute `target_pop`:
   ```
   target_pop = connected_R_tiles × POP_PER_RESIDENTIAL × (0.5 + livability × 0.5) / demand_surge_divisor
   ```
   `demand_surge_divisor` = product of all active Demand Surge divisors (1.0 if none active).

2. Move stored population toward target:
   ```
   population = population + (target_pop - population) × POP_CHANGE_RATE
   ```
   `POP_CHANGE_RATE` default: 0.20 (20% of the gap per tick).

3. Apply bankruptcy penalty (only if `budget < 0` after budget update):
   ```
   population = population × (1 - BANKRUPTCY_POP_PENALTY)
   ```
   `BANKRUPTCY_POP_PENALTY` default: 0.05 (5% loss per tick).

4. Floor to non-negative integer: `population = max(0, floor(population))`

**Pollution spread (per tick):**

Order: **spread first, then decay.** Pollution expands before it fades, making industrial zones more dangerous to neighbors.

1. Each I tile adds `POLLUTION_EMISSION` (default 0.3) to itself
2. Each I tile spreads `POLLUTION_SPREAD_FACTOR` (default 0.15) to each of its 8 neighbors (Moore neighborhood)
3. All pollution values decay by `POLLUTION_DECAY` (default 0.05) per tick
4. Clamp all pollution values to [0.0, 1.0]

**Building costs (one-time):**

| Zone | Cost |
|------|------|
| Road | 50 |
| Residential | 100 |
| Commercial | 150 |
| Industrial | 200 |
| Clear (any → Empty) | 25 |

Building on a non-Empty tile requires clearing first (additional 25 cost), applied automatically.

### Canonical Tick Pipeline

This is the definitive per-tick order and must remain unchanged:

1. Apply actions (zone changes, costs deducted from budget)
2. Recompute connectivity (adjacent non-disabled road requirement)
3. Update active disaster timers (decrement remaining ticks, expire finished disasters)
4. Roll for new disasters (seeded RNG, fixed call order: Recession → Demand Surge → Infra Failure → Pollution Event)
5. Spread pollution, then decay
6. Compute revenue (halved per active recession) and expenses, update budget
7. Compute livability
8. Compute `target_pop`, move stored population toward target via `POP_CHANGE_RATE`
9. Apply bankruptcy penalty if `budget < 0`
10. Floor population to non-negative integer
11. Snapshot `metrics_delta` (current minus previous tick values)

### Starting Conditions

```python
STARTING_BUDGET = 2000
STARTING_POPULATION = 0
TURNS = 50
```

Grid starts fully Empty. No infrastructure. Model must build from scratch.

### Disasters

Disasters fire randomly each tick. Each has a base probability per tick. **Disasters stack** — multiple disasters of the same type can be active simultaneously (e.g., two overlapping recessions = revenue quartered). Don't special-case this; emergent difficulty is intentional.

| Event | Probability/tick | Effect |
|-------|-----------------|--------|
| Recession | 0.04 | Revenue halved for 3 ticks. Multiple recessions multiply (two active = ×0.25). |
| Demand Surge | 0.03 | For 3 ticks, population capacity is compressed: `target_pop = connected_R × POP_PER_RESIDENTIAL × (0.5 + livability × 0.5) / DEMAND_SURGE_DIVISOR`. `DEMAND_SURGE_DIVISOR = 1.5` during the event, `1.0` otherwise. At livability 1.0, capacity drops to ~67% of normal. Multiple surges multiply divisors. The model sees this via the event message and by observing population behavior — reasoning from observation is intentional. |
| Infrastructure failure | 0.03 | A random road tile is disabled for 2 ticks. The tile remains zone `O` in the grid but its `disabled` field is set to `true`. Adjacent tiles show `connected: false` during the outage. Disabled roads still incur maintenance and still count for congestion road count. If there are no road tiles when triggered, skip and log (no reroll). |
| Pollution event | 0.03 | A random tile adjacent to an Industrial tile gets +0.4 pollution instantly. If no eligible tile exists, skip and log (no reroll). |

Use **seeded randomness**. Each run takes a `seed` integer. Same seed = same disaster sequence for all models. This makes cross-model comparison fair.

If a triggered disaster has no valid target, it is a no-op and must be logged, e.g.:
`{"event": "pollution_event", "outcome": "skipped", "reason": "no_industrial_tiles"}`.
Do not reroll.

RNG call discipline is fixed. Each tick, make calls in this order:
1. Recession roll
2. Demand Surge roll
3. Infrastructure Failure roll
4. Pollution Event roll

If Infrastructure Failure triggers, make one additional RNG call to choose the target road tile.
If Pollution Event triggers, make one additional RNG call to choose the target tile.
Use one `random.Random(seed)` instance on `City`; never module-level global random.

**Disaster messages** are appended to `recent_events` every tick while active. The model sees explicit ongoing messages — the benchmark tests planning, not bookkeeping.

Message format:
- **Tick it fires:** `"RECESSION: Revenue halved for 3 ticks."` / `"DEMAND SURGE: Population capacity reduced for 3 ticks."` / `"INFRASTRUCTURE FAILURE: Road at (x, y) disabled for 2 ticks."`
- **Subsequent ticks:** `"RECESSION ONGOING: 2 ticks remaining."` / `"DEMAND SURGE ONGOING: 1 tick remaining."` / `"INFRASTRUCTURE FAILURE ONGOING: Road at (x, y) disabled, 1 tick remaining."`
- **Pollution event:** Single message on the tick it fires only (instantaneous): `"POLLUTION EVENT: Tile (x, y) received +0.4 pollution."`

---

## Agent Interface

### Abstract Base

```python
class BaseAgent:
    def decide(self, state: CityState) -> list[Action]:
        raise NotImplementedError
```

### Action Schema

Actions are submitted as a list. Actions are processed **in list order** (not simultaneously).

```python
@dataclass
class Action:
    type: str    # "zone"
    x: int
    y: int
    zone: str    # E, R, C, I, O
```

Only one action type exists in MVP: `zone` (set a tile's zone type).

**Action cap:** `MAX_ACTIONS_PER_TURN = 50`. Actions beyond the cap are dropped and logged with reason `"exceeded_max_actions"`.

**Duplicate tile handling:** If multiple actions target the same (x, y), last one wins. Actions are processed in list order; later actions overwrite earlier ones on the same tile.

**Budget validation — greedy, in list order:**
- Process each action sequentially, deducting cost from remaining budget
- If the current remaining budget cannot cover an action, **skip it** and log the skipped action
- Continue processing the rest of the list
- This rewards the model for ordering high-priority actions first

**Other validation:**
- Coordinates must be within grid bounds (out-of-bounds actions are skipped and logged)

### Ollama Agent

Sends the serialized city state to a local Ollama model and parses the response.

**Request format:**
```python
POST http://localhost:11434/api/generate
{
  "model": "<model_name>",
  "prompt": "<system_prompt>\n\n<state_json>",
  "stream": false
}
```

**Expected model output — strict JSON only:**
```json
{
  "actions": [
    {"type": "zone", "x": 3, "y": 4, "zone": "O"},
    {"type": "zone", "x": 3, "y": 5, "zone": "R"}
  ]
}
```

The agent must parse only the JSON block from the model response. Use a regex to extract the first `{...}` block if the model outputs surrounding text.

If parsing fails, log the failure and submit an empty action list for that turn.
For invalid output diagnostics, log raw model text truncated to `LOG_RAW_RESPONSE_MAX_CHARS` (default 500).

---

## Prompts

### System Prompt (`prompts/system.txt`)

```
You are an urban planning agent managing a city on a 10x10 grid.

YOUR GOAL: Maximize total population at the end of 50 turns.

ZONE TYPES:
- E: Empty (undeveloped)
- R: Residential — houses people, generates tax revenue
- C: Commercial — creates jobs, boosts livability near residential zones
- I: Industrial — high revenue, but generates pollution that reduces livability and population capacity
- O: Road — required for any zone to function (zones need at least one adjacent road tile)

KEY RULES:
- Zones not adjacent to a Road tile are inactive and contribute nothing
- Pollution from Industrial zones spreads to neighbors and reduces your population ceiling
- Livability affects how many people your residential zones can support
- Budget can go negative — if it does, population will decline each turn
- Balance revenue with expenses: roads cost maintenance every turn

EACH TURN:
You will receive the current city state as JSON. Respond ONLY with a JSON object containing your actions.

Format:
{"actions": [{"type": "zone", "x": <0-9>, "y": <0-9>, "zone": "<E|R|C|I|O>"}]}

You may submit multiple actions per turn. Each action sets one tile's zone type.
Do not include any explanation or text outside the JSON object.
```

---

## Run Loop (`benchmark/runner.py`)

```python
def run(agent, seed, turns=50) -> RunLog:
    sim = City(seed=seed)
    log = RunLog(agent_name=agent.name, seed=seed)

    for turn in range(turns):
        state = sim.get_state()
        log.record_state(turn, state)

        actions = agent.decide(state)
        log.record_actions(turn, actions)

        sim.apply_actions(actions)
        sim.tick()

    log.record_final_state(sim.get_state())
    return log
```

---

## Scoring (`benchmark/scorer.py`)

Score each completed run across four dimensions.
- Population score is not clamped.
- Efficiency, Stability, and Resilience are clamped to [0, 100].

| Dimension | Formula |
|-----------|---------|
| **Population** | `final_population / THEORETICAL_MAX_POP × 100` |
| **Efficiency** | `final_population / total_budget_spent × scaling_factor`. `total_budget_spent` = cumulative sum of all zoning action costs (one-time building costs only, excludes ongoing maintenance). |
| **Stability** | `(1 - std_dev(population_per_tick) / mean(population_per_tick)) × 100` — clamped to [0, 100]. If mean population is 0 (city never grew), stability = 0. |
| **Resilience** | `avg_population_after / avg_population_before × 100` per disaster event, then averaged across all events. Use up to 5 ticks before/after each event with minimum window size 1 at boundaries. Overlapping disasters are measured independently (do not merge windows). If no disasters occurred, resilience = 100. |

**`THEORETICAL_MAX_POP`**: fixed normalization constant only. Set to `4000` and keep it hardcoded. It is not required to be achievable under current game rules. If a future model exceeds it, allowing population score > 100 is a calibration signal (not a simulation bug).

**`scaling_factor`** (for Efficiency): `100 / (POP_PER_RESIDENTIAL × GRID_SIZE)`. Calibrated so a "reasonable" city scores around 50. Recalculate and hardcode after first test runs if the range is off.

**Composite score:** simple average of the four dimensions.

When comparing models, treat duplicate model+seed runs as intentional replications:
- aggregate by model with mean ± std
- show a flag when a model has only one run (variance unavailable)

---

## Logging (`benchmark/logger.py`)

Save one JSON file per run to `results/`. Filename: `{model_name}_{seed}_{timestamp}.json`

```json
{
  "agent": "llama3:8b",
  "seed": 42,
  "turns": [
    {
      "turn": 0,
      "state": { ... },
      "actions": [ ... ],
      "action_parse_success": true
    }
  ],
  "final_state": { ... },
  "scores": {
    "population": 74.2,
    "efficiency": 61.5,
    "stability": 88.0,
    "resilience": 70.1,
    "composite": 73.5
  }
}
```

---

## CLI (`run.py`)

```
python run.py --model llama3:8b --seed 42 --turns 50
python run.py --model llama3:8b --seeds 42,43,44,45,46 --turns 50
python run.py --compare results/  # Print score summary table and save CSV
```

`--compare` outputs an ASCII table to the terminal for quick inspection and also saves a `.csv` file to `results/` for analysis.

---

## Config (`config.py`)

All simulation constants in one place. Must be easy to change for future experiments.

```python
# Grid
GRID_SIZE = 10

# Economy
STARTING_BUDGET = 2000
REVENUE_RESIDENTIAL = 10
REVENUE_COMMERCIAL = 20
REVENUE_INDUSTRIAL = 35
EXPENSE_ROAD = 3
EXPENSE_ZONE = 1

# Building costs
COST_ROAD = 50
COST_RESIDENTIAL = 100
COST_COMMERCIAL = 150
COST_INDUSTRIAL = 200
COST_CLEAR = 25

# Population
POP_PER_RESIDENTIAL = 50
POP_CHANGE_RATE = 0.20
BANKRUPTCY_POP_PENALTY = 0.05
DEMAND_SURGE_DIVISOR = 1.5

# Pollution
POLLUTION_EMISSION = 0.3
POLLUTION_SPREAD_FACTOR = 0.15
POLLUTION_DECAY = 0.05

# Livability
LIVABILITY_BASE = 1.0
POLLUTION_PENALTY = 0.5
COMMERCIAL_BONUS = 0.3
CONGESTION_WEIGHT = 0.2

# Simulation
TURNS = 50

# Scoring
THEORETICAL_MAX_POP = 4000   # Derived from striped layout (2 road cols, 8 R cols, all connected, livability 1.0)
EFFICIENCY_SCALING_FACTOR = 100 / (POP_PER_RESIDENTIAL * GRID_SIZE)  # = 0.2
MAX_ACTIONS_PER_TURN = 50
LOG_RAW_RESPONSE_MAX_CHARS = 500

# Disaster probabilities per tick
DISASTER_RECESSION_PROB = 0.04
DISASTER_DEMAND_SURGE_PROB = 0.03
DISASTER_INFRA_FAIL_PROB = 0.03
DISASTER_POLLUTION_PROB = 0.03
DISASTER_RECESSION_DURATION = 3
DISASTER_DEMAND_SURGE_DURATION = 3
DISASTER_INFRA_FAIL_DURATION = 2

# Ollama
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TIMEOUT = 90
DEFAULT_MODEL = "llama3:8b"
```

---

## Implementation Notes

- Use Python 3.10+
- **Dependencies:** standard library + `requests` only. No other packages.
- No game engine or GUI required for MVP — simulation is pure Python
- Ollama must be running locally on port 11434
- Default model: `llama3:8b` (overridable via CLI)
- **Ollama timeout:** 90 seconds. On timeout or any HTTP error, log the full error, submit empty actions for that turn, and continue. No retries — a slow model failing is meaningful benchmark data.
- All random events use Python's `random.Random(seed)` — never global random state
- Preserve fixed RNG call order every tick (see Disasters section), regardless of map state
- The sim tick and action resolution are deterministic given the same seed and actions
- Add a `--verbose` flag to print state summaries to stdout each turn
- Do not add a web UI, visualization, or any frontend in the MVP

---

## Out of Scope for MVP

- Chain-of-thought / reasoning traces
- Hidden state / partial observability
- Multiple action types beyond zoning
- Web UI or grid visualization
- Automated hyperparameter tuning
- Any model other than Ollama-hosted local models