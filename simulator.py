"""
UE5 Simulator — Simulates all data that UE5 sends
Runs from Terminal and connects to the server via WebSocket
Sends: motion_data + game_events + head_gaze + session_events
"""

import asyncio
import json
import random
import math
import time
import argparse
import sys

try:
    import websockets
except ImportError:
    print("Install websockets: pip install websockets")
    sys.exit(1)

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)


SERVER = "http://localhost:8000"
WS_SERVER = "ws://localhost:8000"

# Simulated Tracker Data

TRACKER_NAMES = [
    "H_R", "LUA_Rotate", "RUA_R", "LRA_R", "RLA_R",
    "LH_R", "RH_R", "LUL_R", "RUL_R", "LLL_R",
    "RLL_R", "LF_R", "RF_R", "R_R"
]

GAMES = ["Boxes", "HitTheOrder", "ShellGame", "TrackTheTarget", "Animals_Game"]


class UE5Simulator:
    def __init__(self, mode="calm"):
        self.mode = mode  # calm, engaged, stressed, overwhelmed
        self.tick = 0
        self.session_id = None
        self.ws = None

    def generate_tracker_data(self) -> tuple:
        """Generate realistic quaternion + accel data for all 14 trackers"""
        base_movement = {
            "calm": 0.3,
            "engaged": 0.8,
            "stressed": 2.0,
            "overwhelmed": 4.0,
        }.get(self.mode, 0.5)

        # Add natural variation
        variation = math.sin(self.tick * 0.1) * 0.2 + random.gauss(0, 0.15)
        movement = max(0.05, base_movement + variation)

        trackers = {}
        for name in TRACKER_NAMES:
            # Body part multiplier
            if "UL" in name or "LL" in name or "F_R" in name:
                mult = 0.3  # legs move less
            elif "H_R" in name:
                mult = 0.5 + (0.3 if self.mode == "stressed" else 0)
            elif "UA" in name or "RA" in name:
                mult = 0.7
            else:
                mult = 0.5

            accel = movement * mult * random.uniform(0.7, 1.3)

            # Quaternion (slight rotation from identity)
            angle = random.gauss(0, movement * 5)
            rad = math.radians(angle)
            trackers[name] = {
                "x": round(math.sin(rad / 2) * random.choice([-1, 1]), 4),
                "y": round(random.gauss(0, 0.02), 4),
                "z": round(random.gauss(0, 0.02), 4),
                "w": round(math.cos(rad / 2), 4),
                "accel_magnitude": round(accel, 4),
            }

        total = sum(t["accel_magnitude"] for t in trackers.values()) / len(trackers)
        return trackers, round(total, 4)

    def generate_game_event(self, activity: str, is_baseline=False) -> dict:
        """Generate a game interaction event"""
        base_rt = {
            "calm": 400,
            "engaged": 300,
            "stressed": 600,
            "overwhelmed": 900,
        }.get(self.mode, 400)

        rt = max(100, base_rt + random.gauss(0, 80))

        # Accuracy based on state
        correct_prob = {
            "calm": 0.85,
            "engaged": 0.92,
            "stressed": 0.65,
            "overwhelmed": 0.40,
        }.get(self.mode, 0.75)

        is_correct = random.random() < correct_prob

        return {
            "type": "game_event",
            "timestamp": time.time(),
            "activity_type": activity,
            "data": {
                "event": "interaction",
                "reaction_time_ms": round(rt, 1),
                "is_correct": is_correct,
                "round": self.tick % 10 + 1,
                "score": random.randint(0, 100),
                "difficulty_level": 1,
                "is_baseline": is_baseline,
            }
        }

    def generate_head_gaze(self, is_baseline=False) -> dict:
        """Generate head gaze data"""
        base_angle = {
            "calm": 8,
            "engaged": 5,
            "stressed": 20,
            "overwhelmed": 35,
        }.get(self.mode, 10)

        angle = max(0, base_angle + random.gauss(0, 5))
        is_looking = angle < 30  # threshold

        return {
            "type": "head_gaze",
            "timestamp": time.time(),
            "data": {
                "hmd_rotation": {
                    "pitch": round(random.gauss(0, angle), 2),
                    "yaw": round(random.gauss(0, angle * 0.8), 2),
                    "roll": round(random.gauss(0, 3), 2),
                },
                "hmd_position": {
                    "x": round(random.gauss(0, 0.1), 3),
                    "y": round(1.2 + random.gauss(0, 0.05), 3),
                    "z": round(random.gauss(0, 0.1), 3),
                },
                "is_looking_at_target": is_looking,
                "angle_to_target_degrees": round(angle, 2),
                "is_baseline": is_baseline,
            }
        }

    def generate_motion_data(self, is_baseline=False) -> dict:
        trackers, total = self.generate_tracker_data()
        return {
            "type": "motion_data",
            "timestamp": time.time(),
            "data": {
                "trackers": trackers,
                "total_movement_index": total,
                "tracker_confidence": round(random.uniform(0.85, 0.99), 3),
                "is_baseline": is_baseline,
            }
        }


async def setup_session() -> tuple:
    """Register, login, create patient, start session — return (session_id, access_key, token)"""
    async with httpx.AsyncClient(base_url=SERVER) as c:
        # Register (ignore if exists)
        await c.post("/api/auth/register", json={
            "full_name": "Dr. Simulator",
            "email": "sim@yourmove.dev",
            "password": "sim123",
        })

        # Login
        r = await c.post("/api/auth/login", json={
            "email": "sim@yourmove.dev",
            "password": "sim123",
        })
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        # Check existing patients
        r = await c.get("/api/patients/", headers=h)
        patients = r.json()
        sim_patient = next((p for p in patients if p["full_name"] == "Test Child Sim"), None)

        if not sim_patient:
            r = await c.post("/api/patients/", json={
                "full_name": "Test Child Sim",
                "age": 8,
                "diagnosis": "ASD",
                "notes": "Simulator test patient",
            }, headers=h)
            sim_patient = r.json()

        access_key = sim_patient["access_key"]

        # Start session
        r = await c.post(
            "/api/sessions/start",
            json={"access_key": sim_patient["access_key"]},
            headers=h,
        )
        session = r.json()

        print(f"Session created: #{session['session_id']}")
        print(f"   Patient: {session['patient_name']}")
        print(f"   Access Key: {access_key}")
        return session["session_id"], access_key, token


async def run_auto_session(stress_mode=False):
    """Run a complete automated session"""
    session_id, _, token = await setup_session()
    sim = UE5Simulator(mode="calm")

    uri = f"{WS_SERVER}/ws/ue5/{session_id}?token={token}"
    print(f"\nConnecting to /ws/ue5/{session_id}...")

    async with websockets.connect(uri) as ws:
        print("WebSocket connected — starting session\n")

        # Phase 1: Baseline
        print("Phase 1: BASELINE (30s)")
        await ws.send(json.dumps({
            "type": "session_event", "event": "baseline_start", "timestamp": time.time()
        }))
        await ws.send(json.dumps({
            "type": "session_event", "event": "activity_start",
            "activity_type": "Boxes", "is_baseline": True, "timestamp": time.time()
        }))

        sim.mode = "calm"
        for i in range(30):
            sim.tick = i
            await ws.send(json.dumps(sim.generate_motion_data(is_baseline=True)))
            await ws.send(json.dumps(sim.generate_head_gaze(is_baseline=True)))
            if i % 3 == 0:
                await ws.send(json.dumps(sim.generate_game_event("Boxes", is_baseline=True)))

            if i % 10 == 0:
                print(f"   Baseline tick {i}/30 — mode: {sim.mode}")

            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=0.05)
                data = json.loads(msg)
                if data.get("type") == "ai_command":
                    print(f"   AI: {data['command']} — {data.get('reason','')}")
            except asyncio.TimeoutError:
                pass

            await asyncio.sleep(0.3)

        await ws.send(json.dumps({
            "type": "session_event", "event": "activity_end",
            "activity_type": "Boxes", "timestamp": time.time(),
            "summary": {"total_correct": 8, "total_wrong": 2}
        }))
        await ws.send(json.dumps({
            "type": "session_event", "event": "baseline_end", "timestamp": time.time()
        }))
        print("Baseline complete\n")

        # Phase 2: Normal gameplay
        phases = [
            ("engaged", "HitTheOrder", 20),
            ("stressed", "ShellGame", 20),
            ("overwhelmed", "TrackTheTarget", 15),
            ("calm", "Boxes", 10),
        ] if stress_mode else [
            ("calm", "HitTheOrder", 20),
            ("engaged", "ShellGame", 20),
            ("calm", "TrackTheTarget", 15),
            ("engaged", "Animals_Game", 10),
        ]

        for mode, game, duration in phases:
            sim.mode = mode
            state_label = {"calm": "CALM", "engaged": "ENGAGED", "stressed": "STRESSED", "overwhelmed": "OVERWHELMED"}
            print(f"Phase: {game} — Mode: {state_label.get(mode, mode)} ({duration}s)")

            await ws.send(json.dumps({
                "type": "session_event", "event": "activity_start",
                "activity_type": game, "timestamp": time.time()
            }))

            correct, wrong = 0, 0
            for i in range(duration):
                sim.tick += 1
                await ws.send(json.dumps(sim.generate_motion_data()))
                await ws.send(json.dumps(sim.generate_head_gaze()))

                if i % 2 == 0:
                    event = sim.generate_game_event(game)
                    await ws.send(json.dumps(event))
                    if event["data"]["is_correct"]:
                        correct += 1
                    else:
                        wrong += 1

                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.05)
                    data = json.loads(msg)
                    if data.get("type") == "ai_command":
                        print(f"   AI Command: {data['command']} — {data.get('reason','')}")
                    elif data.get("type") == "doctor_command":
                        print(f"   Doctor: {data['command']} = {data.get('value','')}")
                except asyncio.TimeoutError:
                    pass

                await asyncio.sleep(0.3)

            await ws.send(json.dumps({
                "type": "session_event", "event": "activity_end",
                "activity_type": game, "timestamp": time.time(),
                "summary": {"total_correct": correct, "total_wrong": wrong}
            }))
            print(f"   Results: {correct} correct, {wrong} wrong\n")

        await ws.send(json.dumps({
            "type": "session_event", "event": "session_end", "timestamp": time.time()
        }))
        print("Session complete!")
        print(f"\nOpen Dashboard: {SERVER}/session/{session_id}")


async def run_interactive():
    """Interactive mode — manual control"""
    session_id, _, token = await setup_session()
    sim = UE5Simulator(mode="calm")

    uri = f"{WS_SERVER}/ws/ue5/{session_id}?token={token}"
    async with websockets.connect(uri) as ws:
        print(f"\nConnected to session #{session_id}")
        print(f"Open Dashboard: {SERVER}/session/{session_id}")
        print("\nCommands:")
        print("  [c]alm  [e]ngaged  [s]tressed  [o]verwhelmed")
        print("  [b]aseline  [bend] — end baseline")
        print("  [g]ame <name>  [end] — session end")
        print("  [t]ick <N> — send N data points")
        print("  [q]uit")

        async def receive_loop():
            try:
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if data.get("type") in ("ai_command", "doctor_command"):
                        t = data["type"].replace("_", " ").title()
                        print(f"\n   {t}: {data.get('command')} = {data.get('value','')} {data.get('reason','')}")
            except Exception:
                pass

        recv_task = asyncio.create_task(receive_loop())

        while True:
            try:
                cmd = await asyncio.get_event_loop().run_in_executor(None, lambda: input("\n> "))
            except EOFError:
                break

            cmd = cmd.strip().lower()
            if cmd in ("q", "quit", "exit"):
                await ws.send(json.dumps({
                    "type": "session_event", "event": "session_end", "timestamp": time.time()
                }))
                break
            elif cmd in ("c", "calm"):
                sim.mode = "calm"
                print("Mode: CALM")
            elif cmd in ("e", "engaged"):
                sim.mode = "engaged"
                print("Mode: ENGAGED")
            elif cmd in ("s", "stressed"):
                sim.mode = "stressed"
                print("Mode: STRESSED")
            elif cmd in ("o", "overwhelmed"):
                sim.mode = "overwhelmed"
                print("Mode: OVERWHELMED")
            elif cmd in ("b", "baseline"):
                await ws.send(json.dumps({
                    "type": "session_event", "event": "baseline_start", "timestamp": time.time()
                }))
                print("Baseline started")
            elif cmd == "bend":
                await ws.send(json.dumps({
                    "type": "session_event", "event": "baseline_end", "timestamp": time.time()
                }))
                print("Baseline ended")
            elif cmd.startswith("g ") or cmd.startswith("game "):
                game = cmd.split(None, 1)[1] if " " in cmd else "HitTheOrder"
                await ws.send(json.dumps({
                    "type": "session_event", "event": "activity_start",
                    "activity_type": game, "timestamp": time.time()
                }))
                print(f"Started game: {game}")
            elif cmd == "end":
                await ws.send(json.dumps({
                    "type": "session_event", "event": "session_end", "timestamp": time.time()
                }))
                print("Session ended")
                break
            elif cmd.startswith("t"):
                parts = cmd.split()
                n = int(parts[1]) if len(parts) > 1 else 10
                game = parts[2] if len(parts) > 2 else "HitTheOrder"
                print(f"   Sending {n} ticks...")
                for i in range(n):
                    sim.tick += 1
                    await ws.send(json.dumps(sim.generate_motion_data()))
                    await ws.send(json.dumps(sim.generate_head_gaze()))
                    if i % 2 == 0:
                        await ws.send(json.dumps(sim.generate_game_event(game)))
                    await asyncio.sleep(0.1)
                print(f"   Sent {n} ticks")
            else:
                print("   Unknown command.")

        recv_task.cancel()


def main():
    parser = argparse.ArgumentParser(description="YourMove UE5 Simulator")
    parser.add_argument("--auto", action="store_true", help="Run automatic full session")
    parser.add_argument("--stress", action="store_true", help="Simulate stress scenario")
    args = parser.parse_args()

    print("=" * 42)
    print("   YourMove — UE5 Simulator")
    print("=" * 42)
    print(f"Server: {SERVER}\n")

    if args.auto:
        asyncio.run(run_auto_session(stress_mode=args.stress))
    else:
        asyncio.run(run_interactive())


if __name__ == "__main__":
    main()
