"""Reputation scoring: converts a resolved dispute's fault percentage into an
update to a party's running trust score. A new wallet starts at a neutral 75
rather than 0 or 100 - unproven, not presumed guilty or perfect."""
import math

from app.db.models.dispute import AgentReputation

_BASE_LEARNING_RATE = 0.35
_MIN_LEARNING_RATE = 0.05
_MAX_LEARNING_RATE = 0.35
DEFAULT_TRUST_SCORE = 75.0

# Escrow size at which the stakes-weighting saturates (log-scaled, so a
# $100k dispute doesn't swing trust ~100x harder than a $1k one - it just
# reaches full weight sooner).
_REFERENCE_ESCROW = 1000.0


def _effective_learning_rate(confidence_score: float, escrow_amount: float | None) -> float:
    """How much *this* dispute is allowed to move the running trust score.

    A fixed learning rate treats a coin-flip 51% verdict over a $5 task the
    same as a decisive 95%-confidence verdict over a $50,000 one - both used
    to move the score by the same amount. They shouldn't: confidence and
    stakes are scaled in independently, each clamped to [0.4, 1.0] rather
    than [0, 1] so a single dispute is never reduced to *zero* weight - even
    an uncertain, low-stakes case is still real signal, just weak signal.
    """
    confidence_factor = 0.4 + 0.6 * max(0.0, min(1.0, confidence_score))
    escrow_size = max(0.0, escrow_amount or 0.0)
    escrow_ratio = math.log1p(escrow_size) / math.log1p(_REFERENCE_ESCROW)
    escrow_factor = 0.4 + 0.6 * min(1.0, escrow_ratio)
    rate = _BASE_LEARNING_RATE * confidence_factor * escrow_factor
    return max(_MIN_LEARNING_RATE, min(_MAX_LEARNING_RATE, rate))


def apply_dispute_outcome(
    reputation: AgentReputation,
    fault_percentage: float,
    *,
    confidence_score: float = 1.0,
    escrow_amount: float | None = None,
) -> None:
    """Mutates `reputation` in place given this party's fault percentage
    (0-100) in a just-resolved dispute. confidence_score (the verdict's own
    Confidence DNA overall score) and escrow_amount scale how much this
    specific dispute is allowed to move the running score - see
    _effective_learning_rate."""
    reputation.disputes_total += 1
    if fault_percentage > 50:
        reputation.disputes_at_fault += 1

    total = reputation.disputes_total
    reputation.avg_fault_percentage = (
        (reputation.avg_fault_percentage * (total - 1)) + fault_percentage
    ) / total

    learning_rate = _effective_learning_rate(confidence_score, escrow_amount)
    target = 100.0 - fault_percentage
    blended = reputation.trust_score * (1 - learning_rate) + target * learning_rate
    reputation.trust_score = max(0.0, min(100.0, blended))


def standing_label(trust_score: float) -> str:
    if trust_score >= 80:
        return "Trusted"
    if trust_score >= 50:
        return "Neutral"
    return "Flagged"
