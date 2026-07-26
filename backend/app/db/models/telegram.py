import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class TelegramLink(Base, UUIDMixin, TimestampMixin):
    """One Telegram chat linked per user - established via the /start <code>
    long-poll handshake in app.services.telegram_linking, never by a user
    typing their own chat_id (which can't be verified as theirs)."""

    __tablename__ = "telegram_links"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    telegram_chat_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WalletWatch(Base, UUIDMixin, TimestampMixin):
    """A wallet a user wants flagged for them - notified over Telegram when a
    dispute is filed against it, or when it's a counterparty in a dispute
    that leaves the other side Flagged."""

    __tablename__ = "wallet_watches"
    __table_args__ = (UniqueConstraint("user_id", "wallet_id", name="uq_wallet_watch_user_wallet"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    wallet_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
