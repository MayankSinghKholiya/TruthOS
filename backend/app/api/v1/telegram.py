"""Telegram notifications: linking a TruthOS account to a Telegram chat,
and managing which wallets that account wants watched for red-flag
activity (see app.services.telegram_notify for what actually triggers a
notification)."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_telegram_bot_service
from app.core.container import get_redis
from app.core.exceptions import NotFoundError
from app.db.models.telegram import TelegramLink, WalletWatch
from app.db.models.user import User
from app.schemas.telegram import LinkStartRead, LinkStatusRead, WalletWatchCreate, WalletWatchRead
from app.services.telegram_bot import TelegramBotService
from app.services.telegram_linking import CODE_TTL_SECONDS, generate_link_code

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/link/start", response_model=LinkStartRead)
async def start_link(
    current_user: User = Depends(get_current_user),
    bot: TelegramBotService = Depends(get_telegram_bot_service),
) -> LinkStartRead:
    redis = get_redis()
    code = await generate_link_code(redis, current_user.id)
    bot_username = await bot.get_bot_username()
    return LinkStartRead(code=code, bot_username=bot_username, expires_in_seconds=CODE_TTL_SECONDS)


@router.get("/link/status", response_model=LinkStatusRead)
async def link_status(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> LinkStatusRead:
    result = await db.execute(select(TelegramLink).where(TelegramLink.user_id == current_user.id))
    link = result.scalar_one_or_none()
    if link is None:
        return LinkStatusRead(linked=False)
    return LinkStatusRead(linked=True, telegram_username=link.telegram_username, linked_at=link.linked_at)


@router.delete("/link", status_code=204)
async def unlink(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    result = await db.execute(select(TelegramLink).where(TelegramLink.user_id == current_user.id))
    link = result.scalar_one_or_none()
    if link is not None:
        await db.delete(link)
        await db.commit()


@router.post("/watches", response_model=WalletWatchRead, status_code=201)
async def create_watch(
    payload: WalletWatchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WalletWatch:
    existing = await db.execute(
        select(WalletWatch).where(
            WalletWatch.user_id == current_user.id, WalletWatch.wallet_id == payload.wallet_id
        )
    )
    watch = existing.scalar_one_or_none()
    if watch is not None:
        return watch

    watch = WalletWatch(user_id=current_user.id, wallet_id=payload.wallet_id, label=payload.label)
    db.add(watch)
    await db.commit()
    await db.refresh(watch)
    return watch


@router.get("/watches", response_model=list[WalletWatchRead])
async def list_watches(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[WalletWatch]:
    result = await db.execute(
        select(WalletWatch)
        .where(WalletWatch.user_id == current_user.id)
        .order_by(WalletWatch.created_at.desc())
    )
    return list(result.scalars().all())


@router.delete("/watches/{watch_id}", status_code=204)
async def delete_watch(
    watch_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    watch = await db.get(WalletWatch, watch_id)
    if watch is None or watch.user_id != current_user.id:
        raise NotFoundError("Watch not found")
    await db.delete(watch)
    await db.commit()
