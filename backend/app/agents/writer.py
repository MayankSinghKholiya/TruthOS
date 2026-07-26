from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.schemas.agent import AgentResult, AgentStatus


class WriterAgent(BaseAgent):
    """Polishes the Judge's raw verdict/summary into final user-facing copy.
    Never introduces new claims - purely a rephrasing/formatting pass."""

    name = "writer"
    temperature = 0.4

    async def run(
        self, *, verdict: str, executive_summary: str, deep_dive: str, tone: str = "plain, direct"
    ) -> AgentResult:
        try:
            output, model_used, retries = await self._run_with_retry(
                verdict=verdict, executive_summary=executive_summary, deep_dive=deep_dive, tone=tone
            )
        except AgentExecutionError as exc:
            return self._failed_result(exc)

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.OK if output.get("executive_summary") else AgentStatus.DEGRADED,
            output=output,
            confidence=0.9 if output.get("executive_summary") else 0.4,
            retries_used=retries,
            model_used=model_used,
        )
