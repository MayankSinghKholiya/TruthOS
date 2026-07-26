"""Unit tests for on-chain evidence verification. Network calls are mocked
at the http client level (same style as test_market_data.py) so these run
without a real RPC endpoint."""
from unittest.mock import AsyncMock, MagicMock

from app.services.chain_verification import (
    ChainVerificationService,
    _extract_tx_hash,
    _values_match,
    _wei_hex_to_native,
    parse_rpc_url_overrides,
)

_VALID_HASH = "0x" + "a" * 64


def _fake_http_client(responses_by_method: dict[str, dict]):
    client = AsyncMock()

    async def post(url, json, timeout=None):
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json = MagicMock(return_value=responses_by_method[json["method"]])
        return response

    client.post = post
    return client


def _rpc_responses(*, from_addr: str, to_addr: str, value_wei: int, block_hex: str, status_hex: str):
    return {
        "eth_getTransactionByHash": {
            "result": {"from": from_addr, "to": to_addr, "value": hex(value_wei), "blockNumber": block_hex}
        },
        "eth_getTransactionReceipt": {"result": {"status": status_hex, "blockNumber": block_hex}},
    }


def test_extract_tx_hash_finds_embedded_hash():
    assert _extract_tx_hash(f"paid via {_VALID_HASH} on base") == _VALID_HASH


def test_extract_tx_hash_rejects_short_hash():
    assert _extract_tx_hash("0xabc123") is None


def test_wei_hex_to_native_converts_correctly():
    assert _wei_hex_to_native(hex(1_500_000_000_000_000_000)) == 1.5


def test_values_match_within_tolerance():
    assert _values_match(100.0, 100.5) is True  # 0.5% diff, under 2% tolerance


def test_values_match_rejects_large_difference():
    assert _values_match(100.0, 250.0) is False


def test_parse_rpc_url_overrides():
    overrides = parse_rpc_url_overrides("base=https://custom-rpc, ethereum=https://other-rpc")
    assert overrides == {"base": "https://custom-rpc", "ethereum": "https://other-rpc"}


async def test_resolve_evidence_invalid_format_when_no_chain():
    service = ChainVerificationService(http_client=AsyncMock())
    status, details = await service.resolve_evidence(chain=None, tx_hash_raw=_VALID_HASH, claimed_amount=None)
    assert status == "invalid_format"
    assert "reason" in details


async def test_resolve_evidence_unsupported_chain():
    service = ChainVerificationService(http_client=AsyncMock())
    status, details = await service.resolve_evidence(chain="dogechain", tx_hash_raw=_VALID_HASH, claimed_amount=None)
    assert status == "unsupported_chain"
    assert "base" in details["supported_chains"]


async def test_resolve_evidence_invalid_format_when_no_hash_found():
    service = ChainVerificationService(http_client=AsyncMock())
    status, _ = await service.resolve_evidence(chain="base", tx_hash_raw="not a hash", claimed_amount=None)
    assert status == "invalid_format"


async def test_resolve_evidence_confirmed_match():
    responses = _rpc_responses(
        from_addr="0xClaimant", to_addr="0xRespondent",
        value_wei=250_000_000_000_000_000_000, block_hex="0x64", status_hex="0x1",
    )
    service = ChainVerificationService(http_client=_fake_http_client(responses))
    status, details = await service.resolve_evidence(chain="base", tx_hash_raw=_VALID_HASH, claimed_amount=250.0)
    assert status == "confirmed_match"
    assert details["value_native"] == 250.0
    assert details["block_number"] == 100


async def test_resolve_evidence_confirmed_mismatch():
    responses = _rpc_responses(
        from_addr="0xClaimant", to_addr="0xRespondent",
        value_wei=10_000_000_000_000_000_000, block_hex="0x64", status_hex="0x1",
    )
    service = ChainVerificationService(http_client=_fake_http_client(responses))
    status, _ = await service.resolve_evidence(chain="base", tx_hash_raw=_VALID_HASH, claimed_amount=250.0)
    assert status == "confirmed_mismatch"


async def test_resolve_evidence_failed_onchain():
    responses = _rpc_responses(
        from_addr="0xClaimant", to_addr="0xRespondent",
        value_wei=250_000_000_000_000_000_000, block_hex="0x64", status_hex="0x0",
    )
    service = ChainVerificationService(http_client=_fake_http_client(responses))
    status, _ = await service.resolve_evidence(chain="base", tx_hash_raw=_VALID_HASH, claimed_amount=250.0)
    assert status == "failed_onchain"


async def test_resolve_evidence_not_found():
    responses = {
        "eth_getTransactionByHash": {"result": None},
        "eth_getTransactionReceipt": {"result": None},
    }
    service = ChainVerificationService(http_client=_fake_http_client(responses))
    status, _ = await service.resolve_evidence(chain="base", tx_hash_raw=_VALID_HASH, claimed_amount=250.0)
    assert status == "not_found"


async def test_resolve_evidence_pending_when_no_receipt_yet():
    responses = {
        "eth_getTransactionByHash": {
            "result": {"from": "0xA", "to": "0xB", "value": "0x1", "blockNumber": None}
        },
        "eth_getTransactionReceipt": {"result": None},
    }
    service = ChainVerificationService(http_client=_fake_http_client(responses))
    status, _ = await service.resolve_evidence(chain="base", tx_hash_raw=_VALID_HASH, claimed_amount=None)
    assert status == "pending"


async def test_resolve_evidence_unverifiable_on_rpc_error():
    import httpx

    client = AsyncMock()

    async def post(*args, **kwargs):
        raise httpx.ConnectTimeout("timed out")

    client.post = post
    service = ChainVerificationService(http_client=client)
    status, _ = await service.resolve_evidence(chain="base", tx_hash_raw=_VALID_HASH, claimed_amount=None)
    assert status == "unverifiable"
