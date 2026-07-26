"""Chat endpoints: session management plus the streaming query endpoint that
drives the full Planner -> Courtroom -> Judge -> Writer pipeline and streams
per-agent progress events over SSE."""
import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_memory_manager, get_orchestrator
from app.core.container import get_redis
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.models.report import Report
from app.db.models.session_model import ChatMessage, ChatSession
from app.db.models.user import User
from app.graph.orchestrator import Orchestrator
from app.memory.manager import MemoryManager
from app.schemas.chat import (
    ChatMessageRead,
    ChatQueryRequest,
    ChatSessionCreate,
    ChatSessionRead,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_REPORT_CACHE_TTL_SECONDS = 600  # 10 min - long enough to absorb a demo re-running the same query


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

    memory_context = await memory_manager.recall_context(
        user_id=current_user.id, query=payload.query
    )
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
            report_row = Report(
                session_id=session.id,
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
                session_id=session.id,
                role="assistant",
                content=report.get("executive_summary", ""),
                meta={"report_id": str(report_row.id)},
            )
            db.add(assistant_message)
            await db.commit()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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
