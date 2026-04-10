import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy import select

from app.core.database import async_session
from app.core.security import authenticate_ws_token
from app.ml import ml_orchestrator
from app.models import Session
from app.repositories import TelemetryRepository
from app.schemas import (
    DoctorCommandMessage,
    GameEventMessage,
    HeadGazeMessage,
    MotionDataMessage,
    SessionEventMessage,
)
from app.services.recommendation_service import RecommendationService
from app.websocket.manager import manager
from app.websocket.service import process_game_event, process_head_gaze, process_motion_data, process_session_event

router = APIRouter()
logger = logging.getLogger("yourmove.websocket")


def _parse_path_session_id(raw: str) -> int | None:
    """Accept numeric id or UE-style '$15' (often appears as %2415 in URLs) so routing does not 403 before the handler."""
    s = (raw or "").strip()
    if not s:
        return None
    if s.startswith("$"):
        s = s[1:]
    try:
        return int(s)
    except ValueError:
        return None


async def _reject_ws(websocket: WebSocket, *, code: int, reason: str) -> None:
    await websocket.accept()
    await websocket.close(code=code, reason=reason)


def _extract_ws_token(websocket: WebSocket) -> tuple[str | None, str | None]:
    protocols = websocket.headers.get("sec-websocket-protocol", "")
    for proto in protocols.split(","):
        value = proto.strip()
        if value.startswith("access_token."):
            return value[len("access_token.") :], "access_token"
    token = websocket.query_params.get("token")
    return (token, None) if token else (None, None)


async def _authenticate_session(websocket: WebSocket, session_id: int) -> tuple[int, str | None] | None:
    token, subprotocol = _extract_ws_token(websocket)
    if not token:
        await websocket.accept()
        await websocket.close(code=4001, reason="Missing authentication token")
        return None

    async with async_session() as db:
        user = await authenticate_ws_token(token, db)
        if not user:
            await websocket.accept()
            await websocket.close(code=4001, reason="Invalid authentication token")
            return None
        result = await db.execute(select(Session).where(Session.id == session_id, Session.therapist_id == user.id))
        session = result.scalar_one_or_none()
        if not session:
            await websocket.accept()
            await websocket.close(code=4004, reason="Session not found")
            return None
        if session.ml_state:
            ml_orchestrator.restore_state(session_id, session.ml_state)
        return user.id, subprotocol


@router.websocket("/ws/ue5/{session_id}")
async def ws_ue5(websocket: WebSocket, session_id: str):
    sid = _parse_path_session_id(session_id)
    if sid is None:
        logger.warning("Invalid WebSocket session id path segment: %r", session_id)
        await _reject_ws(websocket, code=4400, reason="Invalid session id")
        return
    auth = await _authenticate_session(websocket, sid)
    if not auth:
        return
    _, subprotocol = auth
    await manager.connect_ue5(sid, websocket, subprotocol=subprotocol)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            msg_type = data.get("type")
            if msg_type in ("ping", "pong"):
                continue
            try:
                async with async_session() as db:
                    repo = TelemetryRepository(db)
                    if msg_type == "game_event":
                        msg = GameEventMessage(**data)
                        parsed = await process_game_event(sid, msg, repo)
                        ml = ml_orchestrator.process_game_event(sid, msg.data.reaction_time_ms, msg.data.is_baseline)
                        if ml.get("classification"):
                            await repo.create_ml_result(sid, "classifier", ml["classification"])
                        await manager.relay_to_dashboard(sid, {**parsed, "ml": ml})
                    elif msg_type == "motion_data":
                        msg = MotionDataMessage(**data)
                        parsed = await process_motion_data(sid, msg, repo)
                        ml = ml_orchestrator.process_motion(
                            sid,
                            msg.data.trackers,
                            msg.data.total_movement_index,
                            msg.data.is_baseline,
                        )
                        if ml.get("classification"):
                            await repo.create_ml_result(sid, "classifier", ml["classification"])
                        await manager.relay_to_dashboard(sid, {**parsed, "ml": ml})
                    elif msg_type == "head_gaze":
                        msg = HeadGazeMessage(**data)
                        parsed = await process_head_gaze(sid, msg, repo)
                        ml = ml_orchestrator.process_gaze(sid, msg.data.angle_to_target_degrees)
                        await manager.relay_to_dashboard(sid, {**parsed, "ml_gaze": ml})
                    elif msg_type == "session_event":
                        msg = SessionEventMessage(**data)
                        parsed = await process_session_event(sid, msg, repo)
                        if msg.event in ("baseline_end", "session_end"):
                            await repo.persist_ml_state(sid, ml_orchestrator.snapshot_state(sid))
                        if msg.event == "session_end":
                            recommendation = await RecommendationService(repo).build_end_session_recommendation(sid)
                            await manager.relay_to_dashboard(sid, recommendation)
                            ml_orchestrator.cleanup(sid)
                        await manager.relay_to_dashboard(sid, parsed)
                    else:
                        continue
            except ValidationError as exc:
                logger.warning("Invalid message for session %s: %s", sid, exc.error_count())
            except Exception:
                logger.exception("Processing failed for session %s", sid)
    except WebSocketDisconnect:
        manager.disconnect_ue5(sid)
    finally:
        try:
            async with async_session() as db:
                repo = TelemetryRepository(db)
                await repo.persist_ml_state(sid, ml_orchestrator.snapshot_state(sid))
        except Exception:
            logger.exception("Persist ML state failed for session %s", sid)
        await manager.relay_to_dashboard(sid, {"type": "system", "event": "ue5_disconnected"})


@router.websocket("/ws/dashboard/{session_id}")
async def ws_dashboard(websocket: WebSocket, session_id: str):
    sid = _parse_path_session_id(session_id)
    if sid is None:
        logger.warning("Invalid WebSocket session id path segment: %r", session_id)
        await _reject_ws(websocket, code=4400, reason="Invalid session id")
        return
    auth = await _authenticate_session(websocket, sid)
    if not auth:
        return
    user_id, subprotocol = auth
    await manager.connect_dashboard(sid, websocket, subprotocol=subprotocol)
    await websocket.send_json({"type": "system", "event": "connected", "ue5_connected": manager.is_ue5_connected(sid)})

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            if data.get("type") in ("ping", "pong"):
                continue
            if data.get("type") != "doctor_command":
                continue

            cmd = DoctorCommandMessage(**data)
            async with async_session() as db:
                repo = TelemetryRepository(db)
                await repo.create_doctor_command(sid, cmd.command, str(cmd.value or ""))
            await manager.send_to_ue5(
                sid,
                {"type": "doctor_command", "command": cmd.command, "value": cmd.value, "doctor_id": cmd.doctor_id or user_id},
            )
    except WebSocketDisconnect:
        manager.disconnect_dashboard(sid)
        await manager.send_to_ue5(sid, {"type": "system", "event": "dashboard_disconnected"})
