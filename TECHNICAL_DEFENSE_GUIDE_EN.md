# YourMove Technical Defense Guide (English)

## 1) What the project does

YourMove is a real-time VR assessment and support platform for children with ASD/ADHD.  
The child plays VR activities while the backend receives live telemetry and game events, analyzes behavior, and provides decision support to the therapist.

Core outcomes:
- Real-time child state estimation (`CALM`, `ENGAGED`, `STRESSED`, `OVERWHELMED`)
- Motion behavior analysis (`NORMAL`, `FATIGUE`, `DISTRACTION`, `HYPERACTIVE`)
- PSI (Patient Stability Index) score
- Live therapist controls and AI-assisted recommendations
- End-session final report (Gemini optional, local fallback always available)

## 2) End-to-end architecture

1. UE5 sends telemetry and gameplay events over WebSocket.
2. FastAPI validates all messages using Pydantic schemas.
3. Data is stored in SQLAlchemy models (SQLite by default, PostgreSQL-ready).
4. ML pipeline runs in real time:
   - Layer 1: Statistical
   - Layer 2: Stress classifier
   - Layer 3: Motion analysis
5. Enriched data is relayed to therapist dashboard in real time.
6. At session end, recommendation and final report are generated.

## 3) AI layers (full explanation)

### Layer 1: Statistical features
- **EWMA** smooths noisy movement and reaction-time streams.
- **Z-score** detects anomalies against baseline/rolling distribution.
- **CV** measures consistency/instability.
- **Trend (OLS-like slope direction)** detects increasing/decreasing behavior.

Why this matters:
- Gives robust, low-latency features without heavy model training.
- Useful for noisy sensor data.

### Layer 2: Stress state classifier
- Rule-based scoring currently (production-safe for demo).
- Maps feature patterns to:
  - `CALM`
  - `ENGAGED`
  - `STRESSED`
  - `OVERWHELMED`
- Includes smoothing logic to avoid rapid state flicker.
- Emits AI commands when stress persists (example: break suggestion or reduce difficulty).

### Layer 3: Motion analysis
- **RMS** for movement intensity.
- **Entropy** for movement randomness.
- **Dominant frequency** for repetitive vs chaotic patterns.
- **Upper/lower ratio** for pattern interpretation.
- Produces motion state label (`NORMAL`, `FATIGUE`, etc.).

### PSI (Patient Stability Index)
Composite score from stress, movement stability, RT consistency, gaze stability, and motion pattern.

## 4) Security (full explanation)

### Authentication and Authorization
- JWT-based auth for API.
- Password hashing with bcrypt/passlib.
- Every protected endpoint requires valid token.
- Session ownership checks ensure therapist can only access own sessions.

### WebSocket security
- Token authentication on WebSocket handshake (subprotocol + fallback mode).
- Session ownership is verified before accepting streams.
- Invalid/missing token => connection closed with auth error code.

### Input validation
- Pydantic validation for REST payloads and WebSocket message schemas.
- Type checks and field constraints reduce malformed or malicious input.

### Abuse protection
- Rate limiting on session-start endpoint.
- Structured logging and defensive exception handling.

### Data safety
- No plaintext passwords.
- AI outputs are assistive and non-diagnostic.
- Report generation includes guardrails.

## 5) Data sent and received (full explanation)

### UE5 -> Server
- `game_event`:
  - activity type
  - reaction time
  - correctness
  - baseline flag
- `motion_data`:
  - tracker quaternions/accel-derived movement values
  - movement index
  - confidence
- `head_gaze`:
  - HMD orientation/position
  - angle-to-target
  - attention flag
- `session_event`:
  - baseline/session lifecycle transitions

### Server -> Dashboard
- Raw + enriched events:
  - statistical output
  - classification
  - motion analysis
  - PSI
  - recommendation/final-report events when available

### Dashboard/Doctor -> Server -> UE5
- `doctor_command`:
  - pause/resume
  - difficulty/brightness/volume changes
  - break/reward/session end controls

### Storage
- Session and telemetry tables persist all major streams.
- `ai_reports` stores generated final reports.

## 6) Is Gemini used now?

Current behavior:
- Final report service supports **Gemini API** if `GOOGLE_API_KEY` exists.
- If API key is missing or Gemini fails, system uses **local free fallback** and still generates final report.

So:
- Gemini is **optional**.
- System remains functional without paid APIs.

## 7) What you need to configure for AI reports

Required for local free mode only:
- Nothing extra.

Optional for Gemini:
- Set `GOOGLE_API_KEY` in `.env`
- (Optional) set `GEMINI_MODEL` (default: `gemini-1.5-flash`)

## 8) Competition Q&A (ready answers)

### Q1: What is your AI contribution?
We implemented a multi-layer real-time behavioral analytics pipeline: statistical feature extraction, stress-state classification, motion pattern analysis, PSI scoring, and automated recommendations.

### Q2: Is this diagnostic AI?
No. It is decision support for therapist-supervised sessions. It does not diagnose or prescribe medication.

### Q3: Why three AI layers?
To combine fast signal stability (Layer 1), interpretable state inference (Layer 2), and movement behavior semantics (Layer 3) for robust real-time decisions.

### Q4: How do you ensure security?
JWT auth, hashed passwords, session ownership checks, WebSocket auth, strict schema validation, rate limiting, and defensive error handling.

### Q5: What if external AI API is unavailable?
The system falls back to local report generation and remains operational.

### Q6: What is saved in the database?
Patients, sessions, events, motion, gaze, ML outputs, commands, and reports.

### Q7: Why is this useful clinically?
It adds objective, timestamped evidence to therapist observations and supports consistent session adaptation.

## 9) Suggested live demo script

1. Doctor login.
2. Start session by access key.
3. Show incoming motion/game/gaze data.
4. Show state transitions and PSI updates.
5. Send one doctor command.
6. End session.
7. Generate and display final report endpoint output.
