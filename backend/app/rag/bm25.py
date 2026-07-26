"""In-process BM25 sparse retriever over a document corpus.

Indexes whatever documents/snippets were already fetched per-query (the
working set HybridRetriever's web/academic search gathered), rather than
maintaining a separately-managed persistent index - this reranks that live
candidate pool by keyword relevance, it doesn't search a stored corpus.
"""
from dataclasses import dataclass

from rank_bm25 import BM25Okapi


@dataclass
class BM25Document:
    doc_id: str
    text: str


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


class BM25Index:
    def __init__(self, documents: list[BM25Document]) -> None:
        self._documents = documents
        corpus = [_tokenize(doc.text) for doc in documents]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, top_k: int = 10) -> list[tuple[BM25Document, float]]:
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(zip(self._documents, scores), key=lambda pair: pair[1], reverse=True)
        return ranked[:top_k]
