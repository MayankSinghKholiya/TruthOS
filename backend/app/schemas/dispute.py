from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.report import CounterArgument


class EvidenceInput(BaseModel):
    submitted_by: str = Field(pattern="^(claimant|respondent)$")
    evidence_type: str  # chat_log | deliverable | tx_reference | document | other
    content: str
    url: str | None = None
    # Required (semantically) only when evidence_type == "tx_reference" - which
    # chain the referenced transaction hash should be checked against. Left
    # optional at the schema level so a missing chain degrades to an
    # "invalid_format" verification result instead of rejecting the whole
    # dispute filing over one malformed evidence item.
    chain: str | None = None


class DisputeCreate(BaseModel):
    claimant_wallet_id: str
    respondent_wallet_id: str
    task_description: str
    agreed_deliverable: str
    actual_deliverable: str
    escrow_amount: float | None = None
    evidence: list[EvidenceInput] = Field(default_factory=list)


class AgentDisputeCreate(BaseModel):
    """Filing shape for the agent-callable POST /disputes/agent endpoint.
    claimant_wallet_id is deliberately absent - it's derived from the caller's
    API key so an agent can never file a dispute claiming to be a wallet it
    doesn't hold a key for."""

    respondent_wallet_id: str
    task_description: str
    agreed_deliverable: str
    actual_deliverable: str
    escrow_amount: float | None = None
    evidence: list[EvidenceInput] = Field(default_factory=list)
    idempotency_key: str | None = Field(default=None, max_length=255)
    callback_url: str | None = Field(default=None, max_length=2000)


class ChainVerificationRead(BaseModel):
    status: str
    chain: str | None = None
    tx_hash: str | None = None
    explorer_url: str | None = None
    from_address: str | None = None
    to_address: str | None = None
    value_native: float | None = None
    block_number: int | None = None
    claimed_amount: float | None = None
    reason: str | None = None
    supported_chains: list[str] | None = None


class DisputeEvidenceRead(BaseModel):
    id: UUID
    submitted_by: str
    evidence_type: str
    content: str
    url: str | None
    chain: str | None
    verification_status: str | None
    verification_details: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DisputeRead(BaseModel):
    id: UUID
    claimant_wallet_id: str
    respondent_wallet_id: str
    task_description: str
    agreed_deliverable: str
    actual_deliverable: str
    escrow_amount: float | None
    status: str
    created_at: datetime
    evidence: list[DisputeEvidenceRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class EvidenceTimelineEntry(BaseModel):
    submitted_by: str
    evidence_type: str
    summary: str
    weight: float = Field(ge=0.0, le=1.0)


class DisputeVerdictRead(BaseModel):
    id: UUID | None = None
    dispute_id: UUID
    verdict: str
    claimant_fault_percentage: float
    respondent_fault_percentage: float
    refund_recommendation_percentage: float
    executive_summary: str
    reasoning: str
    confidence_score: float
    confidence_breakdown: dict
    evidence_timeline: list[EvidenceTimelineEntry]
    counter_arguments: list[CounterArgument]
    agent_trace: list[dict]
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReputationRead(BaseModel):
    wallet_id: str
    trust_score: float
    disputes_total: int
    disputes_at_fault: int
    avg_fault_percentage: float
    completed_tasks: int
    standing: str

    model_config = {"from_attributes": True}


class DisputeHistoryEntry(BaseModel):
    """One past dispute this wallet was party to - the actual evidence
    behind its reputation score, so a red flag is never just a bare number."""

    dispute_id: UUID
    role: str  # claimant | respondent
    task_description: str
    status: str
    verdict: str | None = None
    fault_percentage: float | None = None
    created_at: datetime


__all__ = [
    "EvidenceInput",
    "DisputeCreate",
    "AgentDisputeCreate",
    "ChainVerificationRead",
    "DisputeEvidenceRead",
    "DisputeRead",
    "EvidenceTimelineEntry",
    "DisputeVerdictRead",
    "ReputationRead",
    "DisputeHistoryEntry",
]
