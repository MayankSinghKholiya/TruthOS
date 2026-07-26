import uuid
from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Dispute(Base, UUIDMixin, TimestampMixin):
    """A filed agent-to-agent dispute: what was agreed, what was delivered,
    and by whom. Resolved by the arbitration pipeline into a DisputeVerdict."""

    __tablename__ = "disputes"

    filed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claimant_wallet_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    respondent_wallet_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    task_description: Mapped[str] = mapped_column(Text, nullable=False)
    agreed_deliverable: Mapped[str] = mapped_column(Text, nullable=False)
    actual_deliverable: Mapped[str] = mapped_column(Text, nullable=False)
    escrow_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    # Set only when filed via the agent-callable API (POST /disputes/agent).
    # Fired once with the final verdict when arbitration completes so a
    # calling agent doesn't have to poll.
    callback_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    evidence: Mapped[list["DisputeEvidence"]] = relationship(
        back_populates="dispute", cascade="all, delete-orphan"
    )
    verdict: Mapped["DisputeVerdict | None"] = relationship(
        back_populates="dispute", cascade="all, delete-orphan", uselist=False
    )


class DisputeEvidence(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "dispute_evidence"

    dispute_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("disputes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    submitted_by: Mapped[str] = mapped_column(String(20), nullable=False)  # claimant | respondent
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # Populated only for evidence_type == "tx_reference": which chain the
    # referenced transaction is claimed to be on, and the result of actually
    # checking it against that chain's RPC (see app.services.chain_verification).
    # verification_status is None for non-tx_reference evidence - there is
    # nothing on-chain to check, which is distinct from "unverifiable".
    chain: Mapped[str | None] = mapped_column(String(50), nullable=True)
    verification_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    verification_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    dispute: Mapped["Dispute"] = relationship(back_populates="evidence")


class DisputeVerdict(Base, UUIDMixin, TimestampMixin):
    """The arbitration engine's resolution: fault split, refund recommendation,
    reasoning, and the full agent trace/confidence breakdown - the arbitration
    analog of app.db.models.report.Report."""

    __tablename__ = "dispute_verdicts"

    dispute_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("disputes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    verdict: Mapped[str] = mapped_column(String(500), nullable=False)
    claimant_fault_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    respondent_fault_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    refund_recommendation_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    evidence_timeline: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    counter_arguments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    agent_trace: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    dispute: Mapped["Dispute"] = relationship(back_populates="verdict")


class AgentReputation(Base, UUIDMixin, TimestampMixin):
    """Running trust score per wallet/agent identity, updated after every
    resolved dispute involving that wallet."""

    __tablename__ = "agent_reputation"

    wallet_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=75.0)
    disputes_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    disputes_at_fault: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_fault_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    completed_tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
