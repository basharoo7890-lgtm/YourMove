from app.repositories.telemetry_repository import TelemetryRepository
from app.schemas import GameEventMessage, HeadGazeMessage, MotionDataMessage, SessionEventMessage


async def process_game_event(session_id: int, msg: GameEventMessage, repo: TelemetryRepository) -> dict:
    event = await repo.create_game_event(
        session_id,
        {
            "activity_type": msg.activity_type,
            "event_type": msg.data.event,
            "reaction_time_ms": msg.data.reaction_time_ms,
            "is_correct": msg.data.is_correct,
            "round_number": msg.data.round,
            "difficulty_level": msg.data.difficulty_level,
            "is_baseline": msg.data.is_baseline,
            "extra_data": msg.data.model_dump(),
        },
    )
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


async def process_motion_data(session_id: int, msg: MotionDataMessage, repo: TelemetryRepository) -> dict:
    motion = await repo.create_motion(
        session_id,
        {
            "trackers": msg.data.trackers,
            "total_movement_index": msg.data.total_movement_index,
            "tracker_confidence": msg.data.tracker_confidence,
            "is_baseline": msg.data.is_baseline,
        },
    )
    return {
        "type": "motion_data",
        "session_id": session_id,
        "total_movement_index": motion.total_movement_index,
        "tracker_confidence": motion.tracker_confidence,
        "trackers": motion.trackers,
        "is_baseline": motion.is_baseline,
    }


async def process_head_gaze(session_id: int, msg: HeadGazeMessage, repo: TelemetryRepository) -> dict:
    gaze = await repo.create_head_gaze(
        session_id,
        {
            "hmd_rotation": msg.data.hmd_rotation,
            "hmd_position": msg.data.hmd_position,
            "is_looking_at_target": msg.data.is_looking_at_target,
            "angle_to_target": msg.data.angle_to_target_degrees,
            "is_baseline": msg.data.is_baseline,
        },
    )
    return {
        "type": "head_gaze",
        "session_id": session_id,
        "is_looking_at_target": gaze.is_looking_at_target,
        "angle_to_target": gaze.angle_to_target,
        "hmd_rotation": gaze.hmd_rotation,
        "is_baseline": gaze.is_baseline,
    }


async def process_session_event(session_id: int, msg: SessionEventMessage, repo: TelemetryRepository) -> dict:
    session = await repo.get_session(session_id)
    if not session:
        return {"type": "error", "message": "Session not found"}

    if msg.event == "baseline_start":
        session.status = "baseline"
        await repo.create_baseline(session_id)
    elif msg.event == "baseline_end":
        session.status = "active"
        await repo.end_latest_baseline(session_id)
    elif msg.event == "activity_start":
        await repo.create_activity(session_id, msg.activity_type or "", bool(msg.is_baseline))
    elif msg.event == "activity_end":
        await repo.end_latest_activity(session_id, msg.activity_type or "", msg.summary)
    elif msg.event == "session_end":
        session.status = "completed"

    await repo.db.commit()
    return {
        "type": "session_event",
        "session_id": session_id,
        "event": msg.event,
        "activity_type": msg.activity_type or "",
        "status": session.status,
    }
