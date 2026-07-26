from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.schemas.agent import AgentResult, AgentStatus


class TruthAgent(BaseAgent):
    """The Truth Engine: reconciles Research/FactChecker/Critic outputs into
    facts vs. opinions vs. open uncertainty, and makes the final call on
    whether the query's subject was ambiguous (see entity_ambiguity)."""

    name = "truth"
    temperature = 0.1

    async def run(
        self,
        *,
        research_claims: list[dict],
        fact_check_findings: list[dict],
        evidence_consistency: dict,
        critic_objections: list[dict],
    ) -> AgentResult:
        try:
            output, model_used, retries = await self._run_with_retry(
                research_claims=research_claims,
                fact_check_findings=fact_check_findings,
                evidence_consistency=evidence_consistency,
                critic_objections=critic_objections,
            )
        except AgentExecutionError as exc:
            return self._failed_result(exc)

        facts = output.get("reconciled_facts", [])
        # certainty is LLM-supplied per fact - clamp the mean so it can't
        # carry an out-of-range value into the arithmetic below.
        mean_certainty = (
            max(0.0, min(1.0, sum(f.get("certainty", 0.5) for f in facts) / len(facts)))
            if facts
            else 0.2
        )
        unresolved = output.get("unresolved_uncertainty", [])
        is_ambiguous = output.get("entity_ambiguity", {}).get("is_ambiguous", False)

        confidence = mean_certainty * (1 - 0.05 * len(unresolved))
        if is_ambiguous:
            # An unresolved "which real-world thing is this even about" is a
            # bigger credibility hit than ordinary open uncertainty - halve
            # confidence rather than let per-item penalties understate it.
            confidence *= 0.5
        # A long unresolved_uncertainty list can drive the multiplier
        # negative - clamp the final value, since AgentResult.confidence
        # requires [0,1].
        confidence = max(0.0, min(1.0, confidence))

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.OK if facts else AgentStatus.DEGRADED,
            output=output,
            confidence=round(confidence, 4),
            retries_used=retries,
            model_used=model_used,
        )
