from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.schemas.agent import AgentResult, AgentStatus


class CriticAgent(BaseAgent):
    """Plays both the Skeptic and the Devil's Advocate in the AI Courtroom."""

    name = "critic"
    temperature = 0.5

    async def run(self, *, facts: dict, claims: list[dict]) -> AgentResult:
        try:
            output, model_used, retries = await self._run_with_retry(facts=facts, claims=claims)
        except AgentExecutionError as exc:
            return self._failed_result(exc)

        objections = output.get("skeptic_objections", [])
        # more/stronger objections => lower confidence in the case being reviewed,
        # but higher confidence that the critique itself is substantive.
        # severity is LLM-supplied and the prompt's [0,1] instruction isn't
        # always followed exactly - clamp before it can push confidence
        # outside the range AgentResult requires.
        mean_severity = (
            max(0.0, min(1.0, sum(o.get("severity", 0.5) for o in objections) / len(objections)))
            if objections
            else 0.0
        )

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.OK,
            output=output,
            confidence=round(0.5 + mean_severity / 2, 4) if objections else 0.6,
            reasoning=output.get("devils_advocate_case", {}).get("summary"),
            retries_used=retries,
            model_used=model_used,
        )
