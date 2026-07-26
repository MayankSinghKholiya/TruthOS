from app.agents.base import BaseAgent
from app.agents.evidence_utils import format_evidence_block
from app.core.exceptions import AgentExecutionError
from app.rag.hybrid_retriever import RetrievedChunk
from app.schemas.agent import AgentResult, AgentStatus


class CoderAgent(BaseAgent):
    name = "coder"
    temperature = 0.2

    async def run(self, *, objective: str, evidence_chunks: list[RetrievedChunk]) -> AgentResult:
        evidence_block = format_evidence_block(evidence_chunks)
        try:
            output, model_used, retries = await self._run_with_retry(
                objective=objective, evidence=evidence_block
            )
        except AgentExecutionError as exc:
            return self._failed_result(exc)

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.OK if output.get("code") else AgentStatus.DEGRADED,
            output=output,
            confidence=0.75 if output.get("code") else 0.3,
            retries_used=retries,
            model_used=model_used,
        )
