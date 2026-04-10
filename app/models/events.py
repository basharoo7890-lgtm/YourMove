from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.utils import utcnow

if TYPE_CHECKING:
    from app.models.session import Session


class GameActivity(Base):
    __tablename__ = "game_activities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    activity_type: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    difficulty_level: Mapped[int] = mapped_column(default=1)
    is_baseline: Mapped[bool] = mapped_column(default=False)
    total_correct: Mapped[int] = mapped_column(default=0)
    total_wrong: Mapped[int] = mapped_column(default=0)
    total_omissions: Mapped[int] = mapped_column(default=0)
    avg_reaction_time_ms: Mapped[Optional[float]] = mapped_column(Float, default=None)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)

    session: Mapped[Session] = relationship(back_populates="activities")


class GameEvent(Base):
    __tablename__ = "game_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    activity_type: Mapped[str] = mapped_column(String(30))
    event_type: Mapped[str] = mapped_column(String(30))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    reaction_time_ms: Mapped[Optional[float]] = mapped_column(Float, default=None)
    is_correct: Mapped[Optional[bool]] = mapped_column(default=None)
    round_number: Mapped[Optional[int]] = mapped_column(default=None)
    difficulty_level: Mapped[Optional[int]] = mapped_column(default=None)
    is_baseline: Mapped[bool] = mapped_column(default=False)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)

    session: Mapped[Session] = relationship(back_populates="game_events")


class BodyMotion(Base):
    __tablename__ = "body_motion"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    trackers: Mapped[dict] = mapped_column(JSON)
    total_movement_index: Mapped[Optional[float]] = mapped_column(Float, default=None)
    tracker_confidence: Mapped[Optional[float]] = mapped_column(Float, default=None)
    is_baseline: Mapped[bool] = mapped_column(default=False)

    session: Mapped[Session] = relationship(back_populates="body_motion")


class HeadGazeData(Base):
    __tablename__ = "head_gaze_data"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    hmd_rotation: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    hmd_position: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    is_looking_at_target: Mapped[Optional[bool]] = mapped_column(default=None)
    angle_to_target: Mapped[Optional[float]] = mapped_column(Float, default=None)
    is_baseline: Mapped[bool] = mapped_column(default=False)

    session: Mapped[Session] = relationship(back_populates="head_gaze")
