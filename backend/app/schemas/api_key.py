from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    wallet_id: str
    label: str | None = Field(default=None, max_length=255)


class ApiKeyCreated(BaseModel):
    """Returned exactly once, at creation - the raw key is never retrievable
    again afterward, only its prefix (for identifying it in a list) survives."""

    id: UUID
    key: str
    key_prefix: str
    wallet_id: str
    label: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyRead(BaseModel):
    id: UUID
    key_prefix: str
    wallet_id: str
    label: str | None
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


__all__ = ["ApiKeyCreate", "ApiKeyCreated", "ApiKeyRead"]
