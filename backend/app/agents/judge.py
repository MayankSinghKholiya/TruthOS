from app.agents.base import BaseAgent
from app.core.config import get_settings
from app.core.exceptions import AgentExecutionError
from app.schemas.agent import AgentResult, AgentStatus
from app.services.llm_router import LLMRouter


class JudgeAgent(BaseAgent):
    """Final authority in the AI Courtroom. Uses the platform's designated
    JUDGE_MODEL (typically the strongest available reasoning model) since
    this call determines the user-facing verdict."""

    name = "judge"
    temperature = 0.0

    def __init__(self, llm_router: LLMRouter) -> None:
        super().__init__(llm_router)
        self.model = get_settings().judge_model

    async def run(
        self,
        *,
        reconciliation: dict,
        critic_findings: dict,
        fact_check_results: dict,
    ) -> AgentResult:
        try:
            output, model_used, retries = await self._run_with_retry(
                reconciliation=reconciliation,
                critic_findings=critic_findings,
                fact_check_results=fact_check_results,
            )
        except AgentExecutionError as exc:
            return self._failed_result(exc)

        # verdict_confidence is LLM-supplied - clamp it, since AgentResult
        # requires [0,1] and a model that ignores that instruction would
        # otherwise crash this call with a validation error.
        confidence = max(0.0, min(1.0, float(output.get("verdict_confidence", 0.5))))

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.OK if output.get("verdict") else AgentStatus.DEGRADED,
            output=output,
            confidence=confidence,
            reasoning=output.get("executive_summary"),
            retries_used=retries,
            model_used=model_used,
        )
