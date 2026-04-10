"""
Data Ingestion Service
- Parses incoming validated data from UE5 WebSocket
- Saves to appropriate DB tables
- Returns parsed data for ML processing and dashboard relay
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import (
    Session, GameActivity, GameEvent, BodyMotion,
    HeadGazeData, BaselineData
)
from app.core.utils import utcnow
from app.schemas import (
    GameEventMessage, MotionDataMessage, HeadGazeMessage, SessionEventMessage,
)


async def handle_game_event(session_id: int, msg: GameEventMessage, db: AsyncSession) -> dict:
    """Save a validated game event to DB and return relay payload."""
    event = GameEvent(
        session_id=session_id,
        activity_type=msg.activity_type,
        event_type=msg.data.event,
        timestamp=utcnow(),
        reaction_time_ms=msg.data.reaction_time_ms,
        is_correct=msg.data.is_correct,
        round_number=msg.data.round,
        difficulty_level=msg.data.difficulty_level,
        is_baseline=msg.data.is_baseline,
        extra_data=msg.data.model_dump(),
    )
    db.add(event)
    await db.commit()

    return {
        "type": "game_event",
        "session_id": session_id,
        "activity_type": event.activity_type,
        "event_type": event.event_type,
        "reaction_time_ms": event.reaction_time_ms,
        "is_correct": event.is_correct,
        "round": event.round_number,
        "difficulty_level": event.difficulty_level,
        "is_baseline": event.is_baseline,
    }


async def handle_motion_data(session_id: int, msg: MotionDataMessage, db: AsyncSession) -> dict:
    """Save validated motion data to DB and return relay payload."""
    motion = BodyMotion(
        session_id=session_id,
        timestamp=utcnow(),
        trackers=msg.data.trackers,
        total_movement_index=msg.data.total_movement_index,
        tracker_confidence=msg.data.tracker_confidence,
        is_baseline=msg.data.is_baseline,
    )
    db.add(motion)
    await db.commit()

    return {
        "type": "motion_data",
        "session_id": session_id,
        "total_movement_index": motion.total_movement_index,
        "tracker_confidence": motion.tracker_confidence,
        "trackers": motion.trackers,
        "is_baseline": motion.is_baseline,
    }


async def handle_head_gaze(session_id: int, msg: HeadGazeMessage, db: AsyncSession) -> dict:
    """Save validated head gaze data to DB and return relay payload."""
    gaze = HeadGazeData(
        session_id=session_id,
        timestamp=utcnow(),
        hmd_rotation=msg.data.hmd_rotation,
        hmd_position=msg.data.hmd_position,
        is_looking_at_target=msg.data.is_looking_at_target,
        angle_to_target=msg.data.angle_to_target_degrees,
        is_baseline=msg.data.is_baseline,
    )
    db.add(gaze)
    await db.commit()

    return {
        "type": "head_gaze",
        "session_id": session_id,
        "is_looking_at_target": gaze.is_looking_at_target,
        "angle_to_target": gaze.angle_to_target,
        "hmd_rotation": gaze.hmd_rotation,
        "is_baseline": gaze.is_baseline,
    }


async def handle_session_event(session_id: int, msg: SessionEventMessage, db: AsyncSession) -> dict:
    """Handle session lifecycle events and update DB state."""
    event = msg.event
    activity_type = msg.activity_type or ""

    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        return {"type": "error", "message": "Session not found"}

    if event == "baseline_start":
        session.status = "baseline"
        baseline = BaselineData(session_id=session_id, started_at=utcnow())
        db.add(baseline)

    elif event == "baseline_end":
        res = await db.execute(
            select(BaselineData).where(BaselineData.session_id == session_id).order_by(BaselineData.id.desc())
        )
        bl = res.scalar_one_or_none()
        if bl:
            bl.ended_at = utcnow()
        session.status = "active"

    elif event == "activity_start":
        activity = GameActivity(
            session_id=session_id,
            activity_type=activity_type,
            started_at=utcnow(),
            is_baseline=msg.is_baseline or False,
        )
        db.add(activity)

    elif event == "activity_end":
        res = await db.execute(
            select(GameActivity)
            .where(GameActivity.session_id == session_id, GameActivity.activity_type == activity_type)
            .order_by(GameActivity.id.desc())
        )
        act = res.scalar_one_or_none()
        if act:
            act.ended_at = utcnow()
            summary = msg.summary or {}
            act.total_correct = summary.get("total_correct", act.total_correct)
            act.total_wrong = summary.get("total_wrong", act.total_wrong)
            act.avg_reaction_time_ms = summary.get("avg_reaction_time_ms", act.avg_reaction_time_ms)

    elif event == "session_end":
        session.status = "completed"
        session.ended_at = utcnow()

    await db.commit()

    return {
        "type": "session_event",
        "session_id": session_id,
        "event": event,
        "activity_type": activity_type,
        "status": session.status,
    }
