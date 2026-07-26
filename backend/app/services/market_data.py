"""Bundles the CoinGecko/AlphaVantage clients behind one call the Finance
agent's orchestration step can await - fetches every requested symbol
concurrently since each is an independent network call."""
import asyncio
from typing import Any

import httpx

from app.services.search_tools import AlphaVantageTool, CoinGeckoTool


class MarketDataService:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._coingecko = CoinGeckoTool(http_client)
        self._alphavantage = AlphaVantageTool(http_client)

    async def fetch(
        self, *, crypto_ids: list[str], equity_symbols: list[str]
    ) -> list[dict[str, Any]]:
        if not crypto_ids and not equity_symbols:
            return []

        results = await asyncio.gather(
            *(self._coingecko.get_price(coin_id) for coin_id in crypto_ids),
            *(self._alphavantage.get_quote(symbol) for symbol in equity_symbols),
        )
        return [result for result in results if result is not None]
