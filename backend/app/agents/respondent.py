from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.schemas.agent import AgentResult, AgentStatus


class RespondentAgent(BaseAgent):
    """Builds the strongest good-faith defense for the party the dispute was
    filed against."""

    name = "respondent"
    temperature = 0.3

    async def run(
        self,
        *,
        task_description: str,
        agreed_deliverable: str,
        actual_deliverable: str,
        respondent_evidence: str,
    ) -> AgentResult:
        try:
            output, model_used, retries = await self._run_with_retry(
                task_description=task_description,
                agreed_deliverable=agreed_deliverable,
                actual_deliverable=actual_deliverable,
                respondent_evidence=respondent_evidence,
            )
        except AgentExecutionError as exc:
            return self._failed_result(exc)

        rebuttals = output.get("rebuttals", [])
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.OK if rebuttals else AgentStatus.DEGRADED,
            output=output,
            confidence=0.75 if rebuttals else 0.3,
            reasoning=output.get("defense_summary"),
            retries_used=retries,
            model_used=model_used,
        )
