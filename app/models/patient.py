from __future__ import annotations

import secrets
import string
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.utils import utcnow

if TYPE_CHECKING:
    from app.models.auth import Therapist
    from app.models.session import Session
    from app.models.system import ConsentHistory, LearningStyleData


def generate_access_key() -> str:
    chars = string.ascii_uppercase + string.digits
    return f"YM-{''.join(secrets.choice(chars) for _ in range(8))}"


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    age: Mapped[int] = mapped_column()
    gender: Mapped[Optional[str]] = mapped_column(String(10), default=None)
    diagnosis: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    access_key: Mapped[str] = mapped_column(String(15), unique=True, index=True, default=generate_access_key)
    sensory_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, default="")
    therapist_id: Mapped[int] = mapped_column(ForeignKey("therapists.id"))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    therapist: Mapped[Therapist] = relationship(back_populates="patients")
    sessions: Mapped[list[Session]] = relationship(back_populates="patient")
    consent_history: Mapped[list[ConsentHistory]] = relationship(back_populates="patient")
    learning_styles: Mapped[list[LearningStyleData]] = relationship(back_populates="patient")
