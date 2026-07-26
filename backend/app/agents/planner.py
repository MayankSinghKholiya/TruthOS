from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.schemas.agent import AgentResult, AgentStatus


class PlannerAgent(BaseAgent):
    name = "planner"
    temperature = 0.3

    async def run(self, *, query: str, context: str = "", memory: str = "") -> AgentResult:
        try:
            output, model_used, retries = await self._run_with_retry(
                query=query, context=context, memory=memory
            )
        except AgentExecutionError as exc:
            return self._failed_result(exc)

        sub_tasks = output.get("sub_tasks", [])
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.OK if sub_tasks else AgentStatus.DEGRADED,
            output=output,
            confidence=0.9 if sub_tasks else 0.3,
            reasoning=output.get("plan_rationale"),
            retries_used=retries,
            model_used=model_used,
        )
