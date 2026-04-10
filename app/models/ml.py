from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.utils import utcnow

if TYPE_CHECKING:
    from app.models.session import Session


class MLResult(Base):
    __tablename__ = "ml_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    layer: Mapped[str] = mapped_column(String(20))
    prediction: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    confidence: Mapped[Optional[float]] = mapped_column(Float, default=None)
    features: Mapped[dict] = mapped_column(JSON, default=dict)
    feature_importance: Mapped[dict] = mapped_column(JSON, default=dict)

    session: Mapped[Session] = relationship(back_populates="ml_results")


class AIReport(Base):
    __tablename__ = "ai_reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    report_text: Mapped[str] = mapped_column(Text)
    report_json: Mapped[dict] = mapped_column(JSON, default=dict)
    model_used: Mapped[Optional[str]] = mapped_column(String(50), default=None)
    anonymized: Mapped[bool] = mapped_column(default=True)

    session: Mapped[Session] = relationship(back_populates="ai_reports")


class BaselineData(Base):
    __tablename__ = "baseline_data"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    duration_seconds: Mapped[int] = mapped_column(default=120)
    avg_movement_index: Mapped[Optional[float]] = mapped_column(Float, default=None)
    avg_reaction_time_ms: Mapped[Optional[float]] = mapped_column(Float, default=None)
    avg_head_stability: Mapped[Optional[float]] = mapped_column(Float, default=None)
    computed_thresholds: Mapped[dict] = mapped_column(JSON, default=dict)

    session: Mapped[Session] = relationship(back_populates="baseline_data")


class DoctorCommand(Base):
    __tablename__ = "doctor_commands"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    command: Mapped[str] = mapped_column(String(30))
    value: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    session: Mapped[Session] = relationship(back_populates="doctor_commands")


class DoctorNote(Base):
    __tablename__ = "doctor_notes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    note_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    session: Mapped[Session] = relationship(back_populates="doctor_notes")
