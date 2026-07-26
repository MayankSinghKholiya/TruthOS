"""Cross-encoder re-ranking: takes the union of BM25 + dense candidates and
re-scores them jointly against the query for the final top-k."""
import math
from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.core.config import get_settings


@lru_cache
def get_cross_encoder() -> CrossEncoder:
    settings = get_settings()
    return CrossEncoder(settings.cross_encoder_model)


def rerank(query: str, candidates: list[str], top_k: int = 8) -> list[tuple[int, float]]:
    """Returns (candidate_index, score) pairs sorted by descending relevance.

    Scores are squashed to (0, 1) via sigmoid before returning: CrossEncoder
    models output unbounded relevance logits (can be negative or >>1), not
    calibrated probabilities, but every downstream consumer (Confidence DNA's
    retrieval_confidence signal, evidence reliability scoring) assumes a
    normalized [0,1] input - an un-squashed score silently broke that
    contract (confidence >100% was observed in practice) until this fix.
    """
    if not candidates:
        return []
    model = get_cross_encoder()
    pairs = [(query, candidate) for candidate in candidates]
    raw_scores = model.predict(pairs)
    scores = [1 / (1 + math.exp(-float(score))) for score in raw_scores]
    ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
    return ranked[:top_k]
