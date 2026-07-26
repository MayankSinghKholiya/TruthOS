"""Shared best-effort webhook notifier for agent-callable endpoints that
accept a callback_url (Court disputes, chat/research queries) - fire the
result at the caller's URL once background processing finishes, but never
let a dead/slow callback endpoint affect the job that produced the result."""
from typing import Any

import httpx

from app.core.container import get_http_client
from app.core.logging import get_logger

logger = get_logger(__name__)


async def notify_callback(callback_url: str, payload: dict[str, Any]) -> None:
    try:
        response = await get_http_client().post(
            callback_url, json=payload, timeout=httpx.Timeout(10.0, connect=5.0)
        )
        response.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("callback_notify_failed", callback_url=callback_url, error=str(exc))
