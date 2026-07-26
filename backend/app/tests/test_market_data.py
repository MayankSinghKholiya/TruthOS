from unittest.mock import AsyncMock

from app.services.market_data import MarketDataService


async def test_fetch_returns_empty_list_with_no_symbols():
    service = MarketDataService.__new__(MarketDataService)  # bypass __init__, no http client needed
    result = await service.fetch(crypto_ids=[], equity_symbols=[])
    assert result == []


async def test_fetch_combines_crypto_and_equity_results_and_drops_misses(monkeypatch):
    service = MarketDataService.__new__(MarketDataService)
    service._coingecko = AsyncMock()
    service._alphavantage = AsyncMock()

    service._coingecko.get_price.side_effect = [
        {"coin_id": "bitcoin", "price": 65000, "currency": "usd", "as_of": 123, "source": "coingecko"},
        None,  # simulates a coin id CoinGecko didn't recognize
    ]
    service._alphavantage.get_quote.return_value = {
        "symbol": "AAPL", "price": "190.12", "as_of": "2026-07-25", "source": "alphavantage"
    }

    result = await service.fetch(crypto_ids=["bitcoin", "not-a-real-coin"], equity_symbols=["AAPL"])

    assert len(result) == 2
    assert {"bitcoin", "AAPL"} == {r.get("coin_id") or r.get("symbol") for r in result}
