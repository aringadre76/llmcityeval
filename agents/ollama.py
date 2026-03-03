from __future__ import annotations

from dataclasses import asdict
import json
import logging
from pathlib import Path
from typing import Any

import requests

from agents.base import BaseAgent
from config import DEFAULT_MODEL, LOG_RAW_RESPONSE_MAX_CHARS, OLLAMA_TIMEOUT, OLLAMA_URL
from sim.city import Action, CityState
from sim.grid import VALID_ZONES

logger = logging.getLogger(__name__)


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


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
            payload = {
                "model": self.model,
                "prompt": f"{self.system_prompt}\n\n{json.dumps(asdict(state), separators=(',', ':'))}",
                "stream": False,
            }
            response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
            response.raise_for_status()
            response_payload = response.json()
            model_text = response_payload.get("response", "")
            self.last_raw_response = str(model_text)
        except requests.RequestException as exc:
            self.last_parse_success = False
            logger.exception("Ollama request failed: %s", exc)
            return []
        except (ValueError, TypeError) as exc:
            self.last_parse_success = False
            logger.exception("Invalid response from Ollama endpoint: %s", exc)
            return []

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
