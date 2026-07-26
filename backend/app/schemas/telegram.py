from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LinkStartRead(BaseModel):
    code: str
    bot_username: str | None
    expires_in_seconds: int


class LinkStatusRead(BaseModel):
    linked: bool
    telegram_username: str | None = None
    linked_at: datetime | None = None


class WalletWatchCreate(BaseModel):
    wallet_id: str
    label: str | None = Field(default=None, max_length=255)


class WalletWatchRead(BaseModel):
    id: UUID
    wallet_id: str
    label: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


__all__ = ["LinkStartRead", "LinkStatusRead", "WalletWatchCreate", "WalletWatchRead"]
