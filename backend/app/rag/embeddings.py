"""Dense embedding model wrapper (BAAI BGE family, per README)."""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    settings = get_settings()
    return SentenceTransformer(settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return vectors.tolist()


def embed_query(query: str) -> list[float]:
    return embed_texts([query])[0]
