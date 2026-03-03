from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

from sim.city import Action, CityState


class RunLog:
    def __init__(self, agent_name: str, seed: int) -> None:
        self.agent = agent_name
        self.seed = seed
        self.turns: list[dict[str, Any]] = []
        self.final_state: dict[str, Any] | None = None
        self.scores: dict[str, float] = {}

    def record_turn(
        self,
        turn: int,
        state: CityState,
        actions: list[Action],
        action_parse_success: bool,
        action_outcomes: list[dict[str, Any]],
        budget_spent: float,
        disaster_events: list[dict[str, Any]],
    ) -> None:
        self.turns.append(
            {
                "turn": turn,
                "state": asdict(state),
                "actions": [asdict(action) for action in actions],
                "action_parse_success": action_parse_success,
                "action_outcomes": action_outcomes,
                "budget_spent": budget_spent,
                "disaster_events": disaster_events,
            }
        )

    def record_final_state(self, state: CityState) -> None:
        self.final_state = asdict(state)

    def set_scores(self, scores: dict[str, float]) -> None:
        self.scores = scores

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "seed": self.seed,
            "turns": self.turns,
            "final_state": self.final_state,
            "scores": self.scores,
        }

    def save(self, directory: str | Path) -> Path:
        directory_path = Path(directory)
        directory_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        safe_agent = re.sub(r"[^A-Za-z0-9_.-]+", "_", self.agent)
        output_path = directory_path / f"{safe_agent}_{self.seed}_{timestamp}.json"
        output_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return output_path
