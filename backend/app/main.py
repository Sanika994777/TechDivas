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
from app.routers import auth, issues, public, track, bot, notifications, admin, worker, geo


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
# Collect allowed origins from settings
allowed_origins: list[str] = [
    origin.strip().rstrip("/")
    for origin in settings.FRONTEND_URL.split(",")
    if origin.strip()
]

# Ensure standard local development and deployed frontend origins are present
default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://tech-divas-xi.vercel.app",
]
for origin in default_origins:
    if origin not in allowed_origins:
        allowed_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://.*",
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
app.include_router(geo.router,           prefix="/api/geo",           tags=["geo"])

