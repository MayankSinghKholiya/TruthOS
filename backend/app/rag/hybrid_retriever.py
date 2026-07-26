"""Hybrid RAG pipeline: BM25 (sparse) + Qdrant (dense) + live web search are
fused with Reciprocal Rank Fusion, then the fused candidate pool is
re-ordered by a cross-encoder for the final top-k. Query expansion is
applied upstream by the Retriever agent (app/agents/retriever.py), which
supplies the list of `queries` this class fans out over.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.rag.bm25 import BM25Document, BM25Index
from app.rag.reranker import rerank
from app.rag.vector_store import VectorStore
from app.services.search_tools import SemanticScholarTool, TavilySearchTool

logger = get_logger(__name__)

_RRF_K = 60  # standard reciprocal-rank-fusion damping constant


@dataclass
class RetrievedChunk:
    text: str
    source_url: str | None
    source_title: str | None
    published_at: str | None
    source: str
    retrieval_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    # This chunk's rank within its OWN query's dense-search hits (0 = most
    # similar), not its position in the final concatenated candidate list.
    # None for non-dense sources (web/academic), which don't participate in
    # the dense side of RRF fusion at all - see HybridRetriever._fuse.
    dense_rank: int | None = None


class HybridRetriever:
    def __init__(
        self,
        vector_store: VectorStore,
        web_search: TavilySearchTool,
        academic_search: SemanticScholarTool | None = None,
    ) -> None:
        self._vector_store = vector_store
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
        # Every query's dense/web/academic lookups are independent network
        # calls - fan them all out concurrently instead of awaiting one at a
        # time, since with query expansion producing several queries per
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

        fused = self._fuse(candidates, queries)
        return self._cross_encoder_rerank(fused, queries[0] if queries else "", top_k)

    async def _fetch_for_query(
        self, query: str, top_k: int, include_web: bool, include_academic: bool
    ) -> list[RetrievedChunk]:
        tasks: list = [self._vector_store.search(query, top_k=top_k)]
        if include_web:
            tasks.append(self._web_search.search(query, max_results=top_k))
        if include_academic and self._academic_search:
            tasks.append(self._academic_search.search(query, max_results=top_k))

        results = await asyncio.gather(*tasks)
        dense_hits = results[0]
        chunks = [
            RetrievedChunk(
                text=hit.text,
                source_url=hit.metadata.get("url"),
                source_title=hit.metadata.get("title"),
                published_at=hit.metadata.get("published_at"),
                source="knowledge_base",
                metadata=hit.metadata,
                dense_rank=rank,
            )
            for rank, hit in enumerate(dense_hits)
        ]

        remaining = results[1:]
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

    def _fuse(
        self, candidates: list[RetrievedChunk], queries: list[str]
    ) -> list[RetrievedChunk]:
        """Reciprocal Rank Fusion across BM25 rank and each chunk's own
        per-query dense-search rank.

        Earlier this used the chunk's position in the fully concatenated
        candidate list (across every query and source) as a stand-in for
        dense rank. That's wrong whenever there's more than one query: a
        dense hit ranked #0 for query 2 would still lose to a dense hit
        ranked #3 for query 1, purely because query 1's results were
        concatenated first - a list-position artifact, not a relevance
        signal. Using RetrievedChunk.dense_rank (each hit's rank within its
        own query's dense results) fixes that; BM25 rank stays global since
        BM25 is inherently a whole-corpus statistic, not a per-query one.
        """
        bm25_docs = [BM25Document(doc_id=str(i), text=c.text) for i, c in enumerate(candidates)]
        bm25_index = BM25Index(bm25_docs)
        bm25_ranked = bm25_index.search(" ".join(queries), top_k=len(candidates))
        bm25_rank_by_id = {doc.doc_id: rank for rank, (doc, _) in enumerate(bm25_ranked)}

        scores: dict[int, float] = {}
        for i, candidate in enumerate(candidates):
            dense_rank = candidate.dense_rank if candidate.dense_rank is not None else len(candidates)
            bm25_rank = bm25_rank_by_id.get(str(i), len(candidates))
            scores[i] = 1 / (_RRF_K + dense_rank) + 1 / (_RRF_K + bm25_rank)

        deduped: dict[str, tuple[RetrievedChunk, float]] = {}
        for i, candidate in enumerate(candidates):
            key = candidate.source_url or candidate.text[:120]
            if key not in deduped or scores[i] > deduped[key][1]:
                deduped[key] = (candidate, scores[i])

        ranked = sorted(deduped.values(), key=lambda pair: pair[1], reverse=True)
        return [c for c, _ in ranked]

    def _cross_encoder_rerank(
        self, fused: list[RetrievedChunk], query: str, top_k: int
    ) -> list[RetrievedChunk]:
        if not query:
            return fused[:top_k]
        texts = [c.text for c in fused]
        reranked = rerank(query, texts, top_k=top_k)
        results = []
        for index, score in reranked:
            chunk = fused[index]
            chunk.retrieval_score = float(score)
            results.append(chunk)
        return results


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
