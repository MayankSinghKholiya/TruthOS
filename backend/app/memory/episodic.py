"""Episodic memory: a chronological log of resolved interactions, queryable
by user - 'what did we conclude about X, and when'."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memory import EpisodicMemory


class EpisodicMemoryStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        user_id: UUID,
        session_id: UUID | None,
        summary: str,
        entities: list[str],
        outcome: str = "resolved",
    ) -> EpisodicMemory:
        entry = EpisodicMemory(
            user_id=user_id,
            session_id=session_id,
            summary=summary,
            entities=entities,
            outcome=outcome,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def recent_for_user(self, user_id: UUID, limit: int = 10) -> list[EpisodicMemory]:
        result = await self._session.execute(
            select(EpisodicMemory)
            .where(EpisodicMemory.user_id == user_id)
            .order_by(EpisodicMemory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
