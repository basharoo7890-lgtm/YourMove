"""
Smoke-style E2E script.
Run manually against a running server:
    python tests/test_e2e.py
"""

import asyncio
import json
import time

import httpx
import websockets

SERVER = "http://localhost:8000"
WS_URL = "ws://localhost:8000"


async def run() -> None:
    async with httpx.AsyncClient(base_url=SERVER, timeout=10) as client:
        health = await client.get("/health")
        assert health.status_code == 200

        await client.post(
            "/api/auth/register",
            json={"full_name": "Dr. E2E", "email": "e2e@example.com", "password": "password123"},
        )
        login = await client.post("/api/auth/login", json={"email": "e2e@example.com", "password": "password123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        created = await client.post("/api/patients/", json={"full_name": "Test Child", "age": 8}, headers=headers)
        patient = created.json()
        session_start = await client.post(
            "/api/sessions/start",
            json={"access_key": patient["access_key"]},
            headers=headers,
        )
        session_id = session_start.json()["session_id"]

        dashboard_messages = []

        async def dashboard_listener() -> None:
            uri = f"{WS_URL}/ws/dashboard/{session_id}?token={token}"
            async with websockets.connect(uri) as ws:
                for _ in range(3):
                    dashboard_messages.append(json.loads(await ws.recv()))

        task = asyncio.create_task(dashboard_listener())
        await asyncio.sleep(0.2)
        ue5_uri = f"{WS_URL}/ws/ue5/{session_id}?token={token}"
        async with websockets.connect(ue5_uri) as ws:
            await ws.send(json.dumps({"type": "session_event", "event": "baseline_start", "timestamp": time.time()}))
            await ws.send(
                json.dumps(
                    {
                        "type": "motion_data",
                        "timestamp": time.time(),
                        "data": {"trackers": {"H_R": {"accel_magnitude": 0.5}}, "total_movement_index": 0.5},
                    }
                )
            )
            await ws.send(json.dumps({"type": "session_event", "event": "session_end", "timestamp": time.time()}))

        await asyncio.sleep(0.2)
        task.cancel()
        assert any(msg.get("type") in {"system", "motion_data", "session_event"} for msg in dashboard_messages)


if __name__ == "__main__":
    asyncio.run(run())
