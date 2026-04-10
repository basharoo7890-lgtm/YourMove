from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Therapist
from app.schemas import PatientCreate, PatientUpdate, PatientOut
from app.services.patient_service import PatientService

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.post("/", response_model=PatientOut, status_code=201)
async def create_patient(
    req: PatientCreate,
    db: AsyncSession = Depends(get_db),
    user: Therapist = Depends(get_current_user),
):
    return await PatientService(db).create_patient(req, user.id)


@router.get("/", response_model=List[PatientOut])
async def list_patients(
    db: AsyncSession = Depends(get_db),
    user: Therapist = Depends(get_current_user),
):
    return await PatientService(db).list_patients(user.id)


@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    user: Therapist = Depends(get_current_user),
):
    return await PatientService(db).get_patient(patient_id, user.id)


@router.put("/{patient_id}", response_model=PatientOut)
async def update_patient(
    patient_id: int,
    req: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    user: Therapist = Depends(get_current_user),
):
    return await PatientService(db).update_patient(patient_id, user.id, req)


@router.delete("/{patient_id}")
async def delete_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    user: Therapist = Depends(get_current_user),
):
    await PatientService(db).deactivate_patient(patient_id, user.id)
    return {"detail": "Patient deactivated"}
