from app.agents.base import BaseAgent
from app.agents.evidence_utils import format_evidence_block, to_evidence_items
from app.core.exceptions import AgentExecutionError
from app.rag.hybrid_retriever import RetrievedChunk
from app.schemas.agent import AgentResult, AgentStatus


class ResearchAgent(BaseAgent):
    """Builds the affirmative case in the AI Courtroom - the prosecution, in
    effect - grounded strictly in retrieved evidence."""

    name = "research"
    temperature = 0.3

    async def run(self, *, objective: str, evidence_chunks: list[RetrievedChunk]) -> AgentResult:
        evidence_block = format_evidence_block(evidence_chunks)
        try:
            output, model_used, retries = await self._run_with_retry(
                objective=objective, evidence=evidence_block
            )
        except AgentExecutionError as exc:
            return self._failed_result(exc)

        claims = output.get("claims", [])
        evidence_items = to_evidence_items(evidence_chunks)
        # Each claim's confidence is LLM-supplied - clamp the mean so a model
        # that ignores the [0,1] instruction can't push this past the range
        # AgentResult requires.
        mean_claim_confidence = (
            max(0.0, min(1.0, sum(c.get("confidence", 0.5) for c in claims) / len(claims)))
            if claims
            else 0.2
        )

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.OK if claims else AgentStatus.DEGRADED,
            output=output,
            confidence=round(mean_claim_confidence, 4),
            evidence=evidence_items,
            reasoning=output.get("summary"),
            retries_used=retries,
            model_used=model_used,
        )
