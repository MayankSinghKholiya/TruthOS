"""Shared contract every agent's input/output must satisfy.

Per the platform rule "each agent owns: prompt, inputs, outputs, tools, retry
policy, confidence" - AgentResult is the uniform envelope so the orchestrator
never needs to know an individual agent's internals.
"""
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    claim: str
    source_url: str | None = None
    source_title: str | None = None
    snippet: str
    reliability: float = Field(ge=0.0, le=1.0, description="Source trust score")


class AgentStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"  # succeeded via fallback model or partial evidence
    FAILED = "failed"


class AgentResult(BaseModel):
    agent_name: str
    status: AgentStatus
    output: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    reasoning: str | None = None
    retries_used: int = 0
    model_used: str | None = None
    error: str | None = None
