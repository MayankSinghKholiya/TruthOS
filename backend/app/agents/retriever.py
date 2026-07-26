from datetime import datetime, timezone

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.schemas.agent import AgentResult, AgentStatus


class RetrieverAgent(BaseAgent):
    """Performs query expansion; the actual fetch is done by
    app.rag.hybrid_retriever.HybridRetriever using the queries this agent
    produces."""

    name = "retriever"
    temperature = 0.4

    async def run(self, *, objective: str, query: str, kg_context: str = "") -> AgentResult:
        try:
            output, model_used, retries = await self._run_with_retry(
                objective=objective,
                query=query,
                current_date=datetime.now(timezone.utc).date().isoformat(),
                kg_context=kg_context or "(none)",
            )
        except AgentExecutionError as exc:
            return self._failed_result(exc)

        queries = output.get("queries", [])
        if query not in queries:
            queries.append(query)  # always keep the literal query as a fallback candidate
        output["queries"] = queries

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.OK if queries else AgentStatus.DEGRADED,
            output=output,
            confidence=0.85 if len(queries) > 1 else 0.5,
            retries_used=retries,
            model_used=model_used,
        )
