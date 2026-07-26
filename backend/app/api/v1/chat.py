"""Chat endpoints: session management plus the streaming query endpoint that
drives the full Planner -> Courtroom -> Judge -> Writer pipeline and streams
per-agent progress events over SSE. Also the agent-callable (X-API-Key)
Verified Answers endpoints - the Chatbot service's counterpart to Court's
POST /disputes/agent, for callers (e.g. the OKX ASP bridge) that need a
plain request/response instead of holding open an SSE connection."""
import hashlib
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_agent_api_key,
    get_current_user,
    get_db,
    get_hybrid_retriever,
    get_knowledge_graph,
    get_llm_router,
    get_market_data_service,
    get_memory_manager,
    get_orchestrator,
)
from app.core.container import get_redis
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.models.api_key import ApiKey
from app.db.models.report import Report
from app.db.models.session_model import ChatMessage, ChatSession
from app.db.models.user import User
from app.db.session import get_session_factory
from app.graph.orchestrator import Orchestrator
from app.memory.episodic import EpisodicMemoryStore
from app.memory.manager import MemoryManager
from app.memory.project import ProjectMemoryStore
from app.schemas.chat import (
    AgentChatQueryCreate,
    ChatMessageRead,
    ChatQueryRequest,
    ChatSessionCreate,
    ChatSessionRead,
)
from app.api.v1.reports import to_layered_report
from app.schemas.report import LayeredReport
from app.services.callback import notify_callback

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_REPORT_CACHE_TTL_SECONDS = 600  # 10 min - long enough to absorb a demo re-running the same query
_IDEMPOTENCY_TTL_SECONDS = 60 * 60 * 24  # 24h - long enough to cover client retry windows


def _report_cache_key(user_id: UUID, query: str) -> str:
    normalized = " ".join(query.strip().lower().split())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"report_cache:{user_id}:{digest}"


@router.post("/sessions", response_model=ChatSessionRead, status_code=201)
async def create_session(
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatSession:
    session = ChatSession(user_id=current_user.id, title=payload.title or "New Investigation")
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[ChatSessionRead])
async def list_sessions(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ChatSession]:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    return list(result.scalars().all())


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageRead])
async def get_messages(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessage]:
    session = await _get_owned_session(db, session_id, current_user.id)
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
    )
    return list(result.scalars().all())


@router.post("/query")
async def query(
    payload: ChatQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    orchestrator: Orchestrator = Depends(get_orchestrator),
    memory_manager: MemoryManager = Depends(get_memory_manager),
) -> StreamingResponse:
    session = (
        await _get_owned_session(db, payload.session_id, current_user.id)
        if payload.session_id
        else await _create_default_session(db, current_user.id, payload.query)
    )

    user_message = ChatMessage(session_id=session.id, role="user", content=payload.query)
    db.add(user_message)
    await db.flush()

    memory_context = await memory_manager.recall_context(user_id=current_user.id)
    cache_key = _report_cache_key(current_user.id, payload.query)
    redis = get_redis()

    async def event_stream():
        report = None
        cache_hit = False
        try:
            cached_raw = await redis.get(cache_key)
            if cached_raw:
                cache_hit = True
                report = json.loads(cached_raw)
                # Replay the same agent_completed cadence a live run would emit
                # (from the cached trace) so the frontend's progress UI looks
                # identical either way - just near-instant instead of the full
                # pipeline latency.
                for entry in report.get("agent_trace", []):
                    payload_data = {
                        "type": "agent_completed",
                        "agent_name": entry.get("agent"),
                        "data": {"cached": True},
                    }
                    yield f"data: {json.dumps(payload_data)}\n\n"
                yield f"data: {json.dumps({'type': 'report_ready', 'agent_name': None, 'data': report})}\n\n"
            else:
                async for event in orchestrator.stream(
                    query=payload.query,
                    user_id=current_user.id,
                    session_id=session.id,
                    memory_context=memory_context,
                ):
                    if event.type == "report_ready":
                        report = event.data
                    yield f"data: {json.dumps({'type': event.type, 'agent_name': event.agent_name, 'data': event.data})}\n\n"
        except Exception as exc:  # noqa: BLE001 - last line of defense before the ASGI connection
            logger.error("chat_query_stream_failed", error=str(exc), exc_info=True)
            error_payload = {
                "type": "error",
                "agent_name": None,
                "data": {"message": "Something went wrong while investigating this query. Please try again."},
            }
            yield f"data: {json.dumps(error_payload)}\n\n"
            return

        if report and not cache_hit:
            await redis.set(cache_key, json.dumps(report), ex=_REPORT_CACHE_TTL_SECONDS)

        if report:
            await _persist_report(db, session.id, report)
            await db.commit()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def _persist_report(db: AsyncSession, session_id: UUID, report: dict[str, Any]) -> Report:
    """Shared by the human SSE stream and the agent background task: saves
    the orchestrator's report dict as a Report row plus its paired assistant
    ChatMessage. Caller commits - this only flushes, so the human path can
    still bundle it into one transaction with its cache write."""
    report_row = Report(
        session_id=session_id,
        query=report["query"],
        verdict=report["verdict"],
        executive_summary=report["executive_summary"],
        confidence_score=report["confidence"]["overall"],
        confidence_breakdown=report["confidence"],
        evidence=report["evidence"],
        counter_arguments=report["counter_arguments"],
        deep_dive=report["deep_dive"],
        references=report["references"],
        agent_trace=report["agent_trace"],
        entity_ambiguity=report.get("entity_ambiguity"),
    )
    db.add(report_row)
    await db.flush()

    assistant_message = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=report.get("executive_summary", ""),
        meta={"report_id": str(report_row.id)},
    )
    db.add(assistant_message)
    return report_row


@router.post("/agent/query", response_model=ChatSessionRead, status_code=201)
async def create_agent_query(
    payload: AgentChatQueryCreate,
    background_tasks: BackgroundTasks,
    api_key: ApiKey = Depends(get_agent_api_key),
    db: AsyncSession = Depends(get_db),
) -> ChatSession:
    """Agent-callable Verified Answers query (A2A) - the Chatbot service's
    counterpart to Court's POST /disputes/agent. Runs the full research
    pipeline in the background and returns the session immediately; the
    caller polls GET /chat/agent/sessions/{id}/report with the same key, or
    supplies callback_url to be notified instead."""
    redis = get_redis()
    idempotency_cache_key = (
        f"idempotency:chat:{api_key.wallet_id}:{payload.idempotency_key}"
        if payload.idempotency_key
        else None
    )

    if idempotency_cache_key:
        existing_id = await redis.get(idempotency_cache_key)
        if existing_id:
            existing = await db.get(ChatSession, UUID(existing_id))
            if existing is not None:
                return existing

    session = ChatSession(user_id=api_key.created_by_user_id, title=payload.query[:80])
    db.add(session)
    await db.flush()

    user_message = ChatMessage(session_id=session.id, role="user", content=payload.query)
    db.add(user_message)
    await db.commit()
    await db.refresh(session)

    if idempotency_cache_key:
        await redis.set(idempotency_cache_key, str(session.id), ex=_IDEMPOTENCY_TTL_SECONDS)

    background_tasks.add_task(
        _run_agent_query_and_notify, session.id, payload.query, api_key.created_by_user_id, payload.callback_url
    )
    return session


@router.get("/agent/sessions/{session_id}/report", response_model=LayeredReport)
async def get_agent_report(
    session_id: UUID,
    api_key: ApiKey = Depends(get_agent_api_key),
    db: AsyncSession = Depends(get_db),
) -> LayeredReport:
    session = await db.get(ChatSession, session_id)
    if session is None or session.user_id != api_key.created_by_user_id:
        raise NotFoundError("Chat session not found")

    result = await db.execute(
        select(Report).where(Report.session_id == session_id).order_by(Report.created_at.desc())
    )
    report = result.scalars().first()
    if report is None:
        raise NotFoundError("Report not yet available")
    return to_layered_report(report)


async def _get_owned_session(db: AsyncSession, session_id: UUID, user_id: UUID) -> ChatSession:
    session = await db.get(ChatSession, session_id)
    if session is None or session.user_id != user_id:
        raise NotFoundError("Chat session not found")
    return session


async def _create_default_session(db: AsyncSession, user_id: UUID, query: str) -> ChatSession:
    session = ChatSession(user_id=user_id, title=query[:80])
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def _run_agent_query_and_notify(
    session_id: UUID, query: str, user_id: UUID, callback_url: str | None
) -> None:
    """Runs on FastAPI's BackgroundTasks executor, strictly after the
    triggering request's response has been sent - it must not touch that
    request's (by-then-closed) DB session, so it opens its own via the same
    session factory `get_db_session` uses (same pattern as Court's
    _run_arbitration_and_notify)."""
    session_factory = get_session_factory()
    async with session_factory() as db:
        try:
            memory_manager = MemoryManager(EpisodicMemoryStore(db), ProjectMemoryStore(db))
            memory_context = await memory_manager.recall_context(user_id=user_id)
            orchestrator = Orchestrator(
                get_llm_router(),
                get_hybrid_retriever(),
                get_knowledge_graph(),
                memory_manager,
                get_market_data_service(),
            )

            report_data: dict[str, Any] | None = None
            async for event in orchestrator.stream(
                query=query, user_id=user_id, session_id=session_id, memory_context=memory_context
            ):
                if event.type == "report_ready":
                    report_data = event.data

            if report_data is None:
                return

            report_row = await _persist_report(db, session_id, report_data)
            await db.commit()
            await db.refresh(report_row)

            if callback_url:
                await notify_callback(callback_url, to_layered_report(report_row).model_dump(mode="json"))
        except Exception as exc:  # noqa: BLE001 - background task, nothing above can catch this
            logger.error("agent_chat_background_failed", session_id=str(session_id), error=str(exc), exc_info=True)
