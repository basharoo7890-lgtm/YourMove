from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models import Therapist
from app.repositories import AuthRepository
from app.schemas import LoginRequest, RegisterRequest, TherapistUpdateRequest


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = AuthRepository(db)

    async def register(self, req: RegisterRequest) -> Therapist:
        existing = await self.repo.get_by_email(req.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        therapist = Therapist(
            full_name=req.full_name,
            email=req.email,
            hashed_password=hash_password(req.password),
            role=req.role,
        )
        return await self.repo.create(therapist)

    async def login(self, req: LoginRequest) -> str:
        user = await self.repo.get_by_email(req.email)
        if not user or not verify_password(req.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return create_access_token({"sub": str(user.id)})

    async def update_profile(self, user_id: int, req: TherapistUpdateRequest) -> Therapist:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        payload = req.model_dump(exclude_unset=True)
        if "email" in payload and payload["email"] != user.email:
            existing = await self.repo.get_by_email(payload["email"])
            if existing and existing.id != user.id:
                raise HTTPException(status_code=400, detail="Email already registered")

        for field, value in payload.items():
            setattr(user, field, value)

        return await self.repo.save(user)
