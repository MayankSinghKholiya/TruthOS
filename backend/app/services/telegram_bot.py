"""Thin wrapper around the Telegram Bot HTTP API. sendMessage is used for
every outbound notification; getUpdates is used only by the long-poll
linking loop in app.services.telegram_linking, never per-request."""
import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_API_BASE = "https://api.telegram.org"


class TelegramBotService:
    def __init__(self, http_client: httpx.AsyncClient, bot_token: str | None = None) -> None:
        self._http = http_client
        self._token = bot_token if bot_token is not None else get_settings().telegram_bot_token

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    def _url(self, method: str) -> str:
        return f"{_API_BASE}/bot{self._token}/{method}"

    async def send_message(self, chat_id: str, text: str) -> bool:
        """Best-effort: a failed Telegram delivery must never break the
        dispute filing or verdict it's reporting on."""
        if not self.is_configured:
            return False
        try:
            response = await self._http.post(
                self._url("sendMessage"),
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                timeout=httpx.Timeout(10.0, connect=5.0),
            )
            response.raise_for_status()
            return True
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.warning("telegram_send_failed", chat_id=chat_id, error=str(exc))
            return False

    async def get_updates(self, offset: int | None, timeout: int = 25) -> list[dict]:
        """Long-poll: Telegram holds the connection open server-side until a
        new update arrives or `timeout` seconds pass, so the client-side
        httpx timeout must be comfortably longer than the poll timeout."""
        if not self.is_configured:
            return []
        params: dict[str, int] = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        response = await self._http.get(
            self._url("getUpdates"), params=params, timeout=httpx.Timeout(timeout + 10.0, connect=5.0)
        )
        response.raise_for_status()
        return response.json().get("result", [])

    async def get_bot_username(self) -> str | None:
        if not self.is_configured:
            return None
        try:
            response = await self._http.get(self._url("getMe"), timeout=httpx.Timeout(10.0, connect=5.0))
            response.raise_for_status()
            return response.json().get("result", {}).get("username")
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.warning("telegram_get_me_failed", error=str(exc))
            return None
