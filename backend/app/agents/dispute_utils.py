"""Formats submitted dispute evidence into the indexed text blocks the
arbitration agents expect in their prompts."""
from typing import Any

_STATUS_DESCRIPTIONS = {
    "confirmed_match": "CONFIRMED - the on-chain transaction exists and its value matches what was claimed.",
    "confirmed_mismatch": "CONTRADICTED - the on-chain transaction exists but its value does NOT match what was claimed.",
    "confirmed": "CONFIRMED - the on-chain transaction exists and succeeded (no claimed amount to compare against).",
    "failed_onchain": "CONTRADICTED - this transaction exists on-chain but FAILED/reverted, so it cannot support a claim of a completed payment.",
    "not_found": "CONTRADICTED - no such transaction exists on the stated chain. This evidence cannot be genuine as described.",
    "pending": "UNRESOLVED - the transaction exists but is not yet confirmed on-chain.",
    "invalid_format": "UNRESOLVED - no valid transaction hash/chain could be parsed from this evidence.",
    "unsupported_chain": "UNRESOLVED - the stated chain isn't one TruthOS Court can check.",
    "unverifiable": "UNRESOLVED - the chain's RPC endpoint could not be reached to check this.",
}


def format_dispute_evidence(
    evidence: list[dict[str, Any]], *, submitted_by: str | None = None, include_verification: bool = False
) -> str:
    filtered = [e for e in evidence if submitted_by is None or e["submitted_by"] == submitted_by]
    if not filtered:
        return "(no evidence submitted)"
    lines = []
    for i, item in enumerate(evidence):
        if submitted_by is not None and item["submitted_by"] != submitted_by:
            continue
        line = f"[{i}] ({item['submitted_by']}, {item['evidence_type']}): {item['content']}"
        if include_verification and item.get("verification_status"):
            line += f"\n    ON-CHAIN CHECK: {_STATUS_DESCRIPTIONS.get(item['verification_status'], item['verification_status'])}"
        lines.append(line)
    return "\n".join(lines)


def evidence_needing_forced_discrepancy(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Evidence whose on-chain check contradicts the submitter's claim outright
    (fabricated, mismatched, or failed transactions). Used as a deterministic
    safety net so a fabricated tx-reference is never silently absorbed into a
    verdict just because the LLM's own discrepancy list missed it - the same
    "don't fully trust the model" philosophy as _normalize_fault_split."""
    flagged = []
    for i, item in enumerate(evidence):
        status = item.get("verification_status")
        if status in {"confirmed_mismatch", "failed_onchain", "not_found"}:
            flagged.append({"index": i, "status": status, "submitted_by": item.get("submitted_by")})
    return flagged
