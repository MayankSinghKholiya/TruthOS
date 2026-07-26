from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ChatSessionCreate(BaseModel):
    title: str | None = None


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
