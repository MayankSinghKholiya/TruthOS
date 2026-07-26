"""Loads agent prompt templates from YAML so no prompt text lives in Python code."""
from functools import lru_cache
from pathlib import Path
from string import Template
from typing import Any

import yaml

_TEMPLATES_DIR = Path(__file__).parent / "templates"


class PromptTemplate:
    def __init__(self, system: str, user: str) -> None:
        self._system = Template(system)
        self._user = Template(user)

    def render(self, **kwargs: Any) -> tuple[str, str]:
        """Returns (system_prompt, user_prompt) with $placeholders substituted."""
        return self._system.safe_substitute(**kwargs), self._user.safe_substitute(**kwargs)


@lru_cache
def _load_yaml(name: str) -> dict:
    path = _TEMPLATES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def get_prompt(name: str) -> PromptTemplate:
    """Load and cache the (system, user) prompt pair for the given agent name."""
    data = _load_yaml(name)
    return PromptTemplate(system=data["system"], user=data["user"])
