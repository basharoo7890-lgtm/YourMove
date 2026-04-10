from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Therapist
from app.schemas import LoginRequest, RegisterRequest, TherapistOut, TokenResponse, TherapistUpdateRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TherapistOut, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.register(req)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return TokenResponse(access_token=await service.login(req))


@router.get("/me", response_model=TherapistOut)
async def me(current_user: Therapist = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=TherapistOut)
async def update_me(
    req: TherapistUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Therapist = Depends(get_current_user),
):
    service = AuthService(db)
    return await service.update_profile(current_user.id, req)
