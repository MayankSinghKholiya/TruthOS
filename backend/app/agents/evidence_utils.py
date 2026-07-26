"""Shared helpers for turning RetrievedChunk lists into the indexed text block
agents expect in their prompts, and into EvidenceItem objects for scoring."""
from app.rag.hybrid_retriever import RetrievedChunk
from app.schemas.agent import EvidenceItem

_SOURCE_BASE_RELIABILITY = {
    "knowledge_base": 0.9,  # previously vetted/ingested documents
    "market_data": 0.95,  # direct exchange/API quote, not a search result
    "academic": 0.85,
    "web": 0.6,
}


def format_evidence_block(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no evidence retrieved)"
    lines = []
    for i, chunk in enumerate(chunks):
        source = chunk.source_title or chunk.source_url or chunk.source
        lines.append(f"[{i}] ({source}): {chunk.text}")
    return "\n".join(lines)


def deduplicate_evidence(
    chunks: list[RetrievedChunk],
) -> tuple[list[RetrievedChunk], dict[int, int]]:
    """Dedupes chunks gathered across multiple sub-tasks by source_url (or a
    text prefix when there's no URL), keeping the highest-retrieval_score
    copy per duplicate group. Returns the deduped list plus a mapping from
    *every* original index - survivors and dropped duplicates alike - to the
    surviving chunk's new index, so claims that cite evidence by index stay
    correct even when the exact copy they cited was the one dropped.
    """
    best_original_index_by_key: dict[str, int] = {}
    for i, chunk in enumerate(chunks):
        key = chunk.source_url or chunk.text[:120]
        current_best = best_original_index_by_key.get(key)
        if current_best is None or chunk.retrieval_score > chunks[current_best].retrieval_score:
            best_original_index_by_key[key] = i

    surviving_original_indices = sorted(set(best_original_index_by_key.values()))
    new_index_by_original_index = {
        original: new for new, original in enumerate(surviving_original_indices)
    }
    deduped_chunks = [chunks[i] for i in surviving_original_indices]

    old_to_new_index: dict[int, int] = {}
    for i, chunk in enumerate(chunks):
        key = chunk.source_url or chunk.text[:120]
        survivor_original_index = best_original_index_by_key[key]
        old_to_new_index[i] = new_index_by_original_index[survivor_original_index]

    return deduped_chunks, old_to_new_index


def remap_claim_evidence_indices(claims: list[dict], index_map: dict[int, int]) -> None:
    """Mutates `claims` in place, remapping each claim's evidence_indices
    through `index_map` (original index -> deduped index) and dropping any
    index that no longer resolves to anything."""
    for claim in claims:
        original_indices = claim.get("evidence_indices", [])
        remapped = sorted(
            {index_map[i] for i in original_indices if isinstance(i, int) and i in index_map}
        )
        claim["evidence_indices"] = remapped


def to_evidence_items(chunks: list[RetrievedChunk]) -> list[EvidenceItem]:
    items = []
    for chunk in chunks:
        base = _SOURCE_BASE_RELIABILITY.get(chunk.source, 0.5)
        # blend base source trust with the cross-encoder's relevance score
        reliability = max(0.0, min(1.0, base * 0.7 + max(chunk.retrieval_score, 0.0) * 0.3))
        items.append(
            EvidenceItem(
                claim="",
                source_url=chunk.source_url,
                source_title=chunk.source_title,
                snippet=chunk.text,
                reliability=round(reliability, 4),
            )
        )
    return items
