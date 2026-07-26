"""Confidence DNA: aggregates five signals into one explainable trust score.

Signals (per README):
  - source_diversity     : how many distinct domains/providers back the answer
  - freshness            : how recent the evidence is
  - consensus            : how much the courtroom agents agreed (fewer/weaker
                            critic objections -> higher consensus)
  - evidence_quality     : mean reliability of the evidence items used
  - retrieval_confidence : mean relevance/rerank score from the RAG layer

Each signal is normalized to [0, 1]; the overall score is a weighted average
so any single weak signal can't be hidden by strong ones elsewhere.
"""
from datetime import datetime, timezone
from math import log2

from pydantic import BaseModel

from app.schemas.agent import EvidenceItem
from app.schemas.report import ConfidenceBreakdown

_WEIGHTS = {
    "source_diversity": 0.2,
    "freshness": 0.15,
    "consensus": 0.25,
    "evidence_quality": 0.25,
    "retrieval_confidence": 0.15,
}


class CritiqueSignal(BaseModel):
    objection_count: int = 0
    mean_objection_severity: float = 0.0


def _source_diversity(evidence: list[EvidenceItem]) -> float:
    if not evidence:
        return 0.0
    domains = {_domain(e.source_url) for e in evidence if e.source_url}
    if not domains:
        return 0.0
    # log-scaled: 1 domain -> ~0.3, 4+ distinct domains -> ~1.0
    return min(1.0, log2(len(domains) + 1) / log2(5))


def _domain(url: str | None) -> str | None:
    if not url:
        return None
    stripped = url.split("//")[-1]
    return stripped.split("/")[0].removeprefix("www.")


def _freshness(published_dates: list[str | None]) -> float:
    now = datetime.now(timezone.utc)
    scores = []
    for raw in published_dates:
        if not raw:
            continue
        try:
            published = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        age_days = max((now - published).days, 0)
        # full credit under 30 days old, linear decay to 0 credit at 3 years
        scores.append(max(0.0, 1.0 - age_days / (365 * 3)))
    if not scores:
        return 0.5  # unknown freshness -> neutral, not penalized to zero
    return sum(scores) / len(scores)


def _consensus(critique: CritiqueSignal) -> float:
    if critique.objection_count == 0:
        return 1.0
    penalty = min(1.0, (critique.objection_count * critique.mean_objection_severity) / 5)
    return max(0.0, 1.0 - penalty)


def _evidence_quality(evidence: list[EvidenceItem]) -> float:
    if not evidence:
        return 0.0
    return sum(e.reliability for e in evidence) / len(evidence)


def compute_confidence(
    *,
    evidence: list[EvidenceItem],
    published_dates: list[str | None],
    critique: CritiqueSignal,
    retrieval_scores: list[float],
) -> ConfidenceBreakdown:
    if not evidence:
        # No evidence at all means there is nothing to be confident about -
        # short-circuit rather than let a neutral freshness/consensus default
        # (no dates to judge, no objections because there's nothing to object
        # to) drag the overall score up from zero.
        return ConfidenceBreakdown(
            source_diversity=0.0,
            freshness=0.0,
            consensus=0.0,
            evidence_quality=0.0,
            retrieval_confidence=0.0,
            overall=0.0,
        )

    source_diversity = _source_diversity(evidence)
    freshness = _freshness(published_dates)
    consensus = _consensus(critique)
    evidence_quality = _evidence_quality(evidence)
    retrieval_confidence = (
        max(0.0, min(1.0, sum(retrieval_scores) / len(retrieval_scores)))
        if retrieval_scores
        else 0.0
    )

    overall = (
        source_diversity * _WEIGHTS["source_diversity"]
        + freshness * _WEIGHTS["freshness"]
        + consensus * _WEIGHTS["consensus"]
        + evidence_quality * _WEIGHTS["evidence_quality"]
        + retrieval_confidence * _WEIGHTS["retrieval_confidence"]
    )

    return ConfidenceBreakdown(
        source_diversity=round(source_diversity, 4),
        freshness=round(freshness, 4),
        consensus=round(consensus, 4),
        evidence_quality=round(evidence_quality, 4),
        retrieval_confidence=round(retrieval_confidence, 4),
        overall=round(overall, 4),
    )


# On-chain verification statuses, scored by how much they support the
# evidence being genuine. "pending"/"unverifiable"/"invalid_format"/
# "unsupported_chain" score neutral (0.5) - "couldn't check" must not cost
# confidence the same way "checked and it's fabricated" does.
_CHAIN_STATUS_SCORES = {
    "confirmed_match": 1.0,
    "confirmed": 0.9,
    "confirmed_mismatch": 0.1,
    "failed_onchain": 0.05,
    "not_found": 0.0,
    "pending": 0.5,
    "invalid_format": 0.5,
    "unsupported_chain": 0.5,
    "unverifiable": 0.5,
}


def compute_arbitration_confidence(
    *,
    evidence_count: int,
    match_score: float,
    discrepancies: list[dict],
    chain_verification_statuses: list[str] | None = None,
) -> dict:
    """Confidence DNA for TruthOS Court verdicts - a different domain from the
    research pipeline (no sources/freshness to speak of), so it uses four
    signals instead:

      - evidence_completeness  : how much evidence both sides actually submitted
      - evidence_decisiveness  : how clear-cut the verifier's match assessment
                                  was (near 0 or 1) vs. ambiguous (near 0.5)
      - narrative_consensus    : how low-severity the flagged discrepancies are
                                  (many severe discrepancies = a messier case)
      - chain_evidence_integrity : for any tx-reference evidence, whether the
                                  real blockchain data backs it up - computed
                                  from ChainVerificationService's results, not
                                  from anything the LLM said, so a fabricated
                                  transaction can't argue its way to a high score
    """
    if evidence_count == 0:
        return {
            "evidence_completeness": 0.0,
            "evidence_decisiveness": 0.0,
            "narrative_consensus": 0.0,
            "chain_evidence_integrity": 0.5,
            "overall": 0.0,
        }

    # match_score and each discrepancy's severity are LLM-supplied - clamp
    # before use, the same way retrieval_confidence above had to be, since an
    # out-of-[0,1] value here would push "overall" past the 0-100% range the
    # whole Confidence DNA contract promises.
    match_score = max(0.0, min(1.0, match_score))
    evidence_completeness = min(1.0, evidence_count / 4)
    evidence_decisiveness = abs(match_score - 0.5) * 2
    mean_severity = (
        max(0.0, min(1.0, sum(d.get("severity", 0.5) for d in discrepancies) / len(discrepancies)))
        if discrepancies
        else 0.0
    )
    narrative_consensus = max(0.0, 1.0 - mean_severity)

    statuses = chain_verification_statuses or []
    chain_evidence_integrity = (
        sum(_CHAIN_STATUS_SCORES.get(status, 0.5) for status in statuses) / len(statuses)
        if statuses
        else 0.5  # no on-chain evidence submitted at all -> neutral, not penalized
    )

    overall = (
        evidence_completeness + evidence_decisiveness + narrative_consensus + chain_evidence_integrity
    ) / 4

    return {
        "evidence_completeness": round(evidence_completeness, 4),
        "evidence_decisiveness": round(evidence_decisiveness, 4),
        "narrative_consensus": round(narrative_consensus, 4),
        "chain_evidence_integrity": round(chain_evidence_integrity, 4),
        "overall": round(overall, 4),
    }
