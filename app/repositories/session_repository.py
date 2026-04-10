from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Session


class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, session: Session) -> Session:
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def list_by_therapist(self, therapist_id: int) -> list[Session]:
        result = await self.db.execute(
            select(Session).where(Session.therapist_id == therapist_id).order_by(Session.started_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id_for_therapist(self, session_id: int, therapist_id: int) -> Session | None:
        result = await self.db.execute(
            select(Session).where(Session.id == session_id, Session.therapist_id == therapist_id)
        )
        return result.scalar_one_or_none()

    async def save(self, session: Session) -> Session:
        await self.db.commit()
        await self.db.refresh(session)
        return session
