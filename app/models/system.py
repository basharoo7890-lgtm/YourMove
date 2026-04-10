from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.utils import utcnow


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(default=None)
    action: Mapped[str] = mapped_column(String(50))
    resource: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    resource_id: Mapped[Optional[int]] = mapped_column(default=None)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ConsentHistory(Base):
    __tablename__ = "consent_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    consent_type: Mapped[str] = mapped_column(String(50))
    granted: Mapped[bool] = mapped_column(default=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    notes: Mapped[str] = mapped_column(Text, default="")

    patient: Mapped["Patient"] = relationship(back_populates="consent_history")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    model_name: Mapped[str] = mapped_column(String(50))
    version: Mapped[str] = mapped_column(String(20))
    file_path: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    accuracy: Mapped[Optional[float]] = mapped_column(Float, default=None)
    trained_on_sessions: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LearningStyleData(Base):
    __tablename__ = "learning_style_data"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    visual_score: Mapped[float] = mapped_column(Float, default=0.0)
    auditory_score: Mapped[float] = mapped_column(Float, default=0.0)
    classification: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    patient: Mapped["Patient"] = relationship(back_populates="learning_styles")
    session: Mapped["Session"] = relationship(back_populates="learning_styles")
