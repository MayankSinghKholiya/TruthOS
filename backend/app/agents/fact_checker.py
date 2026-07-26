from app.agents.base import BaseAgent
from app.agents.evidence_utils import format_evidence_block
from app.core.exceptions import AgentExecutionError
from app.rag.hybrid_retriever import RetrievedChunk
from app.schemas.agent import AgentResult, AgentStatus


class FactCheckerAgent(BaseAgent):
    name = "fact_checker"
    temperature = 0.0  # verification should be as deterministic as possible

    async def run(
        self, *, claims: list[dict], evidence_chunks: list[RetrievedChunk]
    ) -> AgentResult:
        evidence_block = format_evidence_block(evidence_chunks)
        claim_statements = [c.get("statement", "") for c in claims]
        try:
            output, model_used, retries = await self._run_with_retry(
                claims=claim_statements, evidence=evidence_block
            )
        except AgentExecutionError as exc:
            return self._failed_result(exc)

        verifications = output.get("verifications", [])
        verified_count = sum(1 for v in verifications if v.get("verdict") == "VERIFIED")
        confidence = verified_count / len(verifications) if verifications else 0.2

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.OK if verifications else AgentStatus.DEGRADED,
            output=output,
            confidence=round(confidence, 4),
            retries_used=retries,
            model_used=model_used,
        )
