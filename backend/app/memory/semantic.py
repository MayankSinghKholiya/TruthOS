"""Semantic memory: embeds past investigation summaries so future queries can
retrieve 'similar things we've already figured out' via vector similarity."""
from qdrant_client import AsyncQdrantClient

from app.rag.vector_store import VectorHit, VectorStore

_SEMANTIC_MEMORY_COLLECTION = "truthos_semantic_memory"


class SemanticMemory:
    def __init__(self, qdrant_client: AsyncQdrantClient) -> None:
        self._store = VectorStore(qdrant_client, collection=_SEMANTIC_MEMORY_COLLECTION)

    async def remember(self, *, user_id: str, summary: str, entities: list[str]) -> str:
        ids = await self._store.upsert_documents(
            [summary], [{"user_id": user_id, "entities": entities}]
        )
        return ids[0]

    async def recall(self, *, user_id: str, query: str, top_k: int = 3) -> list[VectorHit]:
        hits = await self._store.search(query, top_k=top_k)
        return [hit for hit in hits if hit.metadata.get("user_id") == user_id]
