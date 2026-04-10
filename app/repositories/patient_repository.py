from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Patient


class PatientRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, patient: Patient) -> Patient:
        self.db.add(patient)
        await self.db.commit()
        await self.db.refresh(patient)
        return patient

    async def list_active_by_therapist(self, therapist_id: int) -> list[Patient]:
        result = await self.db.execute(
            select(Patient).where(Patient.therapist_id == therapist_id, Patient.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def get_by_id_for_therapist(self, patient_id: int, therapist_id: int) -> Patient | None:
        result = await self.db.execute(
            select(Patient).where(Patient.id == patient_id, Patient.therapist_id == therapist_id)
        )
        return result.scalar_one_or_none()

    async def get_by_access_key_for_therapist(self, access_key: str, therapist_id: int) -> Patient | None:
        result = await self.db.execute(
            select(Patient).where(
                Patient.access_key == access_key,
                Patient.therapist_id == therapist_id,
                Patient.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def save(self, patient: Patient) -> Patient:
        await self.db.commit()
        await self.db.refresh(patient)
        return patient
