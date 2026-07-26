# Architecture

## Pipeline

Every query goes through the same LangGraph state machine
(`backend/app/graph/orchestrator.py`):

```
plan -> gather -> verify -> critique -> reconcile -> judge -> write
     -> score_confidence -> commit_memory
```

| Node              | Agent(s)                          | Purpose                                                            |
| ----------------- | ---------------------------------- | ------------------------------------------------------------------- |
| `plan`            | Planner                           | Decomposes the query into sub-tasks with an assigned specialist    |
| `gather`          | Retriever, Research/Finance/Legal | Expands queries, runs Hybrid RAG, builds the affirmative case       |
| `verify`          | Fact Checker                      | Verifies each claim strictly against retrieved evidence             |
| `critique`        | Critic (Skeptic + Devil's Advocate) | Attacks weak evidence, builds the strongest opposing case          |
| `reconcile`       | Truth Engine                      | Separates facts from opinions, flags open uncertainty               |
| `judge`           | Judge                             | Weighted-votes across all sides, issues the verdict                 |
| `write`           | Writer                            | Polishes the verdict into user-facing copy (no new claims)          |
| `score_confidence`| -                                  | Computes the Confidence DNA breakdown                                |
| `commit_memory`   | Memory                            | Compresses the resolved investigation into episodic + semantic memory, extracts knowledge-graph triples |

Every agent (`backend/app/agents/*.py`) is a thin subclass of `BaseAgent`
(`backend/app/agents/base.py`) that owns exactly one prompt template
(`backend/app/prompts/templates/*.yaml`), a declared input/output shape via
`AgentResult`, and a retry policy. Agents never call HTTP directly - they go
through `LLMRouter` (`backend/app/services/llm_router.py`), which retries
transient failures and falls back from `DEFAULT_MODEL` to `FALLBACK_MODEL`.

## Hybrid RAG

`backend/app/rag/hybrid_retriever.py` fans a query out across:

- **Dense retrieval** - Qdrant, via BAAI BGE embeddings (`rag/vector_store.py`, `rag/embeddings.py`)
- **Sparse retrieval** - BM25 over the same candidate pool (`rag/bm25.py`)
- **Live web search** - Tavily (`services/search_tools.py`)
- **Academic search** - Semantic Scholar (optional, `services/search_tools.py`)

Candidates are merged with Reciprocal Rank Fusion, then re-ordered by a
cross-encoder (`rag/reranker.py`) for the final top-k. Metadata filters
(domain, date) and query expansion (produced by the Retriever agent) are
applied before fusion.

## Knowledge graph

`backend/app/graph/knowledge_graph.py` stores `(Entity)-[RELATES]->(Entity)`
triples in Neo4j. Triples are extracted from resolved investigations by an
LLM call (`graph/extraction.py`, using the `extraction` prompt template) and
committed alongside memory in the `commit_memory` node.

## Memory

Three memory kinds, unified behind `MemoryManager`
(`backend/app/memory/manager.py`):

- **Semantic** - embedded investigation summaries in a separate Qdrant collection, searched by similarity
- **Episodic** - a chronological Postgres log of resolved interactions per user
- **Project** - long-term rolling key/value context per user

The Memory Agent decides *what* is worth remembering; `MemoryManager` only
persists/retrieves.

## Confidence DNA

`backend/app/services/confidence.py` combines five normalized signals into
one weighted score:

| Signal | Weight | What it measures |
| --- | --- | --- |
| Source diversity | 0.20 | Distinct domains backing the answer (log-scaled) |
| Freshness | 0.15 | Recency of evidence, linear decay over 3 years |
| Consensus | 0.25 | How many/severe the Critic's objections were |
| Evidence quality | 0.25 | Mean reliability of evidence used |
| Retrieval confidence | 0.15 | Mean cross-encoder relevance score |

With zero evidence the score short-circuits to 0 rather than letting neutral
defaults (e.g. "no objections because there was nothing to object to")
inflate it.

## Layered report

The final `LayeredReport` (`backend/app/schemas/report.py`) always contains,
in order: Verdict, Executive Summary, Confidence Dashboard, Evidence,
Counter-Arguments, Deep Dive, References - matching the product spec's
"Layered Output" exactly. The frontend renders this as tabs
(`frontend/src/components/report/LayeredReportView.tsx`).

## Streaming

`POST /api/v1/chat/query` streams Server-Sent Events as each graph node
completes (`agent_completed`), then a final `report_ready` event carrying the
full `LayeredReport`. The frontend can't use the native `EventSource` API
(it needs a POST body + auth header), so it parses the `text/event-stream`
framing manually off a `fetch()` `ReadableStream`
(`frontend/src/lib/api.ts#streamQuery`).

## Why these boundaries

- **Agents own their prompt, not their infra.** Swapping the retrieval
  backend or the LLM provider never touches `app/agents/*.py`.
- **The orchestrator owns sequencing, not logic.** Every node is a thin
  wrapper calling one agent; the actual reasoning lives in the agent + its
  prompt template, so nodes are trivially testable in isolation.
- **MemoryManager persists; MemoryAgent decides.** Keeps the storage facade
  free of LLM calls and the agent free of SQL/Qdrant details.
