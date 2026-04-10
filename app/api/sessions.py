from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rate_limit import rate_limit_session_start
from app.models import Therapist
from app.schemas import SessionStartRequest, SessionStartResponse, SessionOut
from app.services.session_service import SessionService
from app.repositories import TelemetryRepository
from app.services.final_report_service import FinalReportService
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("/start", response_model=SessionStartResponse, dependencies=[Depends(rate_limit_session_start)])
async def start_session(
    req: SessionStartRequest,
    db: AsyncSession = Depends(get_db),
    user: Therapist = Depends(get_current_user),
):
    return await SessionService(db).start_session(req.access_key, user.id)


@router.get("/", response_model=List[SessionOut])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user: Therapist = Depends(get_current_user),
):
    return await SessionService(db).list_sessions(user.id)


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: Therapist = Depends(get_current_user),
):
    return await SessionService(db).get_session(session_id, user.id)


@router.get("/{session_id}/recommendations")
async def get_session_recommendations(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: Therapist = Depends(get_current_user),
):
    await SessionService(db).get_session(session_id, user.id)
    repo = TelemetryRepository(db)
    return await RecommendationService(repo).build_end_session_recommendation(session_id)


@router.post("/{session_id}/report")
async def generate_session_report(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: Therapist = Depends(get_current_user),
):
    await SessionService(db).get_session(session_id, user.id)
    service = FinalReportService(TelemetryRepository(db))
    return await service.generate(session_id)


@router.get("/{session_id}/report")
async def get_session_report(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: Therapist = Depends(get_current_user),
):
    await SessionService(db).get_session(session_id, user.id)
    service = FinalReportService(TelemetryRepository(db))
    report = await service.get_latest(session_id)
    if not report:
        return {"detail": "No report generated yet"}
    return report
