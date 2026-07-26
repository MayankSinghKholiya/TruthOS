from typing import Any

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.schemas.agent import AgentResult, AgentStatus


class FinanceAgent(BaseAgent):
    """Grounded in live market data from CoinGecko/AlphaVantage (fetched by
    the orchestrator via app.services.search_tools before this agent runs)."""

    name = "finance"
    temperature = 0.1

    async def run(self, *, objective: str, market_data: list[dict[str, Any]]) -> AgentResult:
        try:
            output, model_used, retries = await self._run_with_retry(
                objective=objective, market_data=market_data
            )
        except AgentExecutionError as exc:
            return self._failed_result(exc)

        confidence = 0.8 if market_data else 0.3  # no live data -> low confidence, not silence
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.OK if market_data else AgentStatus.DEGRADED,
            output=output,
            confidence=confidence,
            retries_used=retries,
            model_used=model_used,
        )
