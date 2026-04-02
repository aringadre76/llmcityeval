# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run a single benchmark
python run.py --model llama3:8b --seed 42 --turns 50

# Run multiple seeds
python run.py --model llama3:8b --seeds 42,43,44,45,46 --turns 50

# Run with verbose output
python run.py --model llama3:8b --seed 42 --verbose

# Compare existing results
python run.py --compare results/

# Run the experiments CLI
python -m benchmark.experiments_cli run --matrix experiments/citybench_v1/config/matrix.yaml --experiment citybench_v1
python -m benchmark.experiments_cli aggregate --experiment citybench_v1
```

## Architecture

The codebase implements **CityBench**, an LLM benchmark where models act as urban planners managing a 10x10 grid city over 50 turns.

### Core Layers

**Simulation (`sim/`)** - Deterministic city mechanics:
- `grid.py`: 10x10 grid with tile states (empty, road, residential, commercial, industrial)
- `mechanics.py`: Revenue, expenses, livability, population growth, pollution calculations
- `disasters.py`: Seeded disaster manager (recessions, demand surges, infra failures, pollution events)
- `city.py`: Main `City` class that orchestrates turns, applies actions, and tracks state
- `runtime_config.py`: Runtime configuration overrides (for experiments, not hardcoded)

**Agents (`agents/`)** - Decision-making interface:
- `base.py`: Abstract `BaseAgent` with `decide(state) -> list[Action]` method
- `ollama.py`: `OllamaAgent` sends JSON state to local Ollama, parses zoning actions
- `random_agent.py`: Random bounded zoning actions
- `heuristic_agent.py`: Phased policy (road spine, zone stripes, industrial edge)

**Benchmark (`benchmark/`)** - Execution and evaluation:
- `runner.py`: Main loop - get state, decide actions, apply, tick, score
- `scorer.py`: Normalized scores (population, efficiency, stability, resilience, composite)
- `logger.py`: JSON logging per turn for replay/analysis
- `experiment_runner.py`: Multi-model, multi-seed, multi-scenario orchestration
- `experiments_cli.py`: CLI for run/aggregate/upload/inspect/timeline

### Key Patterns

1. **Deterministic execution**: `City(seed)` uses `random.Random(seed)` internally
2. **Action feedback**: Failed actions return reasons (`insufficient_budget`, `out_of_bounds`, etc.) fed to next prompt
3. **Runtime config injection**: `SimConfig` objects override `config.py` values without editing source
4. **Experiment matrix**: YAML defines models, seeds, scenarios with `config_overrides` for variation

### Test commands

```bash
pytest tests -v          # Full test suite
python -m compileall .   # Verify Python syntax
ruff check .             # Linting
```
