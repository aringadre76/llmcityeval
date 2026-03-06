from __future__ import annotations

import json
from dataclasses import asdict

from agents.ollama import OllamaAgent
from sim.city import City


class _FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"response": '{"actions":[]}'}


def test_decide_surfaces_rejected_action_feedback(monkeypatch) -> None:
    captured_payload: dict[str, object] = {}

    def fake_post(url, json, timeout):  # noqa: ANN001
        captured_payload["prompt"] = json["prompt"]
        return _FakeResponse()

    monkeypatch.setattr("requests.post", fake_post)

    state = City(seed=1).get_state()
    state.last_action_outcomes = [
        {
            "action": {"type": "zone", "x": 3, "y": 4, "zone": "O"},
            "applied": False,
            "reason": "insufficient_budget",
            "cost": 50,
        }
    ]
    state_dict = asdict(state)

    agent = OllamaAgent(model="llama3:8b")
    actions = agent.decide(state)

    assert actions == []
    prompt = str(captured_payload["prompt"])
    assert "REJECTED ACTION FEEDBACK" in prompt
    assert "insufficient_budget" in prompt
    assert "(3,4)" in prompt
    assert json.dumps(state_dict, separators=(",", ":")) not in prompt
