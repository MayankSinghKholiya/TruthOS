from typing import Any, TypedDict
from uuid import UUID


class ArbitrationState(TypedDict, total=False):
    dispute_id: UUID
    task_description: str
    agreed_deliverable: str
    actual_deliverable: str
    claimant_wallet_id: str
    respondent_wallet_id: str
    evidence: list[dict[str, Any]]

    claimant_case: dict[str, Any]
    respondent_defense: dict[str, Any]
    evidence_assessment: dict[str, Any]
    claimant_reputation: dict[str, Any]
    respondent_reputation: dict[str, Any]

    verdict_output: dict[str, Any]
    confidence: dict[str, Any]
    agent_trace: list[dict[str, Any]]
