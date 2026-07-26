"""Links a TruthOS account to a Telegram chat.

A user can't just type in their own chat_id - there'd be no way to verify
they actually control it. Instead: TruthOS mints a short-lived one-time
code, the user sends it to the bot as `/start <code>` (either by typing it
or via a t.me deep link, which Telegram delivers identically either way),
and a background long-poll loop watches for that message, resolves the code
back to a user_id via Redis, and persists the chat_id it arrived from -
proof of control, since only the person holding that Telegram chat could
have sent it.
"""
import asyncio
import re
import secrets
from datetime import datetime, timezone
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models.telegram import TelegramLink
from app.db.session import get_session_factory
from app.services.telegram_bot import TelegramBotService

logger = get_logger(__name__)

CODE_TTL_SECONDS = 600  # 10 minutes - public: the API layer echoes this back to the client
_CODE_PREFIX = "telegram_link_code:"
_START_PATTERN = re.compile(r"^/start\s+(\d{6})\s*$")

# How long a getUpdates poll blocks server-side waiting for a new message.
# Telegram's own recommended long-poll timeout.
_POLL_TIMEOUT_SECONDS = 25


async def generate_link_code(redis: Redis, user_id: UUID) -> str:
    code = f"{secrets.randbelow(1_000_000):06d}"
    await redis.set(f"{_CODE_PREFIX}{code}", str(user_id), ex=CODE_TTL_SECONDS)
    return code


async def run_linking_poller(bot: TelegramBotService, redis: Redis) -> None:
    """Runs for the lifetime of the app (started from main.py's lifespan).
    Not per-request - getUpdates is a long-poll, so this is one continuously
    running loop, not something a request handler could do inline."""
    if not bot.is_configured:
        logger.info("telegram_poller_disabled_no_token")
        return

    offset: int | None = None
    while True:
        try:
            updates = await bot.get_updates(offset, timeout=_POLL_TIMEOUT_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - a transient network hiccup must not kill the poller
            logger.warning("telegram_poller_fetch_failed", error=str(exc))
            await asyncio.sleep(5)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            try:
                await _handle_update(update, bot, redis)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - one bad update must not kill the whole poller
                logger.warning("telegram_update_handling_failed", error=str(exc), exc_info=True)


async def _handle_update(update: dict, bot: TelegramBotService, redis: Redis) -> None:
    message = update.get("message") or {}
    text = message.get("text") or ""
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return

    match = _START_PATTERN.match(text.strip())
    if not match:
        return

    code = match.group(1)
    redis_key = f"{_CODE_PREFIX}{code}"
    user_id_raw = await redis.get(redis_key)
    if not user_id_raw:
        await bot.send_message(
            str(chat_id), "This code has expired or is invalid - generate a new one in TruthOS and try again."
        )
        return

    await redis.delete(redis_key)
    await _persist_link(UUID(user_id_raw), str(chat_id), chat.get("username"))
    await bot.send_message(
        str(chat_id),
        "✅ <b>TruthOS linked!</b> You'll get alerts here for wallets you're watching.",
    )


async def _persist_link(user_id: UUID, telegram_chat_id: str, telegram_username: str | None) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        existing = await session.execute(select(TelegramLink).where(TelegramLink.user_id == user_id))
        link = existing.scalar_one_or_none()
        if link is None:
            link = TelegramLink(
                user_id=user_id,
                telegram_chat_id=telegram_chat_id,
                telegram_username=telegram_username,
                linked_at=datetime.now(timezone.utc),
            )
            session.add(link)
        else:
            link.telegram_chat_id = telegram_chat_id
            link.telegram_username = telegram_username
            link.linked_at = datetime.now(timezone.utc)
        await session.commit()
