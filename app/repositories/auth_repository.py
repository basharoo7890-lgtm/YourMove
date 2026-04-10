from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Therapist


class AuthRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> Therapist | None:
        result = await self.db.execute(select(Therapist).where(Therapist.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, therapist_id: int) -> Therapist | None:
        result = await self.db.execute(select(Therapist).where(Therapist.id == therapist_id))
        return result.scalar_one_or_none()

    async def create(self, therapist: Therapist) -> Therapist:
        self.db.add(therapist)
        await self.db.commit()
        await self.db.refresh(therapist)
        return therapist

    async def save(self, therapist: Therapist) -> Therapist:
        await self.db.commit()
        await self.db.refresh(therapist)
        return therapist
