"""Base agent contract. Every agent in TruthOS (Planner, Research, Truth,
Judge, ...) subclasses BaseAgent and owns exactly one prompt template, a
declared input/output shape, whatever tools it needs, and a retry policy -
per the platform rule "each agent owns: prompt, inputs, outputs, tools,
retry policy, confidence".
"""
from abc import ABC, abstractmethod
from typing import Any

from app.core.exceptions import AgentExecutionError
from app.core.logging import get_logger
from app.prompts.loader import PromptTemplate, get_prompt
from app.schemas.agent import AgentResult, AgentStatus
from app.services.llm_router import LLMRouter

logger = get_logger(__name__)


class BaseAgent(ABC):
    #: unique agent identifier, also the YAML prompt template filename stem
    name: str
    #: model override; None means "use the router's default model"
    model: str | None = None
    #: temperature passed to the LLM for this agent's calls
    temperature: float = 0.2
    #: max attempts before giving up (LLMRouter already retries/falls back
    #: per HTTP call; this governs retries of the agent's own business logic)
    max_attempts: int = 2

    def __init__(self, llm_router: LLMRouter) -> None:
        self._llm_router = llm_router

    @property
    def prompt(self) -> PromptTemplate:
        return get_prompt(self.name)

    @abstractmethod
    async def run(self, **kwargs: Any) -> AgentResult:
        """Execute the agent's task and return a uniform AgentResult."""
        raise NotImplementedError

    async def _invoke_llm(self, **template_vars: Any) -> tuple[dict[str, Any], str]:
        system, user = self.prompt.render(**template_vars)
        return await self._llm_router.complete_json(
            system=system,
            user=user,
            model=self.model,
            temperature=self.temperature,
            agent_name=self.name,
        )

    async def _run_with_retry(self, **template_vars: Any) -> tuple[dict[str, Any], str, int]:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                output, model_used = await self._invoke_llm(**template_vars)
                return output, model_used, attempt - 1
            except Exception as exc:  # noqa: BLE001 - broad by design, wrapped below
                last_error = exc
                logger.warning(
                    "agent_attempt_failed", agent=self.name, attempt=attempt, error=str(exc)
                )
        raise AgentExecutionError(self.name, str(last_error))

    def _failed_result(self, error: Exception) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.FAILED,
            output={},
            confidence=0.0,
            error=str(error),
        )
