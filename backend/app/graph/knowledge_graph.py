"""Neo4j-backed knowledge graph: stores (Entity)-[RELATION]->(Entity) triples
extracted from resolved investigations, and lets the Planner/Research agents
query prior relationships instead of re-deriving them from scratch."""
from dataclasses import dataclass
from typing import Any

from neo4j import AsyncDriver

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Triple:
    subject: str
    relation: str
    object: str
    confidence: float = 1.0
    source: str | None = None


class KnowledgeGraph:
    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    async def ensure_constraints(self) -> None:
        async with self._driver.session() as session:
            await session.run(
                "CREATE CONSTRAINT entity_name IF NOT EXISTS "
                "FOR (e:Entity) REQUIRE e.name IS UNIQUE"
            )

    async def upsert_triples(self, triples: list[Triple]) -> None:
        if not triples:
            return
        async with self._driver.session() as session:
            for triple in triples:
                await session.run(
                    """
                    MERGE (s:Entity {name: $subject})
                    MERGE (o:Entity {name: $object})
                    MERGE (s)-[r:RELATES {type: $relation}]->(o)
                    SET r.confidence = $confidence, r.source = $source
                    """,
                    subject=triple.subject,
                    object=triple.object,
                    relation=triple.relation,
                    confidence=triple.confidence,
                    source=triple.source,
                )

    async def neighbors(self, entity: str, *, depth: int = 1) -> list[dict[str, Any]]:
        query = f"""
            MATCH (e:Entity {{name: $entity}})-[r:RELATES*1..{depth}]-(neighbor:Entity)
            RETURN DISTINCT neighbor.name AS name, r AS relations
            LIMIT 25
        """
        async with self._driver.session() as session:
            result = await session.run(query, entity=entity)
            records = [record.data() async for record in result]
        return records

    async def find_related_entities(self, entities: list[str]) -> list[dict[str, Any]]:
        if not entities:
            return []
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity)-[r:RELATES]-(other:Entity)
                WHERE e.name IN $entities
                RETURN e.name AS entity, type(r) AS relation_type, r.type AS relation,
                       other.name AS related_entity, r.confidence AS confidence
                LIMIT 50
                """,
                entities=entities,
            )
            return [record.data() async for record in result]
