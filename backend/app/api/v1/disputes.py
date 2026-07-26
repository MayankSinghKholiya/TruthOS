"""TruthOS Court: dispute filing, AI arbitration, and agent reputation."""
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_agent_api_key,
    get_arbitration_orchestrator,
    get_chain_verification_service,
    get_current_user,
    get_db,
    get_llm_router,
    get_optional_checker_chat_id,
)
from app.core.container import get_http_client, get_redis
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.models.api_key import ApiKey
from app.db.models.dispute import AgentReputation, Dispute, DisputeEvidence, DisputeVerdict
from app.db.models.user import User
from app.db.session import get_session_factory
from app.graph.arbitration_orchestrator import ArbitrationOrchestrator
from app.schemas.dispute import (
    AgentDisputeCreate,
    ChainVerificationRead,
    DisputeCreate,
    DisputeHistoryEntry,
    DisputeRead,
    DisputeVerdictRead,
    EvidenceInput,
    ReputationRead,
)
from app.services.callback import notify_callback
from app.services.chain_verification import ChainVerificationService
from app.services.reputation import DEFAULT_TRUST_SCORE, standing_label
from app.services.telegram_bot import TelegramBotService
from app.services.telegram_notify import (
    _message,
    notify_dispute_filed,
    notify_flagged_counterparty,
    notify_interaction_with_flagged,
    wallet_history_summary,
)

logger = get_logger(__name__)

router = APIRouter(tags=["court"])

_IDEMPOTENCY_TTL_SECONDS = 60 * 60 * 24  # 24h - long enough to cover client retry windows


@router.post("/disputes", response_model=DisputeRead, status_code=201)
async def file_dispute(
    payload: DisputeCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chain_service: ChainVerificationService = Depends(get_chain_verification_service),
) -> Dispute:
    dispute = Dispute(
        filed_by_user_id=current_user.id,
        claimant_wallet_id=payload.claimant_wallet_id,
        respondent_wallet_id=payload.respondent_wallet_id,
        task_description=payload.task_description,
        agreed_deliverable=payload.agreed_deliverable,
        actual_deliverable=payload.actual_deliverable,
        escrow_amount=payload.escrow_amount,
        status="open",
    )
    db.add(dispute)
    await _attach_verified_evidence(dispute, payload.evidence, payload.escrow_amount, chain_service)
    await db.commit()
    background_tasks.add_task(_notify_dispute_filed_background, dispute.id)
    # commit() expires every attribute including the `evidence` relationship;
    # FastAPI's response serialization then touches it outside any
    # async-safe context (MissingGreenlet). db.get() with a loader option
    # doesn't reliably fix this - `dispute` is already in this session's
    # identity map, so get() can take that shortcut and skip the option
    # entirely. refresh(attribute_names=...) forces the actual reload.
    await db.refresh(dispute, attribute_names=["evidence"])
    return dispute


@router.post("/disputes/agent", response_model=DisputeRead, status_code=201)
async def create_agent_dispute(
    payload: AgentDisputeCreate,
    background_tasks: BackgroundTasks,
    api_key: ApiKey = Depends(get_agent_api_key),
    db: AsyncSession = Depends(get_db),
    chain_service: ChainVerificationService = Depends(get_chain_verification_service),
) -> Dispute:
    """Agent-callable dispute filing (A2A). Auth is an X-API-Key, not a human
    JWT - claimant_wallet_id is resolved from that key, never taken from the
    request body, so a caller can only ever file as the wallet it holds a key
    for. filed_by_user_id is still the key's human owner, so it shows up in
    that person's normal (JWT-authed) dispute list too. Arbitration starts
    automatically in the background; the caller polls GET /disputes/agent/{id}
    (or /verdict) with the same key, or supplies callback_url to be notified
    instead.

    Exception: a bridge key (api_key.is_bridge) is a trusted neutral relay -
    e.g. the OKX ASP marketplace integration - arbitrating disputes between
    two other wallets it isn't itself a party to, so for that key type alone
    payload.claimant_wallet_id (when supplied) wins over the key's own
    wallet_id. A non-bridge key can never override its own identity this
    way, regardless of what it puts in the payload."""
    claimant_wallet_id = _resolve_claimant_wallet_id(api_key, payload)
    redis = get_redis()
    idempotency_cache_key = (
        f"idempotency:dispute:{api_key.wallet_id}:{payload.idempotency_key}"
        if payload.idempotency_key
        else None
    )

    if idempotency_cache_key:
        existing_id = await redis.get(idempotency_cache_key)
        if existing_id:
            existing = await db.get(
                Dispute, UUID(existing_id), options=[selectinload(Dispute.evidence)]
            )
            if existing is not None:
                return existing

    dispute = Dispute(
        filed_by_user_id=api_key.created_by_user_id,
        claimant_wallet_id=claimant_wallet_id,
        respondent_wallet_id=payload.respondent_wallet_id,
        task_description=payload.task_description,
        agreed_deliverable=payload.agreed_deliverable,
        actual_deliverable=payload.actual_deliverable,
        escrow_amount=payload.escrow_amount,
        callback_url=payload.callback_url,
        status="open",
    )
    db.add(dispute)
    await _attach_verified_evidence(dispute, payload.evidence, payload.escrow_amount, chain_service)
    await db.commit()

    # Retry-safety, not a hard concurrency lock: two truly simultaneous
    # requests with the same idempotency key can both still create a dispute
    # (last SET wins the mapping). That's an acceptable bound for a client
    # retrying after a timeout, which is what this exists for.
    if idempotency_cache_key:
        await redis.set(idempotency_cache_key, str(dispute.id), ex=_IDEMPOTENCY_TTL_SECONDS)

    background_tasks.add_task(_notify_dispute_filed_background, dispute.id)
    background_tasks.add_task(_run_arbitration_and_notify, dispute.id)
    # Same MissingGreenlet concern as file_dispute() above.
    await db.refresh(dispute, attribute_names=["evidence"])
    return dispute


@router.get("/disputes/verify-tx", response_model=ChainVerificationRead)
async def verify_transaction(
    chain: str = Query(...),
    tx_hash: str = Query(...),
    claimed_amount: float | None = Query(default=None),
    chain_service: ChainVerificationService = Depends(get_chain_verification_service),
) -> ChainVerificationRead:
    """Standalone, no-auth on-chain lookup - lets anyone (human or agent)
    preview whether a transaction is genuine before submitting it as dispute
    evidence, using the same check the arbitration pipeline itself relies on."""
    verification_status, details = await chain_service.resolve_evidence(
        chain=chain, tx_hash_raw=tx_hash, claimed_amount=claimed_amount
    )
    return ChainVerificationRead(status=verification_status, **details)


@router.post("/disputes/{dispute_id}/arbitrate")
async def arbitrate_dispute(
    dispute_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    orchestrator: ArbitrationOrchestrator = Depends(get_arbitration_orchestrator),
) -> StreamingResponse:
    dispute = await _get_owned_dispute(db, dispute_id, current_user.id)
    evidence = await _load_evidence_dicts(db, dispute_id)

    async def event_stream():
        try:
            async for event in orchestrator.stream(
                dispute_id=dispute.id,
                task_description=dispute.task_description,
                agreed_deliverable=dispute.agreed_deliverable,
                actual_deliverable=dispute.actual_deliverable,
                claimant_wallet_id=dispute.claimant_wallet_id,
                respondent_wallet_id=dispute.respondent_wallet_id,
                evidence=evidence,
            ):
                payload = {"type": event.type, "agent_name": event.agent_name, "data": event.data}
                yield f"data: {json.dumps(payload)}\n\n"
            await _notify_after_verdict(db, dispute, evidence)
        except Exception as exc:  # noqa: BLE001 - last line of defense before the ASGI connection
            logger.error("arbitration_stream_failed", dispute_id=str(dispute_id), error=str(exc), exc_info=True)
            error_payload = {
                "type": "error",
                "agent_name": None,
                "data": {"message": "Something went wrong while arbitrating this dispute. Please try again."},
            }
            yield f"data: {json.dumps(error_payload)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/disputes", response_model=list[DisputeRead])
async def list_disputes(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Dispute]:
    result = await db.execute(
        select(Dispute)
        .options(selectinload(Dispute.evidence))
        .where(Dispute.filed_by_user_id == current_user.id)
        .order_by(Dispute.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/disputes/agent/{dispute_id}", response_model=DisputeRead)
async def get_agent_dispute(
    dispute_id: UUID,
    api_key: ApiKey = Depends(get_agent_api_key),
    db: AsyncSession = Depends(get_db),
) -> Dispute:
    return await _get_agent_dispute(db, dispute_id, api_key)


@router.get("/disputes/agent/{dispute_id}/verdict", response_model=DisputeVerdictRead)
async def get_agent_verdict(
    dispute_id: UUID,
    api_key: ApiKey = Depends(get_agent_api_key),
    db: AsyncSession = Depends(get_db),
) -> DisputeVerdict:
    await _get_agent_dispute(db, dispute_id, api_key)
    return await _load_verdict_or_404(db, dispute_id)


@router.get("/disputes/{dispute_id}", response_model=DisputeRead)
async def get_dispute(
    dispute_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dispute:
    return await _get_owned_dispute(db, dispute_id, current_user.id)


@router.get("/disputes/{dispute_id}/verdict", response_model=DisputeVerdictRead)
async def get_verdict(
    dispute_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DisputeVerdict:
    await _get_owned_dispute(db, dispute_id, current_user.id)
    return await _load_verdict_or_404(db, dispute_id)


@router.get("/reputation/{wallet_id}", response_model=ReputationRead)
async def get_reputation(
    wallet_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    checker_chat_id: str | None = Depends(get_optional_checker_chat_id),
) -> ReputationRead:
    """Public lookup (no auth required) - reputation is meant to be checkable
    by any counterparty, human or agent, before they transact with this
    wallet. If the caller happens to be identifiable (a logged-in human, or
    an agent's own API key) AND has Telegram linked, a Flagged result also
    gets pushed to them directly - useful when the "caller" is an agent
    with no screen to show a red-flag banner on."""
    result = await db.execute(
        select(AgentReputation).where(AgentReputation.wallet_id == wallet_id)
    )
    reputation = result.scalar_one_or_none()
    if reputation is None:
        reputation_read = ReputationRead(
            wallet_id=wallet_id,
            trust_score=DEFAULT_TRUST_SCORE,
            disputes_total=0,
            disputes_at_fault=0,
            avg_fault_percentage=0.0,
            completed_tasks=0,
            standing=standing_label(DEFAULT_TRUST_SCORE),
        )
    else:
        reputation_read = ReputationRead(
            wallet_id=reputation.wallet_id,
            trust_score=reputation.trust_score,
            disputes_total=reputation.disputes_total,
            disputes_at_fault=reputation.disputes_at_fault,
            avg_fault_percentage=reputation.avg_fault_percentage,
            completed_tasks=reputation.completed_tasks,
            standing=standing_label(reputation.trust_score),
        )

    if checker_chat_id and reputation_read.standing == "Flagged":
        background_tasks.add_task(_notify_checker_of_flagged_wallet, checker_chat_id, wallet_id)

    return reputation_read


@router.get("/reputation/{wallet_id}/history", response_model=list[DisputeHistoryEntry])
async def get_reputation_history(
    wallet_id: str, db: AsyncSession = Depends(get_db)
) -> list[DisputeHistoryEntry]:
    """Public (no auth) - the actual disputes behind a trust score, so a red
    flag is never just a bare number nobody can inspect."""
    result = await db.execute(
        select(Dispute)
        .where(or_(Dispute.claimant_wallet_id == wallet_id, Dispute.respondent_wallet_id == wallet_id))
        .order_by(Dispute.created_at.desc())
        .limit(10)
    )
    disputes = result.scalars().all()

    entries = []
    for dispute in disputes:
        role = "claimant" if dispute.claimant_wallet_id == wallet_id else "respondent"
        verdict_result = await db.execute(
            select(DisputeVerdict).where(DisputeVerdict.dispute_id == dispute.id)
        )
        verdict = verdict_result.scalar_one_or_none()
        fault_percentage = None
        if verdict is not None:
            fault_percentage = (
                verdict.claimant_fault_percentage
                if role == "claimant"
                else verdict.respondent_fault_percentage
            )
        entries.append(
            DisputeHistoryEntry(
                dispute_id=dispute.id,
                role=role,
                task_description=dispute.task_description,
                status=dispute.status,
                verdict=verdict.verdict if verdict is not None else None,
                fault_percentage=fault_percentage,
                created_at=dispute.created_at,
            )
        )
    return entries


# ---- helpers ----------------------------------------------------------------


def _resolve_claimant_wallet_id(api_key: ApiKey, payload: AgentDisputeCreate) -> str:
    """A regular agent key can only ever file as the wallet it holds a key
    for - claimant_wallet_id is always forced to api_key.wallet_id, ignoring
    anything the payload supplies. A bridge key (api_key.is_bridge) is a
    trusted neutral relay that arbitrates disputes between two OTHER
    wallets, so its explicit payload.claimant_wallet_id wins when given -
    falling back to the bridge's own wallet_id only if it left the field
    unset."""
    if api_key.is_bridge and payload.claimant_wallet_id:
        return payload.claimant_wallet_id
    return api_key.wallet_id


async def _attach_verified_evidence(
    dispute: Dispute,
    evidence_inputs: list[EvidenceInput],
    escrow_amount: float | None,
    chain_service: ChainVerificationService,
) -> None:
    """Runs the on-chain check for every tx_reference item at submission
    time (once, synchronously - the filer sees the result immediately) and
    attaches all evidence rows to `dispute` via the relationship so they're
    visible on the same in-memory object without a second DB round-trip
    (the session's expire_on_commit=False keeps this populated post-commit)."""
    for item in evidence_inputs:
        verification_status: str | None = None
        verification_details: dict[str, Any] | None = None
        if item.evidence_type == "tx_reference":
            verification_status, verification_details = await chain_service.resolve_evidence(
                chain=item.chain, tx_hash_raw=item.content, claimed_amount=escrow_amount
            )
        dispute.evidence.append(
            DisputeEvidence(
                submitted_by=item.submitted_by,
                evidence_type=item.evidence_type,
                content=item.content,
                url=item.url,
                chain=item.chain,
                verification_status=verification_status,
                verification_details=verification_details,
            )
        )


async def _load_evidence_dicts(db: AsyncSession, dispute_id: UUID) -> list[dict[str, Any]]:
    result = await db.execute(select(DisputeEvidence).where(DisputeEvidence.dispute_id == dispute_id))
    return [
        {
            "submitted_by": e.submitted_by,
            "evidence_type": e.evidence_type,
            "content": e.content,
            "chain": e.chain,
            "verification_status": e.verification_status,
            "verification_details": e.verification_details,
        }
        for e in result.scalars().all()
    ]


async def _load_verdict_or_404(db: AsyncSession, dispute_id: UUID) -> DisputeVerdict:
    result = await db.execute(select(DisputeVerdict).where(DisputeVerdict.dispute_id == dispute_id))
    verdict = result.scalar_one_or_none()
    if verdict is None:
        raise NotFoundError("Verdict not yet available")
    return verdict


async def _get_owned_dispute(db: AsyncSession, dispute_id: UUID, user_id: UUID) -> Dispute:
    dispute = await db.get(Dispute, dispute_id, options=[selectinload(Dispute.evidence)])
    if dispute is None or dispute.filed_by_user_id != user_id:
        raise NotFoundError("Dispute not found")
    return dispute


async def _get_wallet_dispute(db: AsyncSession, dispute_id: UUID, wallet_id: str) -> Dispute:
    dispute = await db.get(Dispute, dispute_id, options=[selectinload(Dispute.evidence)])
    if dispute is None or wallet_id not in (dispute.claimant_wallet_id, dispute.respondent_wallet_id):
        raise NotFoundError("Dispute not found")
    return dispute


async def _get_agent_dispute(db: AsyncSession, dispute_id: UUID, api_key: ApiKey) -> Dispute:
    """Polling-scope check for the agent GET routes. A regular key must be a
    named party (claimant or respondent) on the dispute. A bridge key never
    is - it filed the dispute on behalf of two other wallets - so it's
    scoped by filer identity instead: any dispute created through its own
    POST /disputes/agent call (filed_by_user_id == the bridge key's human
    owner)."""
    if api_key.is_bridge:
        dispute = await db.get(Dispute, dispute_id, options=[selectinload(Dispute.evidence)])
        if dispute is None or dispute.filed_by_user_id != api_key.created_by_user_id:
            raise NotFoundError("Dispute not found")
        return dispute
    return await _get_wallet_dispute(db, dispute_id, api_key.wallet_id)


async def _notify_dispute_filed_background(dispute_id: UUID) -> None:
    """Both checks here fire at filing time, before arbitration even starts:
    notify_dispute_filed covers explicit watchers of the respondent wallet;
    notify_interaction_with_flagged covers the "you didn't even check"
    case - if either party is *already* Flagged from past disputes, the
    other party's owner gets warned immediately, resolved via watch OR via
    owning the API key that wallet filed with (see _owners_for_wallet)."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            dispute = await session.get(Dispute, dispute_id)
            if dispute is not None:
                evidence = await _load_evidence_dicts(session, dispute_id)
                bot = TelegramBotService(get_http_client())
                await notify_dispute_filed(session, bot, dispute, evidence)
                await notify_interaction_with_flagged(session, bot, dispute, evidence)
        except Exception as exc:  # noqa: BLE001 - background task, nothing above can catch this
            logger.error("telegram_dispute_filed_notify_failed", dispute_id=str(dispute_id), error=str(exc))


async def _notify_checker_of_flagged_wallet(chat_id: str, wallet_id: str) -> None:
    """Runs as its own background task with a fresh session (not the
    request's, which may already be closed) so the history summary reflects
    the live database, not a stale snapshot from the reputation lookup."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            history = await wallet_history_summary(session, wallet_id)
            rep_result = await session.execute(select(AgentReputation).where(AgentReputation.wallet_id == wallet_id))
            reputation = rep_result.scalar_one_or_none()
            trust_score = reputation.trust_score if reputation else DEFAULT_TRUST_SCORE

            bot = TelegramBotService(get_http_client())
            message = _message(
                emoji="\U0001f50d",
                headline="Safety Check Result: Flagged",
                intro="A wallet you just checked came back Flagged.",
                when=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                fields=[
                    ("\U0001f45b Wallet", f"<code>{wallet_id}</code>"),
                    ("\U0001f4ca History", f"{history} (trust score {trust_score:.0f}/100)"),
                ],
            )
            await bot.send_message(chat_id, message)
        except Exception as exc:  # noqa: BLE001 - background task, nothing above can catch this
            logger.error("telegram_checker_notify_failed", wallet_id=wallet_id, error=str(exc))


async def _notify_after_verdict(session: AsyncSession, dispute: Dispute, evidence: list[dict[str, Any]]) -> None:
    """Shared by both arbitration paths (agent background task and the
    human SSE stream) - checks whether either party's reputation just
    crossed into "Flagged" and, if so, alerts anyone watching the other
    wallet in the dispute."""
    verdict_result = await session.execute(select(DisputeVerdict).where(DisputeVerdict.dispute_id == dispute.id))
    verdict = verdict_result.scalar_one_or_none()
    if verdict is None:
        return

    rep_result = await session.execute(
        select(AgentReputation).where(
            AgentReputation.wallet_id.in_([dispute.claimant_wallet_id, dispute.respondent_wallet_id])
        )
    )
    scores = {rep.wallet_id: rep.trust_score for rep in rep_result.scalars().all()}
    claimant_score = scores.get(dispute.claimant_wallet_id, DEFAULT_TRUST_SCORE)
    respondent_score = scores.get(dispute.respondent_wallet_id, DEFAULT_TRUST_SCORE)

    await notify_flagged_counterparty(
        session,
        TelegramBotService(get_http_client()),
        dispute,
        verdict,
        evidence,
        claimant_trust_score=claimant_score,
        respondent_trust_score=respondent_score,
    )


async def _run_arbitration_and_notify(dispute_id: UUID) -> None:
    """Runs on FastAPI's BackgroundTasks executor, i.e. strictly after the
    triggering request's response has been sent - it must not touch that
    request's (by-then-closed) DB session, so it opens its own via the same
    session factory `get_db_session` uses."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            dispute = await session.get(Dispute, dispute_id)
            if dispute is None:
                return
            evidence = await _load_evidence_dicts(session, dispute_id)
            orchestrator = ArbitrationOrchestrator(get_llm_router(), session)
            verdict = await orchestrator.run(
                dispute_id=dispute.id,
                task_description=dispute.task_description,
                agreed_deliverable=dispute.agreed_deliverable,
                actual_deliverable=dispute.actual_deliverable,
                claimant_wallet_id=dispute.claimant_wallet_id,
                respondent_wallet_id=dispute.respondent_wallet_id,
                evidence=evidence,
            )
            if dispute.callback_url:
                await notify_callback(dispute.callback_url, verdict.model_dump(mode="json"))
            await _notify_after_verdict(session, dispute, evidence)
        except Exception as exc:  # noqa: BLE001 - background task, nothing above can catch this
            logger.error("background_arbitration_failed", dispute_id=str(dispute_id), error=str(exc), exc_info=True)
