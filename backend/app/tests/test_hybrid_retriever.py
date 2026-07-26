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


async def test_hybrid_retriever_fuses_and_reranks(monkeypatch):
    web_hits = [
        {"title": "A", "url": "https://a.com", "snippet": "Paris is the capital of France", "published_at": None},
        {"title": "B", "url": "https://b.com", "snippet": "Bananas are yellow", "published_at": None},
    ]
    retriever = HybridRetriever(_FakeVectorStore(), _FakeWebSearch(web_hits))

    def fake_rerank(query, candidates, top_k=8):
        # force the France-related candidate to rank first regardless of order
        scored = [(i, 1.0 if "France" in c else 0.1) for i, c in enumerate(candidates)]
        return sorted(scored, key=lambda p: p[1], reverse=True)[:top_k]

    monkeypatch.setattr("app.rag.hybrid_retriever.rerank", fake_rerank)

    results: list[RetrievedChunk] = await retriever.retrieve(
        ["What is the capital of France?"], top_k=2
    )

    assert results
    assert "France" in results[0].text


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
