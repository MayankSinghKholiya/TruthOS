from app.agents.base import BaseAgent
from app.core.config import get_settings
from app.core.exceptions import AgentExecutionError
from app.schemas.agent import AgentResult, AgentStatus
from app.services.llm_router import LLMRouter


class ArbitratorAgent(BaseAgent):
    """Final neutral authority in TruthOS Court. Uses the platform's
    strongest available model since this call determines real fault/refund
    outcomes, just like JudgeAgent does for the research courtroom."""

    name = "arbitrator"
    temperature = 0.0

    def __init__(self, llm_router: LLMRouter) -> None:
        super().__init__(llm_router)
        self.model = get_settings().judge_model

    async def run(
        self,
        *,
        claimant_case: dict,
        respondent_defense: dict,
        evidence_assessment: dict,
        claimant_reputation: dict,
        respondent_reputation: dict,
    ) -> AgentResult:
        try:
            output, model_used, retries = await self._run_with_retry(
                claimant_case=claimant_case,
                respondent_defense=respondent_defense,
                evidence_assessment=evidence_assessment,
                claimant_reputation=claimant_reputation,
                respondent_reputation=respondent_reputation,
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
