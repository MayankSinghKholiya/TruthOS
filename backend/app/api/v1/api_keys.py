"""Issuing/revoking the API keys that let other agents call TruthOS Court's
agent-callable endpoints (POST /disputes/agent) as a given wallet, instead of
going through a human JWT login. A human still owns and can revoke each key -
this is a delegated credential, not a separate identity system."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import NotFoundError
from app.core.security import generate_api_key
from app.db.models.api_key import ApiKey
from app.db.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyRead

router = APIRouter(tags=["api-keys"])


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(
    payload: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreated:
    raw_key, key_hash, key_prefix = generate_api_key()
    api_key = ApiKey(
        created_by_user_id=current_user.id,
        wallet_id=payload.wallet_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        label=payload.label,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return ApiKeyCreated(
        id=api_key.id,
        key=raw_key,
        key_prefix=api_key.key_prefix,
        wallet_id=api_key.wallet_id,
        label=api_key.label,
        created_at=api_key.created_at,
    )


@router.get("/api-keys", response_model=list[ApiKeyRead])
async def list_api_keys(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.created_by_user_id == current_user.id)
        .order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    api_key = await db.get(ApiKey, key_id)
    if api_key is None or api_key.created_by_user_id != current_user.id:
        raise NotFoundError("API key not found")
    api_key.revoked_at = datetime.now(timezone.utc)
    await db.commit()
