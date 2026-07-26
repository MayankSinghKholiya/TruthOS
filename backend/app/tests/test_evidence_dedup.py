from app.agents.evidence_utils import deduplicate_evidence, remap_claim_evidence_indices
from app.rag.hybrid_retriever import RetrievedChunk


def _chunk(text: str, url: str | None, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        text=text,
        source_url=url,
        source_title=None,
        published_at=None,
        source="web",
        retrieval_score=score,
    )


def test_dedup_keeps_highest_scoring_copy_per_url():
    chunks = [
        _chunk("low quality summary", "https://a.com/x", score=0.3),
        _chunk("unrelated", "https://b.com/y", score=0.5),
        _chunk("better quality summary", "https://a.com/x", score=0.9),
    ]

    deduped, index_map = deduplicate_evidence(chunks)

    assert len(deduped) == 2
    urls = {c.source_url for c in deduped}
    assert urls == {"https://a.com/x", "https://b.com/y"}
    # Both original a.com/x indices (0 dropped, 2 survivor) map to the same new index
    assert index_map[0] == index_map[2]
    survivor_new_index = index_map[2]
    assert deduped[survivor_new_index].text == "better quality summary"


def test_dedup_no_duplicates_is_a_no_op():
    chunks = [_chunk("one", "https://a.com", 0.5), _chunk("two", "https://b.com", 0.6)]
    deduped, index_map = deduplicate_evidence(chunks)
    assert len(deduped) == 2
    assert index_map == {0: 0, 1: 1}


def test_remap_claim_evidence_indices_follows_dropped_duplicate_to_survivor():
    chunks = [
        _chunk("dup copy 1", "https://a.com/x", score=0.2),
        _chunk("dup copy 2 (best)", "https://a.com/x", score=0.95),
        _chunk("other", "https://c.com", score=0.4),
    ]
    deduped, index_map = deduplicate_evidence(chunks)
    claims = [{"statement": "claim about a.com", "evidence_indices": [0]}]

    remap_claim_evidence_indices(claims, index_map)

    survivor_index = index_map[0]
    assert claims[0]["evidence_indices"] == [survivor_index]
    assert deduped[survivor_index].text == "dup copy 2 (best)"


def test_remap_drops_indices_with_no_mapping():
    claims = [{"statement": "x", "evidence_indices": [0, 99]}]
    remap_claim_evidence_indices(claims, {0: 0})
    assert claims[0]["evidence_indices"] == [0]
