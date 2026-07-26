"""LLM-driven entity/relation triple extraction feeding the knowledge graph."""
from app.core.logging import get_logger
from app.graph.knowledge_graph import Triple
from app.prompts.loader import get_prompt
from app.services.llm_router import LLMRouter

logger = get_logger(__name__)


class TripleExtractor:
    def __init__(self, llm_router: LLMRouter) -> None:
        self._llm_router = llm_router

    async def extract(self, text: str) -> list[Triple]:
        if not text.strip():
            return []
        template = get_prompt("extraction")
        system, user = template.render(text=text)
        try:
            result, _ = await self._llm_router.complete_json(
                system=system, user=user, agent_name="extraction", temperature=0.0
            )
        except Exception as exc:
            logger.warning("triple_extraction_failed", error=str(exc))
            return []

        triples = []
        for raw in result.get("triples", []):
            try:
                triples.append(
                    Triple(
                        subject=raw["subject"],
                        relation=raw["relation"],
                        object=raw["object"],
                        confidence=float(raw.get("confidence", 0.7)),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return triples
