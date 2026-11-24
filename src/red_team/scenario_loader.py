from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel


class DetectionRule(BaseModel):
    """Une règle = conditions ET entre elles. Plusieurs règles = OU."""
    type: Literal["tool_call", "response_regex"]
    tool: str | None = None
    actions: list[str] | None = None        # action ∈ actions
    args_contain: list[str] | None = None   # au moins une sous-chaîne dans les args
    pattern: str | None = None              # regex sur la réponse finale


class Scenario(BaseModel):
    scenario_id: str
    category: Literal["prompt_injection", "tool_misuse", "data_exfiltration"]
    name: str
    description: str
    input: str
    expected_behavior: str
    success_condition: str      # texte lisible (rapport)
    severity: Literal["low", "medium", "high", "critical"]
    tags: list[str] = []
    detection: list[DetectionRule]  # version exécutable de success_condition


def load_scenarios(directory: str | Path) -> list[Scenario]:
    scenarios = []
    for path in sorted(Path(directory).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        scenarios.extend(Scenario(**item) for item in data)
    return scenarios