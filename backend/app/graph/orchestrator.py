"""LangGraph orchestration of the TruthOS pipeline:

    Planner -> Task Decomposition -> Specialist Agents -> Retrieval
    -> Truth Engine -> Debate Engine (Fact Checker + Critic) -> Judge
    -> Writer -> Memory -> Layered Report

Each stage is a graph node backed by one agent (or a small group of agents
for the debate stage). Nodes return partial state dicts that LangGraph
merges, so every node is independently testable and the whole pipeline is
resumable/streamable.
"""
import asyncio
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.agents.coder import CoderAgent
from app.agents.critic import CriticAgent
from app.agents.evidence_utils import deduplicate_evidence, remap_claim_evidence_indices
from app.agents.fact_checker import FactCheckerAgent
from app.agents.finance import FinanceAgent
from app.agents.judge import JudgeAgent
from app.agents.legal import LegalAgent
from app.agents.memory_agent import MemoryAgent
from app.agents.planner import PlannerAgent
from app.agents.research import ResearchAgent
from app.agents.retriever import RetrieverAgent
from app.agents.truth import TruthAgent
from app.agents.writer import WriterAgent
from app.core.logging import get_logger
from app.graph.extraction import TripleExtractor
from app.graph.knowledge_graph import KnowledgeGraph
from app.graph.state import GraphState
from app.memory.manager import MemoryManager
from app.rag.hybrid_retriever import HybridRetriever, RetrievedChunk
from app.schemas.agent import AgentStatus
from app.schemas.chat import StreamEvent, StreamEventType
from app.schemas.report import (
    ConfidenceBreakdown,
    CounterArgument,
    EntityAmbiguity,
    LayeredReport,
    ReferenceItem,
)
from app.services.confidence import CritiqueSignal, compute_confidence
from app.services.llm_router import LLMRouter
from app.services.market_data import MarketDataService

logger = get_logger(__name__)

_SPECIALIST_AGENTS = {"finance", "legal", "coder"}


class Orchestrator:
    def __init__(
        self,
        llm_router: LLMRouter,
        hybrid_retriever: HybridRetriever,
        knowledge_graph: KnowledgeGraph,
        memory_manager: MemoryManager,
        market_data: MarketDataService,
    ) -> None:
        self._retriever_svc = hybrid_retriever
        self._kg = knowledge_graph
        self._memory = memory_manager
        self._market_data = market_data
        self._triple_extractor = TripleExtractor(llm_router)

        self.planner = PlannerAgent(llm_router)
        self.retriever_agent = RetrieverAgent(llm_router)
        self.research = ResearchAgent(llm_router)
        self.finance = FinanceAgent(llm_router)
        self.legal = LegalAgent(llm_router)
        self.coder = CoderAgent(llm_router)
        self.fact_checker = FactCheckerAgent(llm_router)
        self.critic = CriticAgent(llm_router)
        self.truth = TruthAgent(llm_router)
        self.judge = JudgeAgent(llm_router)
        self.writer = WriterAgent(llm_router)
        self.memory_agent = MemoryAgent(llm_router)

        self._graph = self._build_graph()

    # ---- graph construction -------------------------------------------------

    def _build_graph(self):
        graph = StateGraph(GraphState)
        graph.add_node("plan", self._plan_node)
        graph.add_node("gather", self._gather_node)
        graph.add_node("verify", self._verify_node)
        graph.add_node("critique", self._critique_node)
        graph.add_node("reconcile", self._reconcile_node)
        graph.add_node("judge", self._judge_node)
        graph.add_node("write", self._write_node)
        graph.add_node("score_confidence", self._confidence_node)
        graph.add_node("commit_memory", self._memory_node)

        graph.set_entry_point("plan")
        graph.add_edge("plan", "gather")
        graph.add_edge("gather", "verify")
        graph.add_edge("verify", "critique")
        graph.add_edge("critique", "reconcile")
        graph.add_edge("reconcile", "judge")
        graph.add_edge("judge", "write")
        graph.add_edge("write", "score_confidence")
        graph.add_edge("score_confidence", "commit_memory")
        graph.add_edge("commit_memory", END)
        return graph.compile()

    # ---- nodes ---------------------------------------------------------------

    async def _plan_node(self, state: GraphState) -> dict:
        result = await self.planner.run(
            query=state["query"],
            context=state.get("context", ""),
            memory=state.get("memory_context", ""),
        )
        sub_tasks = result.output.get("sub_tasks") or [
            {"objective": state["query"], "assigned_agent": "research", "requires_web": True}
        ]
        return {
            "sub_tasks": sub_tasks,
            "agent_trace": [_trace(result)],
        }

    async def _gather_node(self, state: GraphState) -> dict:
        sub_tasks = state.get("sub_tasks", [])
        # Sub-tasks are independent (each is its own retrieve-then-research
        # slice), so running them concurrently instead of one-by-one is what
        # keeps latency from stacking linearly with plan complexity - a
        # 4-sub-task plan takes as long as the slowest sub-task, not the sum.
        results = await asyncio.gather(
            *(self._process_sub_task(sub_task, state["query"]) for sub_task in sub_tasks)
        )

        all_chunks: list[RetrievedChunk] = []
        all_claims: list[dict] = []
        specialist_outputs: list[dict] = []
        trace = []

        for chunks, claims, specialist_output, sub_trace in results:
            # Each sub-task's claims cite evidence by index into *its own*
            # local chunk list - offset by the running total before merging
            # so every claim's evidence_indices point into the combined list.
            offset = len(all_chunks)
            for claim in claims:
                local_indices = claim.get("evidence_indices", [])
                claim["evidence_indices"] = [
                    offset + i for i in local_indices if isinstance(i, int)
                ]
            all_chunks.extend(chunks)
            all_claims.extend(claims)
            if specialist_output is not None:
                specialist_outputs.append(specialist_output)
            trace.extend(sub_trace)

        # Different sub-tasks' retrieval frequently surfaces the same source
        # (overlapping search terms) - dedup globally so it isn't double
        # counted in Confidence DNA or shown twice in References, remapping
        # claims' evidence_indices so they still point at the right evidence.
        all_chunks, index_map = deduplicate_evidence(all_chunks)
        remap_claim_evidence_indices(all_claims, index_map)

        return {
            "evidence_chunks": all_chunks,
            "claims": all_claims,
            "specialist_outputs": specialist_outputs,
            "agent_trace": state.get("agent_trace", []) + trace,
        }

    async def _process_sub_task(
        self, sub_task: dict, query: str
    ) -> tuple[list[RetrievedChunk], list[dict], dict | None, list[dict]]:
        objective = sub_task.get("objective", query)
        assigned_agent = sub_task.get("assigned_agent", "research")
        trace = []

        kg_context = ""
        if sub_task.get("requires_kg"):
            kg_context = await self._fetch_kg_context(objective)

        expansion = await self.retriever_agent.run(objective=objective, query=query, kg_context=kg_context)
        trace.append(_trace(expansion))
        queries = expansion.output.get("queries", [objective])
        filters = expansion.output.get("filters") or {}

        chunks = await self._retriever_svc.retrieve(
            queries,
            include_web=sub_task.get("requires_web", True),
            domain_filter=filters.get("domains") or None,
            date_after=filters.get("date_after") or None,
        )

        if assigned_agent in _SPECIALIST_AGENTS:
            market_symbols = expansion.output.get("market_symbols") or {}
            specialist_result, extra_chunks = await self._run_specialist(
                assigned_agent, objective, chunks, market_symbols
            )
            trace.append(_trace(specialist_result))
            # A specialist's own finding must reach Fact Checker/Truth/Judge
            # the same way a Research claim does, or it's computed and then
            # silently dropped before the verdict - which is exactly what
            # was happening here before this fix. Wrapping it as a claim
            # (citing whatever evidence this sub-task gathered, including
            # any synthetic market-data chunks) reuses the courtroom
            # pipeline's existing, already-correct claim/evidence handling
            # instead of requiring every downstream node to special-case
            # specialist output.
            all_local_chunks = chunks + extra_chunks
            claims = _claims_from_specialist_output(specialist_result.output, len(all_local_chunks))
            return all_local_chunks, claims, specialist_result.output, trace

        research_result = await self.research.run(objective=objective, evidence_chunks=chunks)
        trace.append(_trace(research_result))
        return chunks, research_result.output.get("claims", []), None, trace

    async def _fetch_kg_context(self, objective: str) -> str:
        """Only called when the Planner set requires_kg=true for this
        sub-task. Reuses the same TripleExtractor that turns a resolved
        investigation into stored triples - here run on the objective text
        itself, just to name the entities worth looking up - then asks the
        graph what it already knows about them from prior investigations.
        Neo4j/extraction failures degrade to "no context" rather than
        failing the whole sub-task; a KG assist is a bonus, not a
        dependency."""
        try:
            triples = await self._triple_extractor.extract(objective)
            entities = sorted({t.subject for t in triples} | {t.object for t in triples})
            if not entities:
                return ""
            records = await self._kg.find_related_entities(entities)
        except Exception as exc:  # noqa: BLE001 - a KG assist must never break retrieval
            logger.warning("kg_context_lookup_failed", objective=objective, error=str(exc))
            return ""
        return _format_kg_context(records)

    async def _run_specialist(
        self,
        agent_name: str,
        objective: str,
        chunks: list[RetrievedChunk],
        market_symbols: dict,
    ) -> tuple[Any, list[RetrievedChunk]]:
        """Returns (agent_result, extra_evidence_chunks) - extra_evidence_chunks
        are synthetic evidence the specialist's own tools produced (e.g. a
        live price quote), appended to this sub-task's evidence so Fact
        Checker has something concrete to verify the claim against."""
        if agent_name == "finance":
            market_data = await self._market_data.fetch(
                crypto_ids=market_symbols.get("crypto_ids", []),
                equity_symbols=market_symbols.get("equity_symbols", []),
            )
            result = await self.finance.run(objective=objective, market_data=market_data)
            return result, _market_data_to_chunks(market_data)
        if agent_name == "legal":
            result = await self.legal.run(objective=objective, evidence_chunks=chunks)
            return result, []
        if agent_name == "coder":
            result = await self.coder.run(objective=objective, evidence_chunks=chunks)
            return result, []
        result = await self.research.run(objective=objective, evidence_chunks=chunks)
        return result, []

    async def _verify_node(self, state: GraphState) -> dict:
        result = await self.fact_checker.run(
            claims=state.get("claims", []), evidence_chunks=state.get("evidence_chunks", [])
        )
        return {
            "fact_check_results": result.output,
            "agent_trace": state.get("agent_trace", []) + [_trace(result)],
        }

    async def _critique_node(self, state: GraphState) -> dict:
        result = await self.critic.run(
            facts=state.get("fact_check_results", {}), claims=state.get("claims", [])
        )
        return {
            "critic_results": result.output,
            "agent_trace": state.get("agent_trace", []) + [_trace(result)],
        }

    async def _reconcile_node(self, state: GraphState) -> dict:
        result = await self.truth.run(
            research_claims=state.get("claims", []),
            fact_check_findings=state.get("fact_check_results", {}).get("verifications", []),
            evidence_consistency=state.get("fact_check_results", {}).get("evidence_consistency", {}),
            critic_objections=state.get("critic_results", {}).get("skeptic_objections", []),
        )
        return {
            "reconciliation": result.output,
            "agent_trace": state.get("agent_trace", []) + [_trace(result)],
        }

    async def _judge_node(self, state: GraphState) -> dict:
        result = await self.judge.run(
            reconciliation=state.get("reconciliation", {}),
            critic_findings=state.get("critic_results", {}),
            fact_check_results=state.get("fact_check_results", {}),
        )
        return {
            "judge_output": result.output,
            "agent_trace": state.get("agent_trace", []) + [_trace(result)],
        }

    async def _write_node(self, state: GraphState) -> dict:
        judge_output = state.get("judge_output", {})
        result = await self.writer.run(
            verdict=judge_output.get("verdict", "Inconclusive"),
            executive_summary=judge_output.get("executive_summary", ""),
            deep_dive=judge_output.get("deep_dive", ""),
        )
        return {
            "writer_output": result.output,
            "agent_trace": state.get("agent_trace", []) + [_trace(result)],
        }

    async def _confidence_node(self, state: GraphState) -> dict:
        from app.agents.evidence_utils import to_evidence_items

        chunks: list[RetrievedChunk] = state.get("evidence_chunks", [])
        evidence_items = to_evidence_items(chunks)
        critic_results = state.get("critic_results", {})
        objections = critic_results.get("skeptic_objections", [])
        critique_signal = CritiqueSignal(
            objection_count=len(objections),
            mean_objection_severity=(
                sum(o.get("severity", 0.5) for o in objections) / len(objections)
                if objections
                else 0.0
            ),
        )
        breakdown = compute_confidence(
            evidence=evidence_items,
            published_dates=[c.published_at for c in chunks],
            critique=critique_signal,
            retrieval_scores=[c.retrieval_score for c in chunks],
        )
        return {"confidence": breakdown.model_dump()}

    async def _memory_node(self, state: GraphState) -> dict:
        judge_output = state.get("judge_output", {})
        writer_output = state.get("writer_output", {})
        result = await self.memory_agent.run(
            query=state["query"],
            verdict=writer_output.get("verdict_headline", judge_output.get("verdict", "")),
            executive_summary=writer_output.get(
                "executive_summary", judge_output.get("executive_summary", "")
            ),
        )
        memory_output = result.output
        await self._memory.commit(
            user_id=state["user_id"],
            session_id=state.get("session_id"),
            summary=memory_output.get("summary", state["query"]),
            entities=memory_output.get("entities", []),
            outcome=memory_output.get("outcome", "resolved"),
        )

        full_text = f"{state['query']}\n{memory_output.get('summary', '')}"
        triples = await self._triple_extractor.extract(full_text)
        await self._kg.upsert_triples(triples)

        return {"agent_trace": state.get("agent_trace", []) + [_trace(result)]}

    # ---- public API -----------------------------------------------------------

    async def run(
        self,
        *,
        query: str,
        user_id: UUID,
        session_id: UUID | None,
        context: str = "",
        memory_context: str = "",
    ) -> LayeredReport:
        final_state: GraphState = await self._graph.ainvoke(
            {
                "query": query,
                "user_id": user_id,
                "session_id": session_id,
                "context": context,
                "memory_context": memory_context,
                "agent_trace": [],
            }
        )
        return _assemble_report(final_state)

    async def stream(
        self,
        *,
        query: str,
        user_id: UUID,
        session_id: UUID | None,
        context: str = "",
        memory_context: str = "",
    ) -> AsyncIterator[StreamEvent]:
        initial_state: GraphState = {
            "query": query,
            "user_id": user_id,
            "session_id": session_id,
            "context": context,
            "memory_context": memory_context,
            "agent_trace": [],
        }
        final_state: GraphState = dict(initial_state)  # type: ignore[assignment]
        async for step in self._graph.astream(initial_state):
            for node_name, partial in step.items():
                if partial:
                    final_state.update(partial)
                yield StreamEvent(
                    type=StreamEventType.AGENT_COMPLETED,
                    agent_name=node_name,
                    data={"keys": list(partial.keys()) if partial else []},
                )
        yield StreamEvent(
            type=StreamEventType.REPORT_READY,
            data=_assemble_report(final_state).model_dump(mode="json"),
        )


def _trace(result) -> dict:
    return {
        "agent": result.agent_name,
        "status": result.status.value if isinstance(result.status, AgentStatus) else result.status,
        "confidence": result.confidence,
        "model_used": result.model_used,
        "retries_used": result.retries_used,
    }


def _format_kg_context(records: list[dict[str, Any]]) -> str:
    if not records:
        return ""
    lines = []
    for record in records[:10]:  # bound the prompt - this is context, not the whole graph
        relation = record.get("relation") or record.get("relation_type") or "relates_to"
        confidence = record.get("confidence")
        suffix = f" (confidence {confidence:.2f})" if isinstance(confidence, (int, float)) else ""
        lines.append(f"{record.get('entity')} {relation} {record.get('related_entity')}{suffix}")
    return "\n".join(lines)


def _market_data_to_chunks(market_data: list[dict[str, Any]]) -> list[RetrievedChunk]:
    """Turns a CoinGecko/AlphaVantage lookup into evidence chunks so a price
    is something Fact Checker can point at, not just a number the Finance
    agent asserts."""
    chunks = []
    for entry in market_data:
        if "coin_id" in entry:
            coin_id = entry["coin_id"]
            text = (
                f"{coin_id} price: {entry.get('price')} {entry.get('currency', 'usd').upper()} "
                f"(CoinGecko, as of {entry.get('as_of')})"
            )
            source_url = f"https://www.coingecko.com/en/coins/{coin_id}"
            title = f"{coin_id} live price (CoinGecko)"
        else:
            symbol = entry.get("symbol", "unknown")
            text = f"{symbol} price: {entry.get('price')} (AlphaVantage, as of {entry.get('as_of')})"
            source_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}"
            title = f"{symbol} live quote (AlphaVantage)"

        chunks.append(
            RetrievedChunk(
                text=text,
                source_url=source_url,
                source_title=title,
                published_at=None,
                source="market_data",
                retrieval_score=1.0,  # authoritative structured data, not a search-ranked guess
            )
        )
    return chunks


def _claims_from_specialist_output(output: dict[str, Any], evidence_count: int) -> list[dict]:
    """Wraps a specialist agent's finding (Finance/Legal use "analysis",
    Coder uses "explanation") as a single claim citing every piece of
    evidence gathered for its sub-task, so it flows through Fact Checker /
    Truth Engine / Judge exactly like a Research claim would."""
    statement = output.get("analysis") or output.get("explanation") or ""
    if not statement:
        return []
    return [
        {
            "statement": statement,
            "evidence_indices": list(range(evidence_count)),
            "confidence": 0.7,
        }
    ]


def _assemble_report(state: GraphState) -> LayeredReport:
    judge_output = state.get("judge_output", {})
    writer_output = state.get("writer_output", {})
    confidence = state.get("confidence") or {
        "source_diversity": 0.0,
        "freshness": 0.0,
        "consensus": 0.0,
        "evidence_quality": 0.0,
        "retrieval_confidence": 0.0,
        "overall": 0.0,
    }
    chunks: list[RetrievedChunk] = state.get("evidence_chunks", [])

    from app.agents.evidence_utils import to_evidence_items

    evidence_items = to_evidence_items(chunks)
    # Assign each claim's statement to the evidence it actually cites (via
    # its own evidence_indices) rather than by position - evidence_items
    # spans every sub-task's retrieval while claims only exist for
    # research-assigned sub-tasks, so the two lists don't line up 1:1.
    for claim in state.get("claims", []):
        statement = claim.get("statement", "")
        for idx in claim.get("evidence_indices", []):
            if isinstance(idx, int) and 0 <= idx < len(evidence_items) and not evidence_items[idx].claim:
                evidence_items[idx].claim = statement

    references = [
        ReferenceItem(title=c.source_title or c.source_url or "source", url=c.source_url, published_at=c.published_at)
        for c in chunks
        if c.source_url
    ]

    counter_arguments = [
        CounterArgument(
            argument=arg.get("argument", ""),
            raised_by=arg.get("raised_by", "critic"),
            strength=float(arg.get("strength", 0.5)),
        )
        for arg in judge_output.get("counter_arguments", [])
    ]

    raw_ambiguity = state.get("reconciliation", {}).get("entity_ambiguity")
    entity_ambiguity = (
        EntityAmbiguity(**raw_ambiguity)
        if raw_ambiguity and raw_ambiguity.get("is_ambiguous")
        else None
    )

    return LayeredReport(
        query=state["query"],
        verdict=writer_output.get("verdict_headline") or judge_output.get("verdict", "Inconclusive"),
        executive_summary=writer_output.get("executive_summary")
        or judge_output.get("executive_summary", ""),
        confidence=ConfidenceBreakdown(**confidence),
        evidence=evidence_items,
        counter_arguments=counter_arguments,
        deep_dive=writer_output.get("deep_dive") or judge_output.get("deep_dive", ""),
        references=references,
        agent_trace=state.get("agent_trace", []),
        entity_ambiguity=entity_ambiguity,
    )
