import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class ApiKey(Base, UUIDMixin, TimestampMixin):
    """A credential letting another agent (not a human browser session) call
    the agent-callable Court endpoints as a given wallet. Only key_hash is
    ever stored - the raw key is returned exactly once, at creation."""

    __tablename__ = "api_keys"

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    wallet_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # A regular key can only ever file a dispute as the wallet it was minted
    # for (claimant_wallet_id is forced server-side, never caller-supplied).
    # A bridge key is for a trusted neutral relay - e.g. the OKX ASP
    # marketplace integration - that arbitrates disputes between two OTHER
    # wallets it isn't a party to, so it alone may supply an explicit
    # claimant_wallet_id. Never set this from user-facing key-creation input;
    # it's only ever True for keys minted by our own operator tooling.
    is_bridge: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
