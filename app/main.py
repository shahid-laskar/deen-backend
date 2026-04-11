"""
Deen — FastAPI Application (Full Product)
==========================================
V1: Auth, Prayer, Quran, Habits, Journal, Tasks, Female, AI
V2: Meal, Workout, Child, Recitation, Qibla, Cycle-sync
V3: Community, Waqf
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.routers import (
    auth, users, prayer, quran, habits, journal, tasks, female, ai,
    # V2
    meal, workout, child, recitation, qibla, cycle_sync,
    # V3
    community, waqf,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    print(f"✓ Database connected | ENV={settings.ENVIRONMENT}")
    yield
    await engine.dispose()
    print("✓ Database connection pool disposed")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Deen — Privacy-first Islamic lifestyle platform. "
        "Free forever. Multi-madhab. AI-powered wellness.\n\n"
        "V1: Prayer, Quran/Hifz, Habits, Journal, Tasks, AI Guide, Female Health\n"
        "V2: Meal Planner, Workout, Child Upbringing, Recitation AI, Qibla, Cycle-sync Ibadah\n"
        "V3: Community Forums, Waqf/Donations"
    ),
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# ─── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.is_development:
        raise exc
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


# ─── Routers ──────────────────────────────────────────────────────────────────

API = "/api/v1"

# V1 — MVP
app.include_router(auth.router, prefix=API)
app.include_router(users.router, prefix=API)
app.include_router(prayer.router, prefix=API)
app.include_router(quran.router, prefix=API)
app.include_router(habits.router, prefix=API)
app.include_router(journal.router, prefix=API)
app.include_router(tasks.router, prefix=API)
app.include_router(female.router, prefix=API)
app.include_router(ai.router, prefix=API)

# V2 — Full product
app.include_router(meal.router, prefix=API)
app.include_router(workout.router, prefix=API)
app.include_router(child.router, prefix=API)
app.include_router(recitation.router, prefix=API)
app.include_router(qibla.router, prefix=API)
app.include_router(cycle_sync.router, prefix=API)

# V3 — Community & Waqf
app.include_router(community.router, prefix=API)
app.include_router(waqf.router, prefix=API)


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["root"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API — Full Product",
        "docs": "/docs",
        "version": settings.APP_VERSION,
        "modules": {
            "v1": ["auth", "prayer", "quran", "habits", "journal", "tasks", "female", "ai"],
            "v2": ["meal", "workout", "children", "recitation", "qibla", "female/ibadah"],
            "v3": ["community", "waqf"],
        },
    }
