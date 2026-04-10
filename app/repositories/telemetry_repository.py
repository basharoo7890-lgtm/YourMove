from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import utcnow
from app.models import (
    AIReport,
    BaselineData,
    BodyMotion,
    DoctorCommand,
    GameActivity,
    GameEvent,
    HeadGazeData,
    MLResult,
    Session,
)


class TelemetryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_game_event(self, session_id: int, payload: dict) -> GameEvent:
        event = GameEvent(session_id=session_id, timestamp=utcnow(), **payload)
        self.db.add(event)
        await self.db.commit()
        return event

    async def create_motion(self, session_id: int, payload: dict) -> BodyMotion:
        motion = BodyMotion(session_id=session_id, timestamp=utcnow(), **payload)
        self.db.add(motion)
        await self.db.commit()
        return motion

    async def create_head_gaze(self, session_id: int, payload: dict) -> HeadGazeData:
        gaze = HeadGazeData(session_id=session_id, timestamp=utcnow(), **payload)
        self.db.add(gaze)
        await self.db.commit()
        return gaze

    async def create_ml_result(self, session_id: int, layer: str, classification: dict) -> None:
        ml = MLResult(
            session_id=session_id,
            layer=layer,
            prediction=classification.get("state"),
            confidence=classification.get("confidence"),
            features={"stress_score": classification.get("stress_score")},
            feature_importance=classification.get("feature_importance", {}),
        )
        self.db.add(ml)
        await self.db.commit()

    async def persist_ml_state(self, session_id: int, state: dict) -> None:
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if session:
            session.ml_state = state
            await self.db.commit()

    async def create_doctor_command(self, session_id: int, command: str, value: str | None) -> None:
        self.db.add(DoctorCommand(session_id=session_id, command=command, value=value))
        await self.db.commit()

    async def get_session(self, session_id: int) -> Session | None:
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    async def create_baseline(self, session_id: int) -> None:
        self.db.add(BaselineData(session_id=session_id, started_at=utcnow()))
        await self.db.commit()

    async def end_latest_baseline(self, session_id: int) -> None:
        result = await self.db.execute(
            select(BaselineData).where(BaselineData.session_id == session_id).order_by(BaselineData.id.desc())
        )
        baseline = result.scalar_one_or_none()
        if baseline:
            baseline.ended_at = utcnow()
            await self.db.commit()

    async def create_activity(self, session_id: int, activity_type: str, is_baseline: bool) -> None:
        self.db.add(
            GameActivity(
                session_id=session_id,
                activity_type=activity_type,
                started_at=utcnow(),
                is_baseline=is_baseline,
            )
        )
        await self.db.commit()

    async def end_latest_activity(self, session_id: int, activity_type: str, summary: dict | None) -> None:
        result = await self.db.execute(
            select(GameActivity)
            .where(GameActivity.session_id == session_id, GameActivity.activity_type == activity_type)
            .order_by(GameActivity.id.desc())
        )
        activity = result.scalar_one_or_none()
        if activity:
            activity.ended_at = utcnow()
            data = summary or {}
            activity.total_correct = data.get("total_correct", activity.total_correct)
            activity.total_wrong = data.get("total_wrong", activity.total_wrong)
            activity.avg_reaction_time_ms = data.get("avg_reaction_time_ms", activity.avg_reaction_time_ms)
            await self.db.commit()

    async def get_recommendation_metrics(self, session_id: int) -> dict:
        rt_q = await self.db.execute(
            select(func.avg(GameEvent.reaction_time_ms)).where(
                GameEvent.session_id == session_id, GameEvent.reaction_time_ms.is_not(None)
            )
        )
        avg_rt = rt_q.scalar_one_or_none()

        movement_q = await self.db.execute(
            select(func.avg(BodyMotion.total_movement_index)).where(
                BodyMotion.session_id == session_id, BodyMotion.total_movement_index.is_not(None)
            )
        )
        avg_movement = movement_q.scalar_one_or_none()

        stress_q = await self.db.execute(
            select(func.count(MLResult.id)).where(
                MLResult.session_id == session_id, MLResult.prediction.in_(["STRESSED", "OVERWHELMED"])
            )
        )
        stress_count = int(stress_q.scalar_one() or 0)

        total_cls_q = await self.db.execute(
            select(func.count(MLResult.id)).where(MLResult.session_id == session_id)
        )
        total_cls = int(total_cls_q.scalar_one() or 0)

        return {
            "avg_reaction_time_ms": float(avg_rt) if avg_rt is not None else None,
            "avg_movement_index": float(avg_movement) if avg_movement is not None else None,
            "stress_count": stress_count,
            "total_classifications": total_cls,
        }

    async def create_ai_report(self, session_id: int, report_text: str, report_json: dict, model_used: str) -> None:
        report = AIReport(
            session_id=session_id,
            report_text=report_text,
            report_json=report_json,
            model_used=model_used,
            anonymized=True,
        )
        self.db.add(report)
        await self.db.commit()

    async def get_latest_ai_report(self, session_id: int) -> AIReport | None:
        result = await self.db.execute(
            select(AIReport).where(AIReport.session_id == session_id).order_by(AIReport.generated_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_report_context(self, session_id: int) -> dict:
        session = await self.get_session(session_id)

        events_count_q = await self.db.execute(select(func.count(GameEvent.id)).where(GameEvent.session_id == session_id))
        events_count = int(events_count_q.scalar_one() or 0)

        motion_count_q = await self.db.execute(select(func.count(BodyMotion.id)).where(BodyMotion.session_id == session_id))
        motion_count = int(motion_count_q.scalar_one() or 0)

        gaze_count_q = await self.db.execute(select(func.count(HeadGazeData.id)).where(HeadGazeData.session_id == session_id))
        gaze_count = int(gaze_count_q.scalar_one() or 0)

        last_cls_q = await self.db.execute(
            select(MLResult.prediction, MLResult.confidence)
            .where(MLResult.session_id == session_id)
            .order_by(MLResult.timestamp.desc())
        )
        last_cls = last_cls_q.first()

        return {
            "session_status": session.status if session else None,
            "started_at": str(session.started_at) if session else None,
            "ended_at": str(session.ended_at) if session and session.ended_at else None,
            "events_count": events_count,
            "motion_count": motion_count,
            "gaze_count": gaze_count,
            "latest_state": last_cls[0] if last_cls else None,
            "latest_confidence": float(last_cls[1]) if last_cls and last_cls[1] is not None else None,
        }
