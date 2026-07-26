from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.schemas.agent import AgentResult, AgentStatus


class MemoryAgent(BaseAgent):
    """Compresses a resolved investigation into a durable memory entry.
    Storage itself is handled by app.memory.manager.MemoryManager - this
    agent only decides *what* is worth remembering."""

    name = "memory"
    temperature = 0.2

    async def run(self, *, query: str, verdict: str, executive_summary: str) -> AgentResult:
        try:
            output, model_used, retries = await self._run_with_retry(
                query=query, verdict=verdict, executive_summary=executive_summary
            )
        except AgentExecutionError as exc:
            return self._failed_result(exc)

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.OK if output.get("summary") else AgentStatus.DEGRADED,
            output=output,
            confidence=0.8 if output.get("summary") else 0.3,
            retries_used=retries,
            model_used=model_used,
        )
