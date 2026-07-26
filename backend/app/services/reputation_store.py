from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.dispute import AgentReputation
from app.services.reputation import DEFAULT_TRUST_SCORE


class ReputationStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, wallet_id: str) -> AgentReputation | None:
        result = await self._session.execute(
            select(AgentReputation).where(AgentReputation.wallet_id == wallet_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, wallet_id: str) -> AgentReputation:
        reputation = await self.get(wallet_id)
        if reputation is None:
            reputation = AgentReputation(wallet_id=wallet_id, trust_score=DEFAULT_TRUST_SCORE)
            self._session.add(reputation)
            await self._session.flush()
        return reputation
