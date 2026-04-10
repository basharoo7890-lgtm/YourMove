# YourMove Server

VR Assessment & Support Platform for ASD/ADHD — Backend + Dashboard

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Run server
uvicorn main:app --reload --port 8000

# 3. Open browser
# http://localhost:8000
```

## Testing without VR

```bash
# Terminal 1: Server
uvicorn main:app --reload --port 8000

# Terminal 2: Simulator (auto session)
python simulator.py --auto

# Terminal 2: Simulator (stress scenario)
python simulator.py --auto --stress

# Terminal 2: Simulator (interactive)
python simulator.py
# Commands: c=calm, e=engaged, s=stressed, o=overwhelmed
#           t 20 = send 20 data points
#           b = start baseline, bend = end baseline
#           end = end session, q = quit

# Terminal 3 (optional): E2E tests
python run_e2e.py
```

## Flow

1. Open `http://localhost:8000` → Register → Login
2. Add patient → copy Access Key (YM-XXXX)
3. Run simulator (or start from UE5)
4. Open `/session/{id}` to watch live data

## Structure

```
yourmove-server/
├── .env.example
├── DEPLOY_KOYEB_STEPS_EN.md
├── TECHNICAL_DEFENSE_GUIDE_EN.md
├── main.py
├── simulator.py
├── run_e2e.py
├── tests/
│   ├── test_e2e.py
│   ├── test_unit_ml_classifier.py
│   ├── test_unit_ml_statistical.py
│   ├── test_unit_patient_schema.py
│   └── test_unit_recommendation_service.py
└── app/
    ├── api/
    ├── core/
    ├── models/
    │   ├── auth.py
    │   ├── patient.py
    │   ├── session.py
    │   ├── events.py
    │   ├── ml.py
    │   └── system.py
    ├── schemas/
    │   ├── auth.py
    │   ├── patient.py
    │   ├── session.py
    │   └── websocket.py
    ├── repositories/
    ├── services/
    ├── ml/
    └── websocket/
```

## Database note

- Default local setup uses SQLite for quick start.
- A PostgreSQL DSN template is provided as `POSTGRES_DATABASE_URL` in `app/core/config.py`.

## AI Final Report

- Generate final report: `POST /api/sessions/{session_id}/report`
- Get latest report: `GET /api/sessions/{session_id}/report`
- Recommendation endpoint: `GET /api/sessions/{session_id}/recommendations`
- Gemini is optional: set `GOOGLE_API_KEY` in `.env` to enable Gemini-backed report generation.
- If Gemini is unavailable, the system uses a local free fallback report generator.
