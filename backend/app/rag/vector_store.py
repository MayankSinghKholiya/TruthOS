"""Qdrant-backed dense vector store for persisted documents (semantic memory
lives here too - see app/memory/semantic.py, which reuses this client)."""
import uuid
from dataclasses import dataclass
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import get_settings
from app.rag.embeddings import embed_query, embed_texts

_VECTOR_SIZE = 384  # BAAI/bge-small-en-v1.5 output dimension


@dataclass
class VectorHit:
    doc_id: str
    text: str
    score: float
    metadata: dict[str, Any]


class VectorStore:
    def __init__(self, client: AsyncQdrantClient, collection: str | None = None) -> None:
        self._client = client
        self._collection = collection or get_settings().qdrant_collection

    async def ensure_collection(self) -> None:
        exists = await self._client.collection_exists(self._collection)
        if not exists:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
            )

    async def upsert_documents(
        self, texts: list[str], metadatas: list[dict[str, Any]]
    ) -> list[str]:
        await self.ensure_collection()
        vectors = embed_texts(texts)
        ids = [str(uuid.uuid4()) for _ in texts]
        points = [
            PointStruct(id=doc_id, vector=vector, payload={"text": text, **meta})
            for doc_id, vector, text, meta in zip(ids, vectors, texts, metadatas)
        ]
        await self._client.upsert(collection_name=self._collection, points=points)
        return ids

    async def search(
        self, query: str, top_k: int = 10, query_filter: dict[str, Any] | None = None
    ) -> list[VectorHit]:
        await self.ensure_collection()
        vector = embed_query(query)
        results = await self._client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=top_k,
        )
        hits = []
        for point in results.points:
            payload = point.payload or {}
            text = payload.pop("text", "")
            hits.append(
                VectorHit(doc_id=str(point.id), text=text, score=point.score, metadata=payload)
            )
        return hits
