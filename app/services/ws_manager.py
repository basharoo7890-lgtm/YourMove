"""
WebSocket Connection Manager
- Manages UE5 <-> Server <-> Dashboard connections per session
- Relays data from UE5 to Dashboard in real-time
- Routes doctor commands from Dashboard to UE5
"""

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
from typing import Dict, Optional
import asyncio
import logging

logger = logging.getLogger("yourmove.ws_manager")

HEARTBEAT_INTERVAL = 30  # seconds
HEARTBEAT_TIMEOUT = 10  # seconds


class ConnectionManager:
    def __init__(self):
        # session_id -> WebSocket
        self.ue5_connections: Dict[int, WebSocket] = {}
        self.dashboard_connections: Dict[int, WebSocket] = {}
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}

    # ─── UE5 ───────────────────────────────────────────

    async def connect_ue5(self, session_id: int, ws: WebSocket, subprotocol: Optional[str] = None):
        # Close existing connection if any (prevents orphaned clients)
        existing = self.ue5_connections.get(session_id)
        if existing:
            logger.warning("Replacing existing UE5 connection for session %s", session_id)
            try:
                await existing.close(code=4009, reason="Replaced by new connection")
            except Exception:
                pass

        await ws.accept(subprotocol=subprotocol)
        self.ue5_connections[session_id] = ws
        self._start_heartbeat(f"ue5:{session_id}", ws, session_id, "ue5")
        logger.info("UE5 connected: session %s", session_id)
        await self._notify_dashboard(session_id, {
            "type": "system", "event": "ue5_connected"
        })

    def disconnect_ue5(self, session_id: int):
        self.ue5_connections.pop(session_id, None)
        self._stop_heartbeat(f"ue5:{session_id}")
        logger.info("UE5 disconnected: session %s", session_id)

    # ─── Dashboard ─────────────────────────────────────

    async def connect_dashboard(self, session_id: int, ws: WebSocket, subprotocol: Optional[str] = None):
        # Close existing connection if any (prevents orphaned clients)
        existing = self.dashboard_connections.get(session_id)
        if existing:
            logger.warning("Replacing existing Dashboard connection for session %s", session_id)
            try:
                await existing.close(code=4009, reason="Replaced by new connection")
            except Exception:
                pass

        await ws.accept(subprotocol=subprotocol)
        self.dashboard_connections[session_id] = ws
        self._start_heartbeat(f"dash:{session_id}", ws, session_id, "dashboard")
        logger.info("Dashboard connected: session %s", session_id)

    def disconnect_dashboard(self, session_id: int):
        self.dashboard_connections.pop(session_id, None)
        self._stop_heartbeat(f"dash:{session_id}")
        logger.info("Dashboard disconnected: session %s", session_id)

    # ─── Relay ─────────────────────────────────────────

    async def relay_to_dashboard(self, session_id: int, data: dict):
        """Send processed data from UE5 -> Dashboard"""
        await self._notify_dashboard(session_id, data)

    async def send_to_ue5(self, session_id: int, data: dict):
        """Send command from Dashboard/AI -> UE5"""
        ws = self.ue5_connections.get(session_id)
        if ws:
            try:
                await ws.send_json(data)
            except WebSocketDisconnect:
                self.disconnect_ue5(session_id)
            except Exception:
                logger.exception("Error sending to UE5 session %s, disconnecting", session_id)
                self.disconnect_ue5(session_id)

    async def _notify_dashboard(self, session_id: int, data: dict):
        ws = self.dashboard_connections.get(session_id)
        if ws:
            try:
                await ws.send_json(data)
            except WebSocketDisconnect:
                self.disconnect_dashboard(session_id)
            except Exception:
                logger.exception("Error sending to Dashboard session %s, disconnecting", session_id)
                self.disconnect_dashboard(session_id)

    def is_ue5_connected(self, session_id: int) -> bool:
        return session_id in self.ue5_connections

    def is_dashboard_connected(self, session_id: int) -> bool:
        return session_id in self.dashboard_connections

    # ─── Heartbeat ─────────────────────────────────────

    def _start_heartbeat(self, key: str, ws: WebSocket, session_id: int, client_type: str):
        self._stop_heartbeat(key)
        self._heartbeat_tasks[key] = asyncio.create_task(
            self._heartbeat_loop(key, ws, session_id, client_type)
        )

    def _stop_heartbeat(self, key: str):
        task = self._heartbeat_tasks.pop(key, None)
        if task and not task.done():
            task.cancel()

    async def _heartbeat_loop(self, key: str, ws: WebSocket, session_id: int, client_type: str):
        """Send periodic WebSocket pings to detect stale connections."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                try:
                    await asyncio.wait_for(
                        ws.send_json({"type": "ping"}),
                        timeout=HEARTBEAT_TIMEOUT,
                    )
                except (asyncio.TimeoutError, Exception):
                    logger.warning("Heartbeat failed for %s session %s, disconnecting", client_type, session_id)
                    if client_type == "ue5":
                        self.disconnect_ue5(session_id)
                    else:
                        self.disconnect_dashboard(session_id)
                    break
        except asyncio.CancelledError:
            pass


# Singleton
manager = ConnectionManager()
