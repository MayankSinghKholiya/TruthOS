from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    title: str | None = None


class AgentChatQueryCreate(BaseModel):
    """Filing shape for the agent-callable POST /chat/agent/query endpoint -
    the Verified Answers counterpart to Court's POST /disputes/agent. Auth is
    an X-API-Key; the session/report this creates is owned by the key's
    human creator, same attribution pattern as agent-filed disputes."""

    query: str
    idempotency_key: str | None = Field(default=None, max_length=255)
    callback_url: str | None = Field(default=None, max_length=2000)


class ChatSessionRead(BaseModel):
    id: UUID
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageRead(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime
    meta: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class ChatQueryRequest(BaseModel):
    session_id: UUID | None = None
    query: str


class StreamEventType:
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    TOKEN = "token"
    REPORT_READY = "report_ready"
    ERROR = "error"


class StreamEvent(BaseModel):
    type: str
    agent_name: str | None = None
    data: dict
