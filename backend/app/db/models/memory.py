import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class EpisodicMemory(Base, UUIDMixin, TimestampMixin):
    """One row per resolved interaction: what was asked, what was concluded.
    Used to recall 'what did we decide about X last time'."""

    __tablename__ = "episodic_memory"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    entities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False, default="resolved")


class ProjectMemory(Base, UUIDMixin, TimestampMixin):
    """Long-term rolling summary of a user's project/workspace context."""

    __tablename__ = "project_memory"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
