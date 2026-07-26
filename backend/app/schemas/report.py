from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.schemas.agent import EvidenceItem


class CounterArgument(BaseModel):
    argument: str
    raised_by: str
    strength: float


class ConfidenceBreakdown(BaseModel):
    source_diversity: float
    freshness: float
    consensus: float
    evidence_quality: float
    retrieval_confidence: float
    overall: float


class ReferenceItem(BaseModel):
    title: str
    url: str | None = None
    published_at: str | None = None


class EntityAmbiguity(BaseModel):
    """Set by the Truth Engine when the query's subject (an acronym, common
    name, etc.) could plausibly refer to more than one distinct real-world
    entity/event and the evidence doesn't clearly settle on one - surfaced
    explicitly rather than letting the Judge silently pick an interpretation."""

    is_ambiguous: bool
    explanation: str = ""


class LayeredReport(BaseModel):
    """The 7-layer output contract: Verdict, Executive Summary, Confidence
    Dashboard, Evidence, Counter Arguments, Deep Dive, References."""

    id: UUID | None = None
    query: str
    verdict: str
    executive_summary: str
    confidence: ConfidenceBreakdown
    evidence: list[EvidenceItem]
    counter_arguments: list[CounterArgument]
    deep_dive: str
    references: list[ReferenceItem]
    agent_trace: list[dict[str, Any]] = []
    entity_ambiguity: EntityAmbiguity | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
