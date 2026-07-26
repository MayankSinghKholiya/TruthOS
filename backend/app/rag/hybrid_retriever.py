"""RAG pipeline: live web (+ academic) search results are ranked by BM25
keyword relevance. Dense (Qdrant) vector search and cross-encoder
reranking were both dropped to keep the service's memory footprint inside
Render's free-tier 512MB limit - loading sentence-transformers/torch for
either one reliably OOM-killed the container on a real query, and dense
retrieval had no ingested documents behind it in practice anyway (nothing
in the running application ever wrote to that collection). Query
expansion is applied upstream by the Retriever agent
(app/agents/retriever.py), which supplies the list of `queries` this class
fans out over.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.rag.bm25 import BM25Document, BM25Index
from app.services.search_tools import SemanticScholarTool, TavilySearchTool

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    text: str
    source_url: str | None
    source_title: str | None
    published_at: str | None
    source: str
    retrieval_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class HybridRetriever:
    def __init__(
        self,
        web_search: TavilySearchTool,
        academic_search: SemanticScholarTool | None = None,
    ) -> None:
        self._web_search = web_search
        self._academic_search = academic_search

    async def retrieve(
        self,
        queries: list[str],
        *,
        top_k: int = 8,
        include_web: bool = True,
        include_academic: bool = False,
        domain_filter: list[str] | None = None,
        date_after: str | None = None,
    ) -> list[RetrievedChunk]:
        # Every query's web/academic lookups are independent network calls -
        # fan them all out concurrently instead of awaiting one at a time,
        # since with query expansion producing several queries per
        # sub-task, sequential awaits were the single biggest latency
        # contributor in the pipeline.
        per_query_results = await asyncio.gather(
            *(
                self._fetch_for_query(query, top_k, include_web, include_academic)
                for query in queries
            )
        )
        candidates: list[RetrievedChunk] = [
            chunk for chunks in per_query_results for chunk in chunks
        ]

        candidates = _apply_metadata_filters(candidates, domain_filter, date_after)
        if not candidates:
            return []

        ranked = self._rank_by_bm25(candidates, queries)
        return ranked[:top_k]

    async def _fetch_for_query(
        self, query: str, top_k: int, include_web: bool, include_academic: bool
    ) -> list[RetrievedChunk]:
        tasks: list = []
        if include_web:
            tasks.append(self._web_search.search(query, max_results=top_k))
        if include_academic and self._academic_search:
            tasks.append(self._academic_search.search(query, max_results=top_k))

        results = await asyncio.gather(*tasks) if tasks else []
        chunks: list[RetrievedChunk] = []

        remaining = list(results)
        if include_web:
            web_hits = remaining.pop(0)
            chunks.extend(
                RetrievedChunk(
                    text=hit["snippet"] or "",
                    source_url=hit.get("url"),
                    source_title=hit.get("title"),
                    published_at=hit.get("published_at"),
                    source="web",
                )
                for hit in web_hits
                if hit.get("snippet")
            )
        if include_academic and self._academic_search:
            academic_hits = remaining.pop(0)
            chunks.extend(
                RetrievedChunk(
                    text=hit["snippet"] or "",
                    source_url=hit.get("url"),
                    source_title=hit.get("title"),
                    published_at=hit.get("published_at"),
                    source="academic",
                )
                for hit in academic_hits
                if hit.get("snippet")
            )
        return chunks

    def _rank_by_bm25(
        self, candidates: list[RetrievedChunk], queries: list[str]
    ) -> list[RetrievedChunk]:
        """Ranks candidates by BM25 keyword relevance against the joined
        queries, dedupes by source (keeping each duplicate's best rank),
        and sets retrieval_score from rank position, min-max normalized to
        [0, 1] so Confidence DNA's retrieval_confidence signal and
        evidence_utils' reliability weighting get a meaningfully-spread
        score rather than a raw BM25 statistic on an arbitrary scale."""
        bm25_docs = [BM25Document(doc_id=str(i), text=c.text) for i, c in enumerate(candidates)]
        bm25_index = BM25Index(bm25_docs)
        bm25_ranked = bm25_index.search(" ".join(queries), top_k=len(candidates))
        scores = {int(doc.doc_id): score for doc, score in bm25_ranked}

        deduped: dict[str, tuple[RetrievedChunk, float]] = {}
        for i, candidate in enumerate(candidates):
            score = scores.get(i, 0.0)
            key = candidate.source_url or candidate.text[:120]
            if key not in deduped or score > deduped[key][1]:
                deduped[key] = (candidate, score)

        ranked = sorted(deduped.values(), key=lambda pair: pair[1], reverse=True)
        raw_scores = [score for _, score in ranked]
        lo, hi = min(raw_scores), max(raw_scores)
        spread = hi - lo
        for chunk, score in ranked:
            chunk.retrieval_score = ((score - lo) / spread) if spread > 0 else 1.0
        return [c for c, _ in ranked]


def _apply_metadata_filters(
    candidates: list[RetrievedChunk],
    domain_filter: list[str] | None,
    date_after: str | None,
) -> list[RetrievedChunk]:
    filtered = candidates
    if domain_filter:
        filtered = [
            c
            for c in filtered
            if not c.source_url or any(domain in c.source_url for domain in domain_filter)
        ]
    if date_after:
        filtered = [c for c in filtered if not c.published_at or c.published_at >= date_after]
    return filtered
