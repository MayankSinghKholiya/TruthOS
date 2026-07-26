"""Facade unifying episodic and project memory behind one API used by the
orchestrator. Compression of raw investigation output into a durable
memory entry is the Memory Agent's job (app/agents/memory_agent.py) - this
manager only persists/retrieves what it's given.

There was a third component here, semantic memory (embedding similarity
search over past investigation summaries via Qdrant), dropped along with
the rest of the dense-vector/sentence-transformers stack to keep the
service's memory footprint inside Render's free-tier limit - recent
history from episodic memory still gives the Planner real context, just
not similarity-ranked across the user's entire history."""
from uuid import UUID

from app.memory.episodic import EpisodicMemoryStore
from app.memory.project import ProjectMemoryStore


class MemoryManager:
    def __init__(
        self,
        episodic: EpisodicMemoryStore,
        project: ProjectMemoryStore,
    ) -> None:
        self.episodic = episodic
        self.project = project

    async def commit(
        self,
        *,
        user_id: UUID,
        session_id: UUID | None,
        summary: str,
        entities: list[str],
        outcome: str,
    ) -> None:
        await self.episodic.record(
            user_id=user_id,
            session_id=session_id,
            summary=summary,
            entities=entities,
            outcome=outcome,
        )

    async def recall_context(self, *, user_id: UUID) -> str:
        """Builds a compact text block of relevant prior memory for the Planner."""
        episodic_entries = await self.episodic.recent_for_user(user_id, limit=5)

        lines = []
        if episodic_entries:
            lines.append("Recent history:")
            lines.extend(f"- {entry.summary} (outcome: {entry.outcome})" for entry in episodic_entries)
        return "\n".join(lines) if lines else "No relevant prior memory."
