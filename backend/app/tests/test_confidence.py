from datetime import datetime, timedelta, timezone

from app.schemas.agent import EvidenceItem
from app.services.confidence import CritiqueSignal, compute_confidence


def _recent_date(days_ago: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def test_confidence_high_when_evidence_is_strong_diverse_and_uncontested():
    evidence = [
        EvidenceItem(
            claim="a", source_url="https://reuters.com/x", snippet="s1", reliability=0.9
        ),
        EvidenceItem(
            claim="b", source_url="https://nature.com/y", snippet="s2", reliability=0.95
        ),
        EvidenceItem(claim="c", source_url="https://mit.edu/z", snippet="s3", reliability=0.9),
    ]
    breakdown = compute_confidence(
        evidence=evidence,
        published_dates=[_recent_date(), _recent_date(2), _recent_date(1)],
        critique=CritiqueSignal(objection_count=0, mean_objection_severity=0.0),
        retrieval_scores=[0.9, 0.85, 0.88],
    )
    assert breakdown.overall > 0.75
    assert breakdown.consensus == 1.0


def test_confidence_low_with_no_evidence():
    breakdown = compute_confidence(
        evidence=[],
        published_dates=[],
        critique=CritiqueSignal(objection_count=0, mean_objection_severity=0.0),
        retrieval_scores=[],
    )
    assert breakdown.overall == 0.0


def test_confidence_penalized_by_strong_critic_objections():
    evidence = [
        EvidenceItem(claim="a", source_url="https://x.com/1", snippet="s1", reliability=0.8),
    ]
    high_consensus = compute_confidence(
        evidence=evidence,
        published_dates=[_recent_date()],
        critique=CritiqueSignal(objection_count=0, mean_objection_severity=0.0),
        retrieval_scores=[0.8],
    )
    low_consensus = compute_confidence(
        evidence=evidence,
        published_dates=[_recent_date()],
        critique=CritiqueSignal(objection_count=5, mean_objection_severity=0.9),
        retrieval_scores=[0.8],
    )
    assert low_consensus.consensus < high_consensus.consensus
    assert low_consensus.overall < high_consensus.overall


def test_confidence_never_exceeds_one_even_with_unnormalized_retrieval_scores():
    # Regression test: cross-encoder relevance logits are unbounded (can be
    # well above 1 or negative) - a real query once produced retrieval_score
    # 5.77, which drove "overall" confidence to 1.5251 (over 100%) before
    # compute_confidence started clamping this signal defensively.
    evidence = [
        EvidenceItem(claim="a", source_url="https://bbc.com/1", snippet="s1", reliability=0.9),
    ]
    breakdown = compute_confidence(
        evidence=evidence,
        published_dates=[None],
        critique=CritiqueSignal(),
        retrieval_scores=[5.7676],
    )
    assert breakdown.retrieval_confidence == 1.0
    assert breakdown.overall <= 1.0


def test_single_domain_scores_lower_diversity_than_multiple_domains():
    single_domain = [
        EvidenceItem(claim="a", source_url="https://x.com/1", snippet="s1", reliability=0.8),
        EvidenceItem(claim="b", source_url="https://x.com/2", snippet="s2", reliability=0.8),
    ]
    multi_domain = [
        EvidenceItem(claim="a", source_url="https://x.com/1", snippet="s1", reliability=0.8),
        EvidenceItem(claim="b", source_url="https://y.com/2", snippet="s2", reliability=0.8),
        EvidenceItem(claim="c", source_url="https://z.com/3", snippet="s3", reliability=0.8),
    ]
    single_breakdown = compute_confidence(
        evidence=single_domain,
        published_dates=[None, None],
        critique=CritiqueSignal(),
        retrieval_scores=[0.7, 0.7],
    )
    multi_breakdown = compute_confidence(
        evidence=multi_domain,
        published_dates=[None, None, None],
        critique=CritiqueSignal(),
        retrieval_scores=[0.7, 0.7, 0.7],
    )
    assert multi_breakdown.source_diversity > single_breakdown.source_diversity
