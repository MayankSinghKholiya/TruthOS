from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.schemas.agent import AgentResult, AgentStatus


class EvidenceVerifierAgent(BaseAgent):
    """Objectively compares agreed vs. actual deliverable using all submitted
    evidence - takes no side, only assesses factual match quality."""

    name = "evidence_verifier"
    temperature = 0.0

    async def run(
        self, *, agreed_deliverable: str, actual_deliverable: str, all_evidence: str
    ) -> AgentResult:
        try:
            output, model_used, retries = await self._run_with_retry(
                agreed_deliverable=agreed_deliverable,
                actual_deliverable=actual_deliverable,
                all_evidence=all_evidence,
            )
        except AgentExecutionError as exc:
            return self._failed_result(exc)

        match_score = output.get("match_score")
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.OK if match_score is not None else AgentStatus.DEGRADED,
            output=output,
            confidence=0.8 if match_score is not None else 0.3,
            retries_used=retries,
            model_used=model_used,
        )
