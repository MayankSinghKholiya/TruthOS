"""LangGraph orchestration for TruthOS Court:

    File Dispute -> Fetch Reputation -> Claimant Case + Respondent Defense +
    Evidence Verification (parallel) -> Arbitrate -> Confidence -> Persist
    Verdict + Update Reputation

Mirrors app/graph/orchestrator.py's shape: each node wraps one agent (or an
independent group run concurrently), returns partial state, and the whole
graph is streamable over SSE the same way the research pipeline is.
"""
import asyncio
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.arbitrator import ArbitratorAgent
from app.agents.claimant import ClaimantAgent
from app.agents.dispute_utils import evidence_needing_forced_discrepancy, format_dispute_evidence
from app.agents.evidence_verifier import EvidenceVerifierAgent
from app.agents.respondent import RespondentAgent
from app.core.logging import get_logger
from app.db.models.dispute import AgentReputation, Dispute, DisputeVerdict
from app.graph.arbitration_state import ArbitrationState
from app.schemas.agent import AgentStatus
from app.schemas.chat import StreamEvent, StreamEventType
from app.schemas.dispute import DisputeVerdictRead
from app.services.confidence import compute_arbitration_confidence
from app.services.llm_router import LLMRouter
from app.services.reputation import apply_dispute_outcome
from app.services.reputation_store import ReputationStore

logger = get_logger(__name__)


class ArbitrationOrchestrator:
    def __init__(self, llm_router: LLMRouter, db_session: AsyncSession) -> None:
        self._session = db_session
        self._reputation_store = ReputationStore(db_session)

        self.claimant = ClaimantAgent(llm_router)
        self.respondent = RespondentAgent(llm_router)
        self.evidence_verifier = EvidenceVerifierAgent(llm_router)
        self.arbitrator = ArbitratorAgent(llm_router)

        self._graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(ArbitrationState)
        graph.add_node("fetch_reputation", self._fetch_reputation_node)
        graph.add_node("build_case", self._build_case_node)
        graph.add_node("arbitrate", self._arbitrate_node)
        graph.add_node("score_confidence", self._confidence_node)
        graph.add_node("persist", self._persist_node)

        graph.set_entry_point("fetch_reputation")
        graph.add_edge("fetch_reputation", "build_case")
        graph.add_edge("build_case", "arbitrate")
        graph.add_edge("arbitrate", "score_confidence")
        graph.add_edge("score_confidence", "persist")
        graph.add_edge("persist", END)
        return graph.compile()

    # ---- nodes ---------------------------------------------------------------

    async def _fetch_reputation_node(self, state: ArbitrationState) -> dict:
        claimant_rep = await self._reputation_store.get_or_create(state["claimant_wallet_id"])
        respondent_rep = await self._reputation_store.get_or_create(state["respondent_wallet_id"])
        return {
            "claimant_reputation": _reputation_snapshot(claimant_rep),
            "respondent_reputation": _reputation_snapshot(respondent_rep),
            "agent_trace": [],
        }

    async def _build_case_node(self, state: ArbitrationState) -> dict:
        evidence = state.get("evidence", [])
        claimant_result, respondent_result, verify_result = await asyncio.gather(
            self.claimant.run(
                task_description=state["task_description"],
                agreed_deliverable=state["agreed_deliverable"],
                actual_deliverable=state["actual_deliverable"],
                claimant_evidence=format_dispute_evidence(evidence, submitted_by="claimant"),
            ),
            self.respondent.run(
                task_description=state["task_description"],
                agreed_deliverable=state["agreed_deliverable"],
                actual_deliverable=state["actual_deliverable"],
                respondent_evidence=format_dispute_evidence(evidence, submitted_by="respondent"),
            ),
            self.evidence_verifier.run(
                agreed_deliverable=state["agreed_deliverable"],
                actual_deliverable=state["actual_deliverable"],
                all_evidence=format_dispute_evidence(evidence, include_verification=True),
            ),
        )

        evidence_assessment = _apply_chain_verification_safety_net(verify_result.output, evidence)

        return {
            "claimant_case": claimant_result.output,
            "respondent_defense": respondent_result.output,
            "evidence_assessment": evidence_assessment,
            "agent_trace": state.get("agent_trace", [])
            + [_trace(claimant_result), _trace(respondent_result), _trace(verify_result)],
        }

    async def _arbitrate_node(self, state: ArbitrationState) -> dict:
        result = await self.arbitrator.run(
            claimant_case=state.get("claimant_case", {}),
            respondent_defense=state.get("respondent_defense", {}),
            evidence_assessment=state.get("evidence_assessment", {}),
            claimant_reputation=state.get("claimant_reputation", {}),
            respondent_reputation=state.get("respondent_reputation", {}),
        )
        return {
            "verdict_output": result.output,
            "agent_trace": state.get("agent_trace", []) + [_trace(result)],
        }

    async def _confidence_node(self, state: ArbitrationState) -> dict:
        evidence = state.get("evidence", [])
        assessment = state.get("evidence_assessment", {})
        confidence = compute_arbitration_confidence(
            evidence_count=len(evidence),
            match_score=float(assessment.get("match_score", 0.0) or 0.0),
            discrepancies=assessment.get("discrepancies", []),
            chain_verification_statuses=[
                e["verification_status"] for e in evidence if e.get("verification_status")
            ],
        )
        return {"confidence": confidence}

    async def _persist_node(self, state: ArbitrationState) -> dict:
        verdict_output = state.get("verdict_output", {})
        confidence = state.get("confidence", {})
        assessment = state.get("evidence_assessment", {})

        claimant_fault, respondent_fault = _normalize_fault_split(
            verdict_output.get("claimant_fault_percentage", 50.0),
            verdict_output.get("respondent_fault_percentage", 50.0),
        )
        refund_recommendation = max(
            0.0, min(100.0, float(verdict_output.get("refund_recommendation_percentage", 50.0)))
        )

        verdict_row = DisputeVerdict(
            dispute_id=state["dispute_id"],
            verdict=verdict_output.get("verdict") or "Inconclusive",
            claimant_fault_percentage=claimant_fault,
            respondent_fault_percentage=respondent_fault,
            refund_recommendation_percentage=refund_recommendation,
            executive_summary=verdict_output.get("executive_summary", ""),
            reasoning=verdict_output.get("reasoning", ""),
            confidence_score=confidence.get("overall", 0.0),
            confidence_breakdown=confidence,
            evidence_timeline=assessment.get("evidence_timeline", []),
            counter_arguments=verdict_output.get("counter_arguments", []),
            agent_trace=state.get("agent_trace", []),
        )
        self._session.add(verdict_row)

        dispute = await self._session.get(Dispute, state["dispute_id"])
        if dispute is not None:
            dispute.status = "resolved"

        claimant_rep = await self._reputation_store.get_or_create(state["claimant_wallet_id"])
        respondent_rep = await self._reputation_store.get_or_create(state["respondent_wallet_id"])
        overall_confidence = confidence.get("overall", 0.0)
        escrow_amount = dispute.escrow_amount if dispute is not None else None
        apply_dispute_outcome(
            claimant_rep, claimant_fault, confidence_score=overall_confidence, escrow_amount=escrow_amount
        )
        apply_dispute_outcome(
            respondent_rep, respondent_fault, confidence_score=overall_confidence, escrow_amount=escrow_amount
        )

        await self._session.commit()
        # Returning a non-empty dict matters here: LangGraph's astream() has
        # been observed to yield None (not {}) for a terminal node that
        # returns no state updates, which crashes callers iterating
        # partial.keys() - see stream() below.
        return {"agent_trace": state.get("agent_trace", [])}

    # ---- public API -----------------------------------------------------------

    async def run(
        self,
        *,
        dispute_id: UUID,
        task_description: str,
        agreed_deliverable: str,
        actual_deliverable: str,
        claimant_wallet_id: str,
        respondent_wallet_id: str,
        evidence: list[dict],
    ) -> DisputeVerdictRead:
        await self._graph.ainvoke(
            self._initial_state(
                dispute_id=dispute_id,
                task_description=task_description,
                agreed_deliverable=agreed_deliverable,
                actual_deliverable=actual_deliverable,
                claimant_wallet_id=claimant_wallet_id,
                respondent_wallet_id=respondent_wallet_id,
                evidence=evidence,
            )
        )
        return await self._load_verdict(dispute_id)

    async def stream(
        self,
        *,
        dispute_id: UUID,
        task_description: str,
        agreed_deliverable: str,
        actual_deliverable: str,
        claimant_wallet_id: str,
        respondent_wallet_id: str,
        evidence: list[dict],
    ) -> AsyncIterator[StreamEvent]:
        initial_state = self._initial_state(
            dispute_id=dispute_id,
            task_description=task_description,
            agreed_deliverable=agreed_deliverable,
            actual_deliverable=actual_deliverable,
            claimant_wallet_id=claimant_wallet_id,
            respondent_wallet_id=respondent_wallet_id,
            evidence=evidence,
        )
        async for step in self._graph.astream(initial_state):
            for node_name, partial in step.items():
                yield StreamEvent(
                    type=StreamEventType.AGENT_COMPLETED,
                    agent_name=node_name,
                    data={"keys": list(partial.keys()) if partial else []},
                )
        verdict = await self._load_verdict(dispute_id)
        yield StreamEvent(type=StreamEventType.REPORT_READY, data=verdict.model_dump(mode="json"))

    def _initial_state(self, **kwargs) -> ArbitrationState:
        return {**kwargs, "agent_trace": []}  # type: ignore[typeddict-item]

    async def _load_verdict(self, dispute_id: UUID) -> DisputeVerdictRead:
        result = await self._session.execute(
            select(DisputeVerdict).where(DisputeVerdict.dispute_id == dispute_id)
        )
        row = result.scalar_one()
        return DisputeVerdictRead.model_validate(row)


_FORCED_DISCREPANCY_SEVERITY = {
    "not_found": 0.95,
    "failed_onchain": 0.9,
    "confirmed_mismatch": 0.85,
}
_FORCED_DISCREPANCY_REASON = {
    "not_found": "no such transaction exists on the stated chain",
    "failed_onchain": "the transaction exists on-chain but failed/reverted",
    "confirmed_mismatch": "the transaction's real on-chain value does not match what was claimed",
}


def _apply_chain_verification_safety_net(
    evidence_assessment: dict[str, Any], evidence: list[dict[str, Any]]
) -> dict[str, Any]:
    """Guarantees a fabricated/contradicted tx-reference always shows up as a
    discrepancy, even if the LLM's own output missed it - the same
    belt-and-suspenders approach as _normalize_fault_split below. Appends
    rather than replaces, so this only ever adds signal, never removes
    whatever the model itself already flagged."""
    flagged = evidence_needing_forced_discrepancy(evidence)
    if not flagged:
        return evidence_assessment

    discrepancies = list(evidence_assessment.get("discrepancies") or [])
    for item in flagged:
        discrepancies.append(
            {
                "description": (
                    f"On-chain check on evidence [{item['index']}] (submitted by {item['submitted_by']}): "
                    f"{_FORCED_DISCREPANCY_REASON[item['status']]}."
                ),
                "severity": _FORCED_DISCREPANCY_SEVERITY[item["status"]],
            }
        )
    return {**evidence_assessment, "discrepancies": discrepancies}


def _normalize_fault_split(claimant_fault_raw: Any, respondent_fault_raw: Any) -> tuple[float, float]:
    """Clamps and re-normalizes the Arbitrator's two fault percentages so
    they always sum to exactly 100 - the prompt asks for this, but LLMs
    don't reliably comply (can return values that don't sum to 100, exceed
    100 individually, or go negative), and a fault split that doesn't add up
    would visibly undermine trust in a product whose entire premise is
    transparent, correct scoring."""
    claimant_fault = max(0.0, min(100.0, float(claimant_fault_raw)))
    respondent_fault = max(0.0, min(100.0, float(respondent_fault_raw)))

    total = claimant_fault + respondent_fault
    if total <= 0:
        return 50.0, 50.0
    return claimant_fault / total * 100, respondent_fault / total * 100


def _reputation_snapshot(reputation: AgentReputation) -> dict:
    return {
        "trust_score": reputation.trust_score,
        "disputes_total": reputation.disputes_total,
        "disputes_at_fault": reputation.disputes_at_fault,
    }


def _trace(result) -> dict:
    return {
        "agent": result.agent_name,
        "status": result.status.value if isinstance(result.status, AgentStatus) else result.status,
        "confidence": result.confidence,
        "model_used": result.model_used,
        "retries_used": result.retries_used,
    }
