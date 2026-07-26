from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.schemas.agent import AgentResult, AgentStatus


class ClaimantAgent(BaseAgent):
    """Builds the strongest good-faith case for whoever filed the dispute."""

    name = "claimant"
    temperature = 0.3

    async def run(
        self,
        *,
        task_description: str,
        agreed_deliverable: str,
        actual_deliverable: str,
        claimant_evidence: str,
    ) -> AgentResult:
        try:
            output, model_used, retries = await self._run_with_retry(
                task_description=task_description,
                agreed_deliverable=agreed_deliverable,
                actual_deliverable=actual_deliverable,
                claimant_evidence=claimant_evidence,
            )
        except AgentExecutionError as exc:
            return self._failed_result(exc)

        claims = output.get("claims", [])
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.OK if claims else AgentStatus.DEGRADED,
            output=output,
            confidence=0.75 if claims else 0.3,
            reasoning=output.get("case_summary"),
            retries_used=retries,
            model_used=model_used,
        )
