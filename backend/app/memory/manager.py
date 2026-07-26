"""Facade unifying semantic, episodic and project memory behind one API used
by the orchestrator. Compression of raw investigation output into a durable
memory entry is the Memory Agent's job (app/agents/memory_agent.py) - this
manager only persists/retrieves what it's given."""
from uuid import UUID

from app.memory.episodic import EpisodicMemoryStore
from app.memory.project import ProjectMemoryStore
from app.memory.semantic import SemanticMemory


class MemoryManager:
    def __init__(
        self,
        semantic: SemanticMemory,
        episodic: EpisodicMemoryStore,
        project: ProjectMemoryStore,
    ) -> None:
        self.semantic = semantic
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
        await self.semantic.remember(user_id=str(user_id), summary=summary, entities=entities)

    async def recall_context(self, *, user_id: UUID, query: str) -> str:
        """Builds a compact text block of relevant prior memory for the Planner."""
        semantic_hits = await self.semantic.recall(user_id=str(user_id), query=query)
        episodic_entries = await self.episodic.recent_for_user(user_id, limit=5)

        lines = []
        if semantic_hits:
            lines.append("Similar past investigations:")
            lines.extend(f"- {hit.text}" for hit in semantic_hits)
        if episodic_entries:
            lines.append("Recent history:")
            lines.extend(f"- {entry.summary} (outcome: {entry.outcome})" for entry in episodic_entries)
        return "\n".join(lines) if lines else "No relevant prior memory."
