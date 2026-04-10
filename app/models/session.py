from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.utils import utcnow


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    therapist_id: Mapped[int] = mapped_column(ForeignKey("therapists.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    pre_session_mood: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    post_session_mood: Mapped[Optional[str]] = mapped_column(String(30), default=None)
    session_notes: Mapped[str] = mapped_column(Text, default="")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    ml_state: Mapped[dict] = mapped_column(JSON, default=dict)

    patient: Mapped["Patient"] = relationship(back_populates="sessions")
    therapist: Mapped["Therapist"] = relationship(back_populates="sessions")
    activities: Mapped[list["GameActivity"]] = relationship(back_populates="session")
    game_events: Mapped[list["GameEvent"]] = relationship(back_populates="session")
    body_motion: Mapped[list["BodyMotion"]] = relationship(back_populates="session")
    head_gaze: Mapped[list["HeadGazeData"]] = relationship(back_populates="session")
    ml_results: Mapped[list["MLResult"]] = relationship(back_populates="session")
    baseline_data: Mapped[list["BaselineData"]] = relationship(back_populates="session")
    doctor_commands: Mapped[list["DoctorCommand"]] = relationship(back_populates="session")
    doctor_notes: Mapped[list["DoctorNote"]] = relationship(back_populates="session")
    ai_reports: Mapped[list["AIReport"]] = relationship(back_populates="session")
    learning_styles: Mapped[list["LearningStyleData"]] = relationship(back_populates="session")
