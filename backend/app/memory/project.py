"""Project memory: long-term rolling key/value context per user (e.g. a
running summary of an ongoing research project) that grows across sessions."""
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memory import ProjectMemory


class ProjectMemoryStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self, *, user_id: UUID, key: str, content: str, meta: dict[str, Any] | None = None
    ) -> ProjectMemory:
        existing = await self._get(user_id, key)
        if existing:
            existing.content = content
            existing.meta = meta
            await self._session.flush()
            return existing

        entry = ProjectMemory(user_id=user_id, key=key, content=content, meta=meta)
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get(self, user_id: UUID, key: str) -> ProjectMemory | None:
        return await self._get(user_id, key)

    async def _get(self, user_id: UUID, key: str) -> ProjectMemory | None:
        result = await self._session.execute(
            select(ProjectMemory).where(
                ProjectMemory.user_id == user_id, ProjectMemory.key == key
            )
        )
        return result.scalar_one_or_none()

    async def all_for_user(self, user_id: UUID) -> list[ProjectMemory]:
        result = await self._session.execute(
            select(ProjectMemory).where(ProjectMemory.user_id == user_id)
        )
        return list(result.scalars().all())
