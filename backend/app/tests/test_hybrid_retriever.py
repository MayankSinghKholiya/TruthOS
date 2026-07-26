import pytest

from app.rag.bm25 import BM25Document, BM25Index
from app.rag.hybrid_retriever import HybridRetriever, RetrievedChunk
from app.rag.ingestion import chunk_text
from app.rag.vector_store import VectorHit


def test_chunk_text_splits_and_respects_overlap():
    text = "x" * 2000
    chunks = chunk_text(text, chunk_size=800, overlap=100)
    assert len(chunks) > 1
    assert all(len(c) <= 800 for c in chunks)


def test_chunk_text_rejects_overlap_gte_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("hello", chunk_size=50, overlap=50)


def test_bm25_ranks_more_relevant_document_first():
    docs = [
        BM25Document(doc_id="1", text="cats are small domestic animals"),
        BM25Document(doc_id="2", text="the stock market rose sharply today"),
    ]
    index = BM25Index(docs)

    results = index.search("domestic cats", top_k=2)

    assert results[0][0].doc_id == "1"


class _FakeVectorStore:
    def __init__(self, hits=None):
        self._hits = hits or []

    async def search(self, query, top_k=10, query_filter=None):
        return self._hits


class _FakeWebSearch:
    def __init__(self, hits):
        self._hits = hits

    async def search(self, query, max_results=5):
        return self._hits


async def test_hybrid_retriever_retrieve_returns_fused_order_directly():
    dense_hits = [VectorHit(doc_id="1", text="Paris is the capital of France", score=0.9, metadata={})]
    web_hits = [
        {"title": "B", "url": "https://b.com", "snippet": "Bananas are yellow", "published_at": None},
    ]
    retriever = HybridRetriever(_FakeVectorStore(dense_hits), _FakeWebSearch(web_hits))

    results: list[RetrievedChunk] = await retriever.retrieve(
        ["What is the capital of France?"], top_k=2
    )

    # The dense hit (rank 0 in both dense search and, since its text shares
    # "capital"/"France" with the query, BM25) should fuse ahead of the
    # unrelated web hit - no reranking pass follows fusion anymore.
    assert results
    assert "France" in results[0].text


def test_fuse_sets_retrieval_score_normalized_to_unit_range():
    retriever = HybridRetriever(_FakeVectorStore(), _FakeWebSearch([]))
    candidates = [
        RetrievedChunk(
            text="best match for the query", source_url="https://best.example", source_title="Best",
            published_at=None, source="knowledge_base", dense_rank=0,
        ),
        RetrievedChunk(
            text="unrelated filler text", source_url="https://worst.example", source_title="Worst",
            published_at=None, source="knowledge_base", dense_rank=50,
        ),
    ]

    fused = retriever._fuse(candidates, ["query about the best match"])

    assert fused[0].source_url == "https://best.example"
    assert fused[0].retrieval_score == 1.0
    assert fused[-1].retrieval_score == 0.0
    assert all(0.0 <= c.retrieval_score <= 1.0 for c in fused)


def test_fuse_single_candidate_gets_full_score_not_division_by_zero():
    retriever = HybridRetriever(_FakeVectorStore(), _FakeWebSearch([]))
    candidates = [
        RetrievedChunk(
            text="only candidate", source_url="https://only.example", source_title="Only",
            published_at=None, source="knowledge_base", dense_rank=0,
        ),
    ]

    fused = retriever._fuse(candidates, ["query"])

    assert fused[0].retrieval_score == 1.0


async def test_fetch_for_query_assigns_dense_rank_by_position_within_the_query():
    dense_hits = [
        VectorHit(doc_id="1", text="best match", score=0.9, metadata={}),
        VectorHit(doc_id="2", text="second best", score=0.7, metadata={}),
    ]
    retriever = HybridRetriever(_FakeVectorStore(dense_hits), _FakeWebSearch([]))

    chunks = await retriever._fetch_for_query("query", top_k=5, include_web=False, include_academic=False)

    assert [c.dense_rank for c in chunks] == [0, 1]


def test_fuse_uses_per_query_dense_rank_not_concatenated_list_position():
    """Regression test: _fuse() used to treat a chunk's position in the
    fully concatenated (multi-query) candidate list as its dense rank, so a
    later query's #1 dense match could lose to an earlier query's #50 match
    purely because of concatenation order. Two candidates with identical
    text (so BM25 scores them identically) isolate the dense_rank signal."""
    retriever = HybridRetriever(_FakeVectorStore(), _FakeWebSearch([]))
    identical_text = "some evidence passage about the topic at hand"
    candidates = [
        RetrievedChunk(
            text=identical_text, source_url="https://early.example", source_title="Early",
            published_at=None, source="knowledge_base", dense_rank=50,
        ),
        RetrievedChunk(
            text=identical_text, source_url="https://late.example", source_title="Late",
            published_at=None, source="knowledge_base", dense_rank=0,
        ),
    ]

    fused = retriever._fuse(candidates, ["the topic at hand"])

    assert fused[0].source_url == "https://late.example"
