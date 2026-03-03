# CityBench MVP

CityBench is a city-building benchmark where an LLM acts as an urban planner.  
Each turn, the model receives structured city state JSON and returns zoning actions.  
The simulator advances deterministically (given a seed), logs every turn, and computes final scores.

## Requirements

- Python 3.10+
- Local Ollama instance at `http://localhost:11434`
- Dependency: `requests`

Install:

```bash
pip install -r requirements.txt
```

## Run benchmark

Single seed:

```bash
python run.py --model llama3:8b --seed 42 --turns 50
```

Multiple seeds:

```bash
python run.py --model llama3:8b --seeds 42,43,44,45,46 --turns 50
```

Verbose per-turn output:

```bash
python run.py --model llama3:8b --seed 42 --verbose
```

## Compare existing results

```bash
python run.py --compare results/
```

This prints an ASCII table and writes `results/comparison_summary.csv`.

## Project layout

- `sim/`: simulation state, mechanics, grid, disasters
- `agents/`: base agent interface and Ollama-backed agent
- `benchmark/`: run loop, scoring, and logging
- `prompts/system.txt`: system prompt passed to the model
- `config.py`: all tunable constants
- `results/`: generated per-run JSON logs
