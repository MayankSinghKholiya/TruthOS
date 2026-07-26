"""OpenRouter-backed LLM client with structured JSON output, retries and
model fallback. This is the single choke point every agent calls through -
agents never talk HTTP directly.
"""
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings
from app.core.exceptions import AgentExecutionError
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMTransientError(Exception):
    """Raised for retryable failures (timeouts, 5xx, rate limits)."""


class LLMRouter:
    """Routes chat completions through OpenRouter with retry + fallback model.

    Usage:
        router = LLMRouter(http_client)
        content = await router.complete_json(system=..., user=..., model=None)
    """

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http = http_client
        self._settings = get_settings()

    async def _call_openrouter(
        self, *, model: str, system: str, user: str, temperature: float
    ) -> str:
        if not self._settings.openrouter_api_key:
            raise LLMTransientError("OPENROUTER_API_KEY is not configured")

        response = await self._http.post(
            f"{self._settings.openrouter_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        if response.status_code == 429 or response.status_code >= 500:
            raise LLMTransientError(f"OpenRouter returned {response.status_code}")
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]

    @retry(
        retry=retry_if_exception_type(LLMTransientError),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _complete_with_retry(
        self, *, model: str, system: str, user: str, temperature: float
    ) -> str:
        return await self._call_openrouter(
            model=model, system=system, user=user, temperature=temperature
        )

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0.2,
        agent_name: str = "unknown",
    ) -> tuple[str, str]:
        """Returns (content, model_actually_used). Falls back to FALLBACK_MODEL
        if the primary model fails after retries."""
        primary = model or self._settings.default_model
        try:
            content = await self._complete_with_retry(
                model=primary, system=system, user=user, temperature=temperature
            )
            return content, primary
        except Exception as primary_exc:
            logger.warning(
                "llm_primary_failed", agent=agent_name, model=primary, error=str(primary_exc)
            )
            try:
                content = await self._complete_with_retry(
                    model=self._settings.fallback_model,
                    system=system,
                    user=user,
                    temperature=temperature,
                )
                return content, self._settings.fallback_model
            except Exception as fallback_exc:
                raise AgentExecutionError(
                    agent_name,
                    f"primary and fallback models both failed: {fallback_exc}",
                ) from fallback_exc

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0.2,
        agent_name: str = "unknown",
    ) -> tuple[dict[str, Any], str]:
        """Same as complete(), but parses the response as JSON. Retries once
        with a corrective instruction if the model returns malformed JSON."""
        content, used_model = await self.complete(
            system=system, user=user, model=model, temperature=temperature, agent_name=agent_name
        )
        try:
            return _extract_json(content), used_model
        except (json.JSONDecodeError, ValueError):
            corrective_user = (
                f"{user}\n\nYour previous response was not valid JSON. "
                "Respond again with ONLY the valid JSON object, no prose."
            )
            content, used_model = await self.complete(
                system=system,
                user=corrective_user,
                model=used_model,
                temperature=0.0,
                agent_name=agent_name,
            )
            return _extract_json(content), used_model


def _extract_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model output")
    return json.loads(text[start : end + 1])
