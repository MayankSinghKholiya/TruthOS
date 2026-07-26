"""Ensures required settings exist before any module imports app.core.config,
so tests never depend on a real .env file or live infrastructure."""
import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")

import pytest


class FakeLLMRouter:
    """Drop-in stand-in for LLMRouter that returns a pre-scripted JSON payload
    instead of calling OpenRouter, so agent unit tests don't need network
    access or API keys."""

    def __init__(self, scripted_response: dict, model_used: str = "test-model") -> None:
        self.scripted_response = scripted_response
        self.model_used = model_used
        self.calls: list[dict] = []

    async def complete_json(self, *, system: str, user: str, model=None, temperature=0.2, agent_name="unknown"):
        self.calls.append({"system": system, "user": user, "agent_name": agent_name})
        return self.scripted_response, self.model_used


@pytest.fixture
def fake_llm_router():
    return FakeLLMRouter
