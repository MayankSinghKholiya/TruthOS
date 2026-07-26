"""Thin async clients for the external retrieval APIs TruthOS depends on:
Tavily (web search), Semantic Scholar (academic), CoinGecko (crypto),
AlphaVantage (equities/fx). Each returns a normalized list of dicts so the
retriever/agents don't need to know per-provider response shapes.
"""
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TavilySearchTool:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http = http_client
        self._settings = get_settings()

    async def search(self, query: str, *, max_results: int = 5) -> list[dict[str, Any]]:
        if not self._settings.tavily_api_key:
            logger.warning("tavily_search_skipped_no_api_key")
            return []
        try:
            response = await self._http.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self._settings.tavily_api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "advanced",
                },
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            logger.error("tavily_search_failed", error=str(exc))
            return []

        return [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("content"),
                "published_at": item.get("published_date"),
                "source": "tavily",
            }
            for item in data.get("results", [])
        ]


class SemanticScholarTool:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http = http_client
        self._settings = get_settings()

    async def search(self, query: str, *, max_results: int = 5) -> list[dict[str, Any]]:
        headers = {}
        if self._settings.semantic_scholar_api_key:
            headers["x-api-key"] = self._settings.semantic_scholar_api_key
        try:
            response = await self._http.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={
                    "query": query,
                    "limit": max_results,
                    "fields": "title,abstract,url,year,authors",
                },
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            logger.error("semantic_scholar_search_failed", error=str(exc))
            return []

        return [
            {
                "title": paper.get("title"),
                "url": paper.get("url"),
                "snippet": paper.get("abstract") or "",
                "published_at": str(paper.get("year")) if paper.get("year") else None,
                "source": "semantic_scholar",
            }
            for paper in data.get("data", [])
        ]


class CoinGeckoTool:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http = http_client
        self._settings = get_settings()

    async def get_price(self, coin_id: str, vs_currency: str = "usd") -> dict[str, Any] | None:
        headers = {}
        if self._settings.coingecko_api_key:
            headers["x-cg-demo-api-key"] = self._settings.coingecko_api_key
        try:
            response = await self._http.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": coin_id,
                    "vs_currencies": vs_currency,
                    "include_last_updated_at": "true",
                },
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            logger.error("coingecko_lookup_failed", error=str(exc))
            return None

        entry = data.get(coin_id)
        if not entry:
            return None
        return {
            "coin_id": coin_id,
            "price": entry.get(vs_currency),
            "currency": vs_currency,
            "as_of": entry.get("last_updated_at"),
            "source": "coingecko",
        }


class AlphaVantageTool:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http = http_client
        self._settings = get_settings()

    async def get_quote(self, symbol: str) -> dict[str, Any] | None:
        if not self._settings.alphavantage_api_key:
            logger.warning("alphavantage_lookup_skipped_no_api_key")
            return None
        try:
            response = await self._http.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": self._settings.alphavantage_api_key,
                },
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            logger.error("alphavantage_lookup_failed", error=str(exc))
            return None

        quote = data.get("Global Quote") or {}
        if not quote:
            return None
        return {
            "symbol": quote.get("01. symbol"),
            "price": quote.get("05. price"),
            "as_of": quote.get("07. latest trading day"),
            "source": "alphavantage",
        }
