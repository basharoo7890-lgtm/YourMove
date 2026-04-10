from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Patient
from app.repositories import PatientRepository
from app.schemas import PatientCreate, PatientUpdate


class PatientService:
    def __init__(self, db: AsyncSession):
        self.repo = PatientRepository(db)

    async def create_patient(self, req: PatientCreate, therapist_id: int) -> Patient:
        patient = Patient(**req.model_dump(), therapist_id=therapist_id)
        return await self.repo.create(patient)

    async def list_patients(self, therapist_id: int) -> list[Patient]:
        return await self.repo.list_active_by_therapist(therapist_id)

    async def get_patient(self, patient_id: int, therapist_id: int) -> Patient:
        patient = await self.repo.get_by_id_for_therapist(patient_id, therapist_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        return patient

    async def update_patient(self, patient_id: int, therapist_id: int, req: PatientUpdate) -> Patient:
        patient = await self.get_patient(patient_id, therapist_id)
        for field, value in req.model_dump(exclude_unset=True).items():
            setattr(patient, field, value)
        return await self.repo.save(patient)

    async def deactivate_patient(self, patient_id: int, therapist_id: int) -> None:
        patient = await self.get_patient(patient_id, therapist_id)
        patient.is_active = False
        await self.repo.save(patient)
