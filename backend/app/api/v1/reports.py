from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.exceptions import NotFoundError
from app.db.models.report import Report
from app.db.models.session_model import ChatSession
from app.db.models.user import User
from app.schemas.report import ConfidenceBreakdown, LayeredReport

router = APIRouter(prefix="/reports", tags=["reports"])


def to_layered_report(report: Report) -> LayeredReport:
    return LayeredReport(
        id=report.id,
        query=report.query,
        verdict=report.verdict,
        executive_summary=report.executive_summary,
        confidence=ConfidenceBreakdown(**report.confidence_breakdown),
        evidence=report.evidence,
        counter_arguments=report.counter_arguments,
        deep_dive=report.deep_dive,
        references=report.references,
        agent_trace=report.agent_trace,
        entity_ambiguity=report.entity_ambiguity,
        created_at=report.created_at,
    )


@router.get("/{report_id}", response_model=LayeredReport)
async def get_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LayeredReport:
    report = await db.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report not found")

    session = await db.get(ChatSession, report.session_id)
    if session is None or session.user_id != current_user.id:
        raise NotFoundError("Report not found")

    return to_layered_report(report)


@router.get("/by-session/{session_id}", response_model=list[LayeredReport])
async def list_reports_for_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LayeredReport]:
    session = await db.get(ChatSession, session_id)
    if session is None or session.user_id != current_user.id:
        raise NotFoundError("Chat session not found")

    result = await db.execute(
        select(Report).where(Report.session_id == session_id).order_by(Report.created_at)
    )
    return [to_layered_report(r) for r in result.scalars().all()]
