from __future__ import annotations

from benchmark.logger import RunLog
from benchmark.scorer import score_run
from config import TURNS
from sim.city import City
from sim.runtime_config import SimConfig


def run(
    agent,
    seed: int,
    turns: int = TURNS,
    verbose: bool = False,
    results_dir: str = "results",
    sim_config: SimConfig | None = None,
) -> RunLog:
    sim = City(seed=seed, sim_config=sim_config)
    log = RunLog(agent_name=agent.name, seed=seed)

    for turn in range(turns):
        state = sim.get_state()
        actions = agent.decide(state)
        sim.apply_actions(actions)
        disaster_events = sim.tick()

        parse_success = bool(getattr(agent, "last_parse_success", True))
        action_outcomes = sim.get_last_action_outcomes()
        budget_spent = sim.get_last_budget_spent()
        log.record_turn(
            turn=turn,
            state=state,
            actions=actions,
            action_parse_success=parse_success,
            action_outcomes=action_outcomes,
            budget_spent=budget_spent,
            disaster_events=disaster_events,
        )

        if verbose:
            current = sim.get_state()
            print(
                "turn="
                f"{turn:02d} pop={current.population} budget={current.budget:.1f} "
                f"rev={current.revenue_per_tick:.1f} exp={current.expenses_per_tick:.1f} "
                f"liv={current.livability:.3f} poll={current.pollution_avg:.3f}"
            )

    final_state = sim.get_state()
    log.record_final_state(final_state)
    scores = score_run(log.to_dict())
    log.set_scores(scores)
    log.save(results_dir)
    return log
