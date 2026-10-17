"""
CivicFix FastAPI Application
Entry point: uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base

# Import all models so SQLAlchemy sees them before create_all
import app.models  # noqa: F401

# Import routers
from app.routers import auth, issues, public, track, bot, notifications, admin, worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (no migrations for hackathon)
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables verified / created.")
    yield
    # Nothing to teardown


app = FastAPI(
    title="CivicFix API",
    description="Backend for the CivicFix civic issue reporting platform.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,          prefix="/api/auth",          tags=["auth"])
app.include_router(issues.router,        prefix="/api/issues",        tags=["issues"])
app.include_router(public.router,        prefix="/api/public",        tags=["public"])
app.include_router(track.router,         prefix="/api",               tags=["track"])
app.include_router(bot.router,           prefix="/api/bot",           tags=["bot"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(admin.router,         prefix="/api/admin",         tags=["admin"])
app.include_router(worker.router,        prefix="/api/worker",        tags=["worker"])
