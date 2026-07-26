"""Verifies dispute evidence of type `tx_reference` against real on-chain
data instead of trusting the submitter's (or an LLM's) textual description.

Talks raw JSON-RPC directly (`eth_getTransactionByHash` / `eth_getTransactionReceipt`)
rather than pulling in a heavyweight client library - every EVM chain speaks
this protocol identically, so a thin httpx-based client covers all of them
with no per-chain SDK code.
"""
import re
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

_TX_HASH_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")

# Public, no-API-key-required RPC endpoints. Overridable per-chain via the
# CHAIN_RPC_URLS setting (e.g. "base=https://my-rpc,ethereum=https://other")
# without needing a code change or a new Settings field per chain.
_DEFAULT_RPC_URLS: dict[str, str] = {
    "ethereum": "https://eth.llamarpc.com",
    "base": "https://mainnet.base.org",
    "bsc": "https://bsc-dataseed.binance.org",
    "polygon": "https://polygon-rpc.com",
    "arbitrum": "https://arb1.arbitrum.io/rpc",
    "xlayer": "https://rpc.xlayer.tech",
}

_EXPLORER_URLS: dict[str, str] = {
    "ethereum": "https://etherscan.io/tx/{hash}",
    "base": "https://basescan.org/tx/{hash}",
    "bsc": "https://bscscan.com/tx/{hash}",
    "polygon": "https://polygonscan.com/tx/{hash}",
    "arbitrum": "https://arbiscan.io/tx/{hash}",
    "xlayer": "https://www.oklink.com/xlayer/tx/{hash}",
}

VerificationStatus = Literal[
    "confirmed_match",
    "confirmed_mismatch",
    "confirmed",
    "failed_onchain",
    "pending",
    "not_found",
    "invalid_format",
    "unsupported_chain",
    "unverifiable",
]

# Fraction of tolerance allowed between a claimed escrow amount and the
# transaction's actual on-chain value before it counts as a mismatch -
# covers gas-driven or rounding-driven differences, not genuine discrepancies.
_VALUE_MATCH_TOLERANCE = 0.02


@dataclass(frozen=True)
class ChainTxFacts:
    """Raw facts read off the chain for one transaction - no judgment about
    whether they match anyone's claim, just what actually happened."""

    exists: bool
    confirmed: bool
    success: bool | None
    from_address: str | None
    to_address: str | None
    value_native: float | None
    block_number: int | None


class ChainVerificationService:
    def __init__(self, http_client: httpx.AsyncClient, rpc_urls: dict[str, str] | None = None) -> None:
        self._http = http_client
        self._rpc_urls = {**_DEFAULT_RPC_URLS, **(rpc_urls or {})}

    def supported_chains(self) -> list[str]:
        return sorted(self._rpc_urls)

    async def resolve_evidence(
        self, *, chain: str | None, tx_hash_raw: str, claimed_amount: float | None
    ) -> tuple[VerificationStatus, dict[str, Any]]:
        """The one entry point the dispute pipeline calls: given what was
        submitted as evidence, returns a status plus the raw facts to show
        a human or feed an LLM as grounding context."""
        chain_key = (chain or "").strip().lower()
        tx_hash = _extract_tx_hash(tx_hash_raw)

        if not chain_key:
            return "invalid_format", {"reason": "No chain specified for tx_reference evidence."}
        if chain_key not in self._rpc_urls:
            return "unsupported_chain", {
                "chain": chain_key,
                "reason": f"'{chain_key}' is not a supported chain.",
                "supported_chains": self.supported_chains(),
            }
        if tx_hash is None:
            return "invalid_format", {
                "chain": chain_key,
                "reason": "Could not find a valid 0x-prefixed transaction hash.",
            }

        try:
            facts = await self._fetch_tx_facts(chain_key, tx_hash)
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.warning("chain_verification_unreachable", chain=chain_key, tx_hash=tx_hash, error=str(exc))
            return "unverifiable", {
                "chain": chain_key,
                "tx_hash": tx_hash,
                "reason": "Could not reach the chain RPC endpoint.",
            }

        details: dict[str, Any] = {
            "chain": chain_key,
            "tx_hash": tx_hash,
            "explorer_url": _EXPLORER_URLS.get(chain_key, "").format(hash=tx_hash) or None,
            "from_address": facts.from_address,
            "to_address": facts.to_address,
            "value_native": facts.value_native,
            "block_number": facts.block_number,
        }

        if not facts.exists:
            return "not_found", details
        if not facts.confirmed:
            return "pending", details
        if facts.success is False:
            return "failed_onchain", details

        if claimed_amount is None or facts.value_native is None:
            return "confirmed", details

        matches = _values_match(facts.value_native, claimed_amount)
        details["claimed_amount"] = claimed_amount
        return ("confirmed_match" if matches else "confirmed_mismatch"), details

    async def _fetch_tx_facts(self, chain: str, tx_hash: str) -> ChainTxFacts:
        rpc_url = self._rpc_urls[chain]
        tx_response, receipt_response = await self._gather_rpc(
            rpc_url,
            ("eth_getTransactionByHash", [tx_hash]),
            ("eth_getTransactionReceipt", [tx_hash]),
        )

        tx = tx_response.get("result") if tx_response else None
        receipt = receipt_response.get("result") if receipt_response else None

        if tx is None:
            return ChainTxFacts(
                exists=False, confirmed=False, success=None,
                from_address=None, to_address=None, value_native=None, block_number=None,
            )

        block_number = _hex_to_int(tx.get("blockNumber"))
        value_native = _wei_hex_to_native(tx.get("value"))

        if receipt is None or receipt.get("blockNumber") is None:
            return ChainTxFacts(
                exists=True, confirmed=False, success=None,
                from_address=tx.get("from"), to_address=tx.get("to"),
                value_native=value_native, block_number=block_number,
            )

        status_hex = receipt.get("status")
        success = _hex_to_int(status_hex) == 1 if status_hex is not None else None

        return ChainTxFacts(
            exists=True,
            confirmed=True,
            success=success,
            from_address=tx.get("from"),
            to_address=tx.get("to"),
            value_native=value_native,
            block_number=_hex_to_int(receipt.get("blockNumber")) or block_number,
        )

    async def _gather_rpc(
        self, rpc_url: str, *calls: tuple[str, list[Any]]
    ) -> list[dict[str, Any] | None]:
        import asyncio

        async def _call(method: str, params: list[Any]) -> dict[str, Any] | None:
            response = await self._http.post(
                rpc_url,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                timeout=httpx.Timeout(10.0, connect=5.0),
            )
            response.raise_for_status()
            return response.json()

        return await asyncio.gather(*(_call(method, params) for method, params in calls))


def _extract_tx_hash(raw: str) -> str | None:
    match = re.search(r"0x[0-9a-fA-F]{64}", raw or "")
    if not match:
        return None
    candidate = match.group(0)
    return candidate if _TX_HASH_RE.match(candidate) else None


def _hex_to_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value, 16)
    except (TypeError, ValueError):
        return None


def _wei_hex_to_native(value: str | None) -> float | None:
    wei = _hex_to_int(value)
    if wei is None:
        return None
    return wei / 1e18


def _values_match(actual: float, claimed: float) -> bool:
    if claimed == 0:
        return actual == 0
    return abs(actual - claimed) / abs(claimed) <= _VALUE_MATCH_TOLERANCE


def parse_rpc_url_overrides(raw: str) -> dict[str, str]:
    """Parses the CHAIN_RPC_URLS setting: "base=https://x,ethereum=https://y" """
    overrides: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        chain, url = part.split("=", 1)
        chain, url = chain.strip().lower(), url.strip()
        if chain and url:
            overrides[chain] = url
    return overrides
