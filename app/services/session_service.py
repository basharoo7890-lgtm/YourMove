from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Session
from app.repositories import PatientRepository, SessionRepository
from app.schemas import SessionStartResponse


class SessionService:
    def __init__(self, db: AsyncSession):
        self.patient_repo = PatientRepository(db)
        self.session_repo = SessionRepository(db)

    async def start_session(self, access_key: str, therapist_id: int) -> SessionStartResponse:
        patient = await self.patient_repo.get_by_access_key_for_therapist(access_key, therapist_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Invalid access key or unauthorized")

        session = Session(
            patient_id=patient.id,
            therapist_id=therapist_id,
            status="pending",
            config={"brightness": 60, "volume": 50, "difficulty": 1},
        )
        session = await self.session_repo.create(session)
        return SessionStartResponse(
            session_id=session.id,
            patient_name=patient.full_name,
            sensory_profile=patient.sensory_profile or {},
            baseline_duration_seconds=120,
        )

    async def list_sessions(self, therapist_id: int) -> list[Session]:
        return await self.session_repo.list_by_therapist(therapist_id)

    async def get_session(self, session_id: int, therapist_id: int) -> Session:
        session = await self.session_repo.get_by_id_for_therapist(session_id, therapist_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
