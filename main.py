import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import configure_logging
from app.api.auth import router as auth_router
from app.api.patients import router as patients_router
from app.api.sessions import router as sessions_router
from app.api.websocket import router as ws_router

configure_logging()

STATIC_DIR = os.path.join(os.path.dirname(__file__), "app", "static")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logging.getLogger("yourmove").info("Database initialized — YourMove Server ready")
    yield


app = FastAPI(
    title="YourMove API",
    version="0.1.0",
    description="VR Assessment & Support Platform for ASD/ADHD",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(sessions_router)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "yourmove"}


@app.get("/ready")
async def ready():
    """Readiness check — verifies DB connectivity."""
    from app.core.database import async_session
    from sqlalchemy import text
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "not_ready", "db": str(e)})


# ─── Page Routes (serve HTML) ─────────────────────────

@app.get("/")
async def index():
    return RedirectResponse("/dashboard")


@app.get("/login")
async def login_page():
    return FileResponse(os.path.join(STATIC_DIR, "login.html"))


@app.get("/dashboard")
async def dashboard_page():
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))


@app.get("/patients")
async def patients_page():
    return FileResponse(os.path.join(STATIC_DIR, "patients.html"))


@app.get("/sessions")
async def sessions_page():
    return FileResponse(os.path.join(STATIC_DIR, "sessions.html"))


@app.get("/profile")
async def profile_page():
    return FileResponse(os.path.join(STATIC_DIR, "profile.html"))


@app.get("/session/{session_id}")
async def session_page(session_id: int):
    return FileResponse(os.path.join(STATIC_DIR, "session.html"))


# Static files (CSS, JS)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
