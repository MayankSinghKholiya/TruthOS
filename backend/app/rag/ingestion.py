"""Document ingestion: chunk raw text and upsert into the vector store so it
becomes part of the retrievable knowledge base."""
from dataclasses import dataclass

from app.rag.vector_store import VectorStore

_CHUNK_SIZE = 800  # characters
_CHUNK_OVERLAP = 100


@dataclass
class IngestResult:
    document_ids: list[str]
    chunk_count: int


def chunk_text(text: str, *, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == length:
            break
        start = end - overlap
    return chunks


class DocumentIngestionPipeline:
    def __init__(self, vector_store: VectorStore) -> None:
        self._vector_store = vector_store

    async def ingest(
        self, *, text: str, title: str, url: str | None = None, published_at: str | None = None
    ) -> IngestResult:
        chunks = chunk_text(text)
        metadatas = [
            {"title": title, "url": url, "published_at": published_at, "chunk_index": i}
            for i in range(len(chunks))
        ]
        ids = await self._vector_store.upsert_documents(chunks, metadatas)
        return IngestResult(document_ids=ids, chunk_count=len(chunks))
