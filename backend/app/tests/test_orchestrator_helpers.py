from unittest.mock import AsyncMock

from app.graph.knowledge_graph import Triple
from app.graph.orchestrator import (
    Orchestrator,
    _claims_from_specialist_output,
    _format_kg_context,
    _market_data_to_chunks,
)


def test_market_data_to_chunks_handles_crypto_entry():
    chunks = _market_data_to_chunks(
        [{"coin_id": "bitcoin", "price": 65000, "currency": "usd", "as_of": 123, "source": "coingecko"}]
    )
    assert len(chunks) == 1
    assert chunks[0].source == "market_data"
    assert "bitcoin" in chunks[0].text
    assert "65000" in chunks[0].text
    assert chunks[0].retrieval_score == 1.0


def test_market_data_to_chunks_handles_equity_entry():
    chunks = _market_data_to_chunks(
        [{"symbol": "AAPL", "price": "190.12", "as_of": "2026-07-25", "source": "alphavantage"}]
    )
    assert len(chunks) == 1
    assert "AAPL" in chunks[0].text
    assert "alphavantage.co" in chunks[0].source_url


def test_market_data_to_chunks_empty_input():
    assert _market_data_to_chunks([]) == []


def test_claims_from_specialist_output_uses_analysis_field():
    claims = _claims_from_specialist_output({"analysis": "BTC is up 3% today"}, evidence_count=2)
    assert len(claims) == 1
    assert claims[0]["statement"] == "BTC is up 3% today"
    assert claims[0]["evidence_indices"] == [0, 1]


def test_claims_from_specialist_output_falls_back_to_explanation_field():
    # Coder's schema uses "explanation" instead of "analysis".
    claims = _claims_from_specialist_output({"explanation": "Use asyncio.gather for this"}, evidence_count=1)
    assert claims[0]["statement"] == "Use asyncio.gather for this"


def test_claims_from_specialist_output_empty_when_no_statement():
    assert _claims_from_specialist_output({}, evidence_count=3) == []


def test_format_kg_context_empty_with_no_records():
    assert _format_kg_context([]) == ""


def test_format_kg_context_formats_relation_lines():
    formatted = _format_kg_context(
        [{"entity": "CJP", "relation": "relates_to", "related_entity": "CAA protests", "confidence": 0.8}]
    )
    assert formatted == "CJP relates_to CAA protests (confidence 0.80)"


def test_format_kg_context_caps_at_ten_records():
    records = [
        {"entity": f"e{i}", "relation": "relates_to", "related_entity": f"o{i}", "confidence": 0.5}
        for i in range(25)
    ]
    formatted = _format_kg_context(records)
    assert len(formatted.splitlines()) == 10


def _bare_orchestrator() -> Orchestrator:
    return Orchestrator.__new__(Orchestrator)  # bypass __init__, no real infra needed


async def test_fetch_kg_context_returns_empty_when_no_entities_extracted():
    orchestrator = _bare_orchestrator()
    orchestrator._triple_extractor = AsyncMock()
    orchestrator._triple_extractor.extract.return_value = []
    orchestrator._kg = AsyncMock()

    result = await orchestrator._fetch_kg_context("some objective")

    assert result == ""
    orchestrator._kg.find_related_entities.assert_not_called()


async def test_fetch_kg_context_queries_graph_for_extracted_entities():
    orchestrator = _bare_orchestrator()
    orchestrator._triple_extractor = AsyncMock()
    orchestrator._triple_extractor.extract.return_value = [
        Triple(subject="CJP", relation="organized", object="a protest")
    ]
    orchestrator._kg = AsyncMock()
    orchestrator._kg.find_related_entities.return_value = [
        {"entity": "CJP", "relation": "relates_to", "related_entity": "CAA protests", "confidence": 0.8}
    ]

    result = await orchestrator._fetch_kg_context("is CJP protest anti-national")

    orchestrator._kg.find_related_entities.assert_awaited_once_with(["CJP", "a protest"])
    assert "CAA protests" in result


async def test_fetch_kg_context_degrades_to_empty_on_failure():
    orchestrator = _bare_orchestrator()
    orchestrator._triple_extractor = AsyncMock()
    orchestrator._triple_extractor.extract.side_effect = RuntimeError("llm down")

    result = await orchestrator._fetch_kg_context("some objective")

    assert result == ""
