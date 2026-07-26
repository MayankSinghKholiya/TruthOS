"""Lightweight dependency-injection container.

TruthOS favors constructor injection: services declare the clients/repositories
they need as constructor arguments, and this module is the single place that
knows how to construct singleton infrastructure clients (Redis, Neo4j, HTTP).
FastAPI routes pull instances via `app/api/deps.py`, which composes these
providers - nothing here talks HTTP or knows about routes.
"""
from functools import lru_cache

import httpx
from neo4j import AsyncDriver, AsyncGraphDatabase
from redis.asyncio import Redis, from_url

from app.core.config import get_settings


@lru_cache
def get_redis() -> Redis:
    settings = get_settings()
    return from_url(settings.redis_url, decode_responses=True)


@lru_cache
def get_neo4j_driver() -> AsyncDriver:
    settings = get_settings()
    return AsyncGraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )


@lru_cache
def get_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))


async def shutdown_container() -> None:
    """Close pooled connections gracefully on app shutdown."""
    await get_redis().aclose()
    await get_neo4j_driver().close()
    await get_http_client().aclose()
