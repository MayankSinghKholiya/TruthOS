from app.rag.bm25 import BM25Document, BM25Index
from app.rag.hybrid_retriever import HybridRetriever, RetrievedChunk


def test_bm25_ranks_more_relevant_document_first():
    docs = [
        BM25Document(doc_id="1", text="cats are small domestic animals"),
        BM25Document(doc_id="2", text="the stock market rose sharply today"),
    ]
    index = BM25Index(docs)

    results = index.search("domestic cats", top_k=2)

    assert results[0][0].doc_id == "1"


class _FakeWebSearch:
    def __init__(self, hits):
        self._hits = hits

    async def search(self, query, max_results=5):
        return self._hits


async def test_hybrid_retriever_retrieve_ranks_web_results_by_bm25():
    # BM25's IDF term needs enough corpus size to discriminate at all - with
    # too few documents, a term appearing in exactly half of them can get an
    # IDF of exactly zero (log((N-df+0.5)/(df+0.5))), scoring every
    # candidate 0.0 regardless of relevance. Four unrelated fillers alongside
    # the one relevant hit keeps this test meaningful.
    web_hits = [
        {"title": "A", "url": "https://a.com", "snippet": "Bananas are yellow", "published_at": None},
        {"title": "B", "url": "https://b.com", "snippet": "Paris is the capital of France", "published_at": None},
        {"title": "C", "url": "https://c.com", "snippet": "The stock market rose today", "published_at": None},
        {"title": "D", "url": "https://d.com", "snippet": "Cats are small domestic animals", "published_at": None},
    ]
    retriever = HybridRetriever(_FakeWebSearch(web_hits))

    results: list[RetrievedChunk] = await retriever.retrieve(
        ["What is the capital of France?"], top_k=2
    )

    assert results
    assert "France" in results[0].text


def test_rank_by_bm25_sets_retrieval_score_normalized_to_unit_range():
    retriever = HybridRetriever(_FakeWebSearch([]))
    candidates = [
        RetrievedChunk(
            text="best match for the query", source_url="https://best.example", source_title="Best",
            published_at=None, source="web",
        ),
        RetrievedChunk(
            text="unrelated filler text", source_url="https://worst.example", source_title="Worst",
            published_at=None, source="web",
        ),
        RetrievedChunk(
            text="some other unrelated passage", source_url="https://c.example", source_title="C",
            published_at=None, source="web",
        ),
        RetrievedChunk(
            text="yet another distinct snippet", source_url="https://d.example", source_title="D",
            published_at=None, source="web",
        ),
    ]

    ranked = retriever._rank_by_bm25(candidates, ["query about the best match"])

    assert ranked[0].source_url == "https://best.example"
    assert ranked[0].retrieval_score == 1.0
    assert ranked[-1].retrieval_score == 0.0
    assert all(0.0 <= c.retrieval_score <= 1.0 for c in ranked)


def test_rank_by_bm25_single_candidate_gets_full_score_not_division_by_zero():
    retriever = HybridRetriever(_FakeWebSearch([]))
    candidates = [
        RetrievedChunk(
            text="only candidate", source_url="https://only.example", source_title="Only",
            published_at=None, source="web",
        ),
    ]

    ranked = retriever._rank_by_bm25(candidates, ["query"])

    assert ranked[0].retrieval_score == 1.0


def test_rank_by_bm25_dedupes_by_source_url_keeping_best_score():
    retriever = HybridRetriever(_FakeWebSearch([]))
    candidates = [
        RetrievedChunk(
            text="irrelevant filler", source_url="https://dup.example", source_title="Dup",
            published_at=None, source="web",
        ),
        RetrievedChunk(
            text="highly relevant match for the query", source_url="https://dup.example", source_title="Dup",
            published_at=None, source="web",
        ),
        RetrievedChunk(
            text="some other unrelated passage", source_url="https://c.example", source_title="C",
            published_at=None, source="web",
        ),
        RetrievedChunk(
            text="yet another distinct snippet", source_url="https://d.example", source_title="D",
            published_at=None, source="web",
        ),
    ]

    ranked = retriever._rank_by_bm25(candidates, ["relevant match query"])

    assert len([c for c in ranked if c.source_url == "https://dup.example"]) == 1
    assert next(c for c in ranked if c.source_url == "https://dup.example").text == "highly relevant match for the query"
