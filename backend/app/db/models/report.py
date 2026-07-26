import uuid
from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Report(Base, UUIDMixin, TimestampMixin):
    """Persisted layered report: Verdict, Executive Summary, Confidence Dashboard,
    Evidence, Counter Arguments, Deep Dive, References."""

    __tablename__ = "reports"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[str] = mapped_column(String(500), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    counter_arguments: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    deep_dive: Mapped[str] = mapped_column(Text, nullable=False, default="")
    references: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    agent_trace: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    entity_ambiguity: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    session: Mapped["ChatSession"] = relationship(back_populates="reports")  # noqa: F821
