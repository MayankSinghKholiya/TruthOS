"""Shared mutable state threaded through the LangGraph orchestration graph.
Every node reads what it needs and returns a partial dict LangGraph merges
back in - nodes never mutate state directly, keeping each node testable in
isolation."""
from typing import Any, TypedDict
from uuid import UUID


class GraphState(TypedDict, total=False):
    query: str
    user_id: UUID
    session_id: UUID | None
    context: str
    memory_context: str

    sub_tasks: list[dict[str, Any]]
    evidence_chunks: list[Any]  # list[RetrievedChunk], kept as Any to avoid import cycle
    claims: list[dict[str, Any]]
    specialist_outputs: list[dict[str, Any]]

    fact_check_results: dict[str, Any]
    critic_results: dict[str, Any]
    reconciliation: dict[str, Any]
    judge_output: dict[str, Any]
    writer_output: dict[str, Any]

    confidence: dict[str, Any]
    agent_trace: list[dict[str, Any]]
    errors: list[str]
