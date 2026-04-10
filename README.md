# Deen — Backend API

**Privacy-first Islamic lifestyle platform. Free forever.**

A production-grade FastAPI backend for the Deen app — a comprehensive Islamic lifestyle companion covering prayer tracking, Quran memorisation, habits, journaling, productivity planning, AI-guided wellness, and a full female health module with multi-madhab fiqh calculations.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local development with uv](#local-development-with-uv)
  - [Docker (recommended)](#docker-recommended)
- [Environment Variables](#environment-variables)
- [API Modules](#api-modules)
- [Repository Layer](#repository-layer)
- [Fiqh Engine](#fiqh-engine)
- [AI Guide](#ai-guide)
- [Security & Privacy](#security--privacy)
- [Database & Migrations](#database--migrations)
- [Testing](#testing)
- [Deployment](#deployment)
- [Makefile Reference](#makefile-reference)

---

## Overview

Deen is built on three core principles:

1. **Free forever** — no paywalls, no feature gates. Funded by optional waqf donations.
2. **Privacy first** — zero third-party analytics, no data selling. Female health data is AES-256 encrypted per-user at rest.
3. **Scholarly integrity** — the AI assistant never issues fatwas. A keyword-based intent classifier intercepts all fiqh/ruling questions before they reach the LLM and redirects to qualified scholarly resources.

---

## Architecture

```
HTTP Request
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  Router  (HTTP concerns: parsing, auth, responses)  │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  Service  (business logic: fiqh engine, SM-2, AI)   │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  Repository  (data access: all SQLAlchemy queries)  │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│  Database  (PostgreSQL 16 via asyncpg)              │
└─────────────────────────────────────────────────────┘
```

No code outside `app/repositories/` calls `db.execute()` or `db.add()` directly. This keeps routers thin, services pure, and data access testable in isolation.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 + Uvicorn |
| ORM | SQLAlchemy 2.0 (fully async) |
| Validation | Pydantic v2 |
| Migrations | Alembic |
| Database | PostgreSQL 16 (asyncpg driver) |
| Cache / Queue | Redis 7 (Upstash-compatible) |
| Auth | JWT (python-jose) — access 15 min, refresh 30 days |
| Encryption | Fernet AES-256 per-user keys (cryptography) |
| Passwords | bcrypt |
| AI (primary) | Gemini 2.0 Flash (free tier) |
| AI (fallback) | Groq llama-3.3-70b (free tier) |
| External APIs | Aladhan (prayer times), Quran.com v4 |
| Package manager | **uv** |
| Containerisation | Docker + Docker Compose |

---

## Project Structure

```
deen-backend/
├── app/
│   ├── main.py                    # FastAPI app, middleware, router registration
│   ├── core/
│   │   ├── config.py              # Settings (pydantic-settings, .env)
│   │   ├── database.py            # Async SQLAlchemy engine + session factory
│   │   ├── dependencies.py        # FastAPI deps: CurrentUser, DB, FemaleUser
│   │   └── security.py            # JWT, bcrypt, per-user AES-256 encryption
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── user.py                # User, UserProfile, RefreshToken
│   │   ├── prayer.py              # PrayerLog
│   │   ├── quran.py               # HifzProgress, DuaFavorite
│   │   ├── habit.py               # Habit, HabitLog
│   │   ├── journal.py             # JournalEntry
│   │   ├── task.py                # Task
│   │   ├── female.py              # MenstrualCycle, FastingLog
│   │   └── ai.py                  # AIConversation
│   ├── schemas/                   # Pydantic v2 request/response schemas
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── prayer.py
│   │   └── schemas.py             # All other schemas
│   ├── repositories/              # Data access layer (all DB queries live here)
│   │   ├── base.py                # Generic BaseRepository[T]
│   │   ├── user.py                # UserRepository
│   │   ├── prayer.py              # PrayerRepository
│   │   ├── quran.py               # HifzRepository, DuaFavoriteRepository
│   │   ├── habit.py               # HabitRepository, HabitLogRepository
│   │   ├── repos.py               # Journal, Task, Cycle, Fasting, AI repos
│   │   └── __init__.py            # DI factories + Annotated aliases
│   ├── routers/                   # HTTP route handlers (thin layer)
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── prayer.py
│   │   ├── quran.py
│   │   ├── habits.py
│   │   ├── journal.py
│   │   ├── tasks.py
│   │   ├── female.py
│   │   └── ai.py
│   └── services/                  # Business logic
│       ├── prayer_service.py      # Aladhan API, streak calculation
│       ├── quran_service.py       # Quran.com API, SM-2 algorithm
│       ├── ai_service.py          # Gemini/Groq, intent classifier
│       └── fiqh_engine/           # Multi-madhab hayd/tuhr calculations
│           ├── base.py            # Abstract BaseMadhab interface
│           ├── hanafi.py          # Hanafi rules (min 3d, max 10d, tuhr 15d)
│           └── madhabs.py         # Shafi'i, Maliki, Hanbali implementations
├── alembic/                       # Database migrations
├── tests/
│   ├── conftest.py                # Async fixtures, in-memory SQLite test DB
│   ├── routers/                   # Integration tests (full HTTP cycle)
│   ├── services/                  # Unit tests (fiqh engine, SM-2, security)
│   └── repositories/              # Data-layer unit tests (no HTTP)
├── Dockerfile                     # Multi-stage production image
├── Dockerfile.dev                 # Single-stage dev image with hot-reload
├── docker-compose.yml             # Postgres + Redis + API services
├── pyproject.toml                 # uv project file
└── Makefile                       # Common workflow shortcuts
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Docker + Docker Compose (for containerised setup)
- PostgreSQL 16 (local or Docker)

---

### Local development with uv

```bash
# 1. Clone and enter the project
cd deen-backend

# 2. Install all dependencies (creates .venv automatically)
uv sync --extra dev

# 3. Configure environment
cp .env.example .env
# Edit .env — at minimum set DATABASE_URL, SECRET_KEY, ENCRYPTION_MASTER_KEY

# 4. Generate secure keys
python -c "import secrets; print(secrets.token_hex(64))"  # SECRET_KEY
python -c "import secrets; print(secrets.token_hex(64))"  # ENCRYPTION_MASTER_KEY

# 5. Run migrations
uv run alembic upgrade head

# 6. Start the development server
uv run uvicorn app.main:app --reload --port 8000

# API docs available at:
# http://localhost:8000/docs   (Swagger UI)
# http://localhost:8000/redoc  (ReDoc)
```

---

### Docker (recommended)

**Development — hot-reload, source mounted as volume:**

```bash
cp .env.example .env    # fill in SECRET_KEY and ENCRYPTION_MASTER_KEY at minimum

# Start Postgres + Redis + API with hot-reload
make dev-up

# View logs
make logs-dev

# Open a shell inside the running container
make shell

# Connect to the database
make shell-db

# Stop everything
make down
```

**Production:**

```bash
make build    # builds the lean multi-stage image
make up       # starts db + redis + api
make logs     # tail logs
```

The `DATABASE_URL` and `REDIS_URL` in your `.env` are automatically overridden by Docker Compose to use the internal service hostnames (`db`, `redis`).

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values below. Variables marked **required** must be set before starting.

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://user:pass@host:5432/db` |
| `SECRET_KEY` | ✅ | 64-byte hex secret for JWT signing. Generate with `openssl rand -hex 64` |
| `ENCRYPTION_MASTER_KEY` | ✅ | 64-byte hex master key for per-user AES-256 encryption of female health data |
| `ENVIRONMENT` | — | `development` \| `staging` \| `production` (default: `development`) |
| `GEMINI_API_KEY` | — | Google Gemini 2.0 Flash API key (free tier). AI guide disabled without it |
| `GROQ_API_KEY` | — | Groq API key for fallback LLM (free tier) |
| `REDIS_URL` | — | Redis connection string (default: `redis://localhost:6379/0`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | JWT access token lifetime (default: `15`) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | — | JWT refresh token lifetime (default: `30`) |
| `AI_DAILY_LIMIT_PER_USER` | — | Max AI messages per user per day (default: `20`) |
| `ALLOWED_ORIGINS` | — | JSON array of CORS-allowed origins (default: `["http://localhost:5173"]`) |
| `POSTGRES_USER` | Docker only | Postgres username (default: `deen_user`) |
| `POSTGRES_PASSWORD` | Docker only | Postgres password (default: `deen_password`) |
| `POSTGRES_DB` | Docker only | Postgres database name (default: `deen_db`) |

---

## API Modules

All routes are prefixed with `/api/v1`. Interactive documentation is available at `/docs` in development.

### Auth — `/api/v1/auth`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/register` | Register new account. Returns access + refresh tokens |
| `POST` | `/login` | Login with email + password |
| `POST` | `/refresh` | Exchange refresh token for new access token |
| `POST` | `/logout` | Revoke refresh token |
| `GET` | `/me` | Get current authenticated user |

### Users — `/api/v1/users`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/me` | Get user with profile |
| `PATCH` | `/me` | Update user settings (madhab, gender, location, timezone) |
| `PATCH` | `/me/profile` | Update display name, goals, notification preferences |
| `POST` | `/me/change-password` | Change password (requires current password) |
| `DELETE` | `/me` | Permanently delete account and all data (GDPR) |

### Prayer — `/api/v1/prayer`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/times` | Prayer times for user's location and madhab (via Aladhan API) |
| `POST` | `/log` | Log a prayer (upserts — safe to call multiple times) |
| `GET` | `/log` | Get prayer logs for a date range |
| `GET` | `/summary/today` | Today's 5-prayer completion summary |
| `GET` | `/streak` | Current streak, longest streak, weekly completion % |
| `PATCH` | `/log/{id}` | Update a prayer log entry |
| `DELETE` | `/log/{id}` | Delete a prayer log entry |

### Quran — `/api/v1/quran`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/surahs` | List all 114 surahs with metadata |
| `GET` | `/surah/{number}` | Full surah with translation (via Quran.com API) |
| `GET` | `/ayah/{surah}/{ayah}` | Single ayah with translation and audio |
| `GET` | `/search?q=` | Keyword search across the Quran |
| `GET` | `/hifz` | All Hifz progress entries for the user |
| `GET` | `/hifz/due-today` | Entries due for SM-2 review today |
| `POST` | `/hifz` | Add surah/ayah range to Hifz tracker |
| `POST` | `/hifz/{id}/review` | Submit SM-2 review (quality 0–5) |
| `PATCH` | `/hifz/{id}` | Update a Hifz entry |
| `DELETE` | `/hifz/{id}` | Remove from Hifz tracker |
| `GET` | `/duas` | Dua library (filterable by category) |
| `GET` | `/duas/favorites` | User's saved duas |
| `POST` | `/duas/favorites` | Save a dua to favourites |
| `DELETE` | `/duas/favorites/{id}` | Remove from favourites |

### Habits — `/api/v1/habits`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | All habits with streak, completion rate, today's status |
| `POST` | `/` | Create a habit |
| `GET` | `/{id}` | Get habit with streak data |
| `PATCH` | `/{id}` | Update habit |
| `DELETE` | `/{id}` | Delete habit and all logs |
| `POST` | `/log` | Log a habit completion (upserts) |
| `GET` | `/{id}/logs` | Get habit logs for the last N days |

### Journal — `/api/v1/journal`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | List entries (filterable by date range, mood) |
| `POST` | `/` | Create entry (content, mood, gratitude, intentions, Quran ref) |
| `GET` | `/{id}` | Get a single entry |
| `PATCH` | `/{id}` | Update entry |
| `DELETE` | `/{id}` | Delete entry |

### Tasks / Planner — `/api/v1/tasks`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | List tasks (filterable by due date, priority, time block, completed) |
| `GET` | `/today` | Tasks due today, not yet completed |
| `POST` | `/` | Create task (with prayer-time block scheduling) |
| `GET` | `/{id}` | Get a task |
| `PATCH` | `/{id}` | Update task |
| `POST` | `/{id}/complete` | Mark task complete |
| `DELETE` | `/{id}` | Delete task |

### Female Module — `/api/v1/female`

> **Guarded:** All endpoints require `gender = female` on the user account. Returns `403` otherwise.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/cycles` | Menstrual cycle history |
| `POST` | `/cycles` | Start a new cycle (triggers fiqh engine calculation) |
| `GET` | `/cycles/current` | Active open cycle with worship gates |
| `GET` | `/cycles/{id}` | Get cycle with decrypted notes/symptoms |
| `PATCH` | `/cycles/{id}` | Update cycle (close it, mark ghusl, re-runs fiqh engine) |
| `DELETE` | `/cycles/{id}` | Delete cycle |
| `GET` | `/fasting` | Fasting log (filterable by year, type) |
| `POST` | `/fasting` | Log a fast (Ramadan, Qadha, voluntary) |
| `PATCH` | `/fasting/{id}` | Update fast (mark fidya paid, kaffarah done) |
| `GET` | `/fasting/missed-summary` | Missed fasts, qadha count, fidya owed for a year |

### AI Guide — `/api/v1/ai`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Send a message to the AI guide |
| `GET` | `/conversations` | List conversation threads |
| `GET` | `/conversations/{id}` | Get a conversation with full message history |
| `DELETE` | `/conversations/{id}` | Archive a conversation |
| `GET` | `/usage` | Today's message count and remaining limit |

---

## Repository Layer

The repository pattern enforces a strict separation between data access and business logic. Nothing outside `app/repositories/` touches the database session directly.

### BaseRepository[T]

All repositories inherit from `BaseRepository` and get these methods for free:

```python
# Core CRUD
await repo.get(id)                          # → Model | None
await repo.get_or_404(id)                   # → Model | raises 404
await repo.get_owned_or_404(id, user_id)    # → Model | raises 404 (ownership guard)
await repo.list(stmt=..., limit=..., offset=...)
await repo.count(stmt=...)
await repo.create(**kwargs)                 # → Model
await repo.update(obj, **kwargs)            # → Model
await repo.update_by_id(id, **kwargs)       # → Model
await repo.delete(obj)
await repo.delete_by_id(id)
await repo.exists(stmt)                     # → bool
```

### Using repositories in routes

Import the `Annotated` type alias from `app.repositories` and declare it as a dependency:

```python
from app.repositories import UserRepo, PrayerRepo

@router.get("/summary")
async def summary(
    current_user: CurrentUser,
    db: DB,
    user_repo: UserRepo,
    prayer_repo: PrayerRepo,
):
    user = await user_repo.get_with_profile_or_404(current_user.id)
    logs  = await prayer_repo.get_today(current_user.id)
    ...
```

FastAPI resolves `UserRepo` → `UserRepository(db)` automatically, scoped to the request.

### Adding a new repository

```python
# app/repositories/my_model.py
from app.models.my_model import MyModel
from app.repositories.base import BaseRepository

class MyModelRepository(BaseRepository[MyModel]):
    model = MyModel

    async def get_by_some_field(self, value: str) -> MyModel | None:
        result = await self.db.execute(
            select(MyModel).where(MyModel.some_field == value)
        )
        return result.scalar_one_or_none()
```

Then register it in `app/repositories/__init__.py`:

```python
from app.repositories.my_model import MyModelRepository

def get_my_model_repo(db: DB) -> MyModelRepository:
    return MyModelRepository(db)

MyModelRepo = Annotated[MyModelRepository, Depends(get_my_model_repo)]
```

---

## Fiqh Engine

The fiqh engine classifies menstrual cycles according to the user's chosen school of thought. It is **stateless** — it receives cycle data and returns a `FiqhRuling` dataclass.

### Architecture

```
classify_cycle(madhab, CycleInput)
    │
    ├── get_fiqh_engine("hanafi")  → HanafiEngine
    ├── get_fiqh_engine("shafii")  → ShafiEngine
    ├── get_fiqh_engine("maliki")  → MalikiEngine
    └── get_fiqh_engine("hanbali") → HanbaliEngine
            │
            ▼
        BaseMadhab.classify_cycle(CycleInput) → FiqhRuling
```

### Madhab rules summary

| Madhab | Hayd min | Hayd max | Tuhr min |
|---|---|---|---|
| Hanafi | 3 days | 10 days | 15 days |
| Shafi'i | 1 day | 15 days | 15 days |
| Maliki | 1 day | 15 days | 15 days |
| Hanbali | 1 day | 15 days | **13 days** |

### FiqhRuling output

```python
@dataclass
class FiqhRuling:
    classification: str      # "hayd" | "istihadah" | "tuhr"
    madhab: str
    can_pray: bool
    can_fast: bool
    can_read_quran: bool     # touching mushaf — scholarly difference applies
    ghusl_required: bool
    ruling_summary: str      # human-readable explanation
    notes: list[str]         # guidance points + referral note
    confidence: str          # "certain" | "probable" | "consult_scholar"
```

### Adding a new madhab

Create a file in `app/services/fiqh_engine/`, subclass `BaseMadhab`, implement `classify_cycle`, and register it in `app/services/fiqh_engine/__init__.py`:

```python
_REGISTRY["new_madhab"] = NewMadhabEngine()
```

No router or service changes required.

---

## AI Guide

### Boundary enforcement

The AI assistant is lifestyle-only. A keyword-based intent classifier runs **before every LLM call** at zero cost:

```
User message
    │
    ▼
is_fiqh_question(message)?
    │
    ├── YES → build_referral_response(madhab)
    │          Returns scholar links, no LLM call made
    │
    └── NO  → generate_ai_reply(message, history, user_context)
               Gemini 2.0 Flash → Groq fallback
```

Detected fiqh keywords include: `ruling`, `fatwa`, `is it haram`, `is it halal`, `is it permissible`, `what is the ruling`, and similar phrases.

### System prompt design

The system prompt:
- Confines the AI to habits, productivity, Quran revision, wellness, and motivation
- Passes the user's madhab for culturally appropriate framing
- Passes the female user's current cycle status (if active) for cycle-aware advice
- Explicitly prohibits issuing fatwas or reinterpreting scholarly positions

### Free tier sustainability

Daily message limits (`AI_DAILY_LIMIT_PER_USER`, default 20) are enforced per user per day. Gemini 2.0 Flash free tier allows 1,500 requests/day. Groq free tier is generous for burst load. Together they support hundreds of daily active users with zero infrastructure cost.

---

## Security & Privacy

### JWT authentication

- Access tokens expire in 15 minutes (configurable)
- Refresh tokens expire in 30 days, stored as SHA-256 hashes — never in plaintext
- Single-session policy: logging in revokes all existing refresh tokens
- `401` is returned for expired/invalid tokens; `403` for active but unauthorised users

### Female health data encryption

Notes and symptoms in `MenstrualCycle` are encrypted at rest using per-user Fernet keys derived from the master key via HMAC-SHA256:

```
user_key = HMAC-SHA256(ENCRYPTION_MASTER_KEY, user_id)
ciphertext = Fernet(base64url(user_key)).encrypt(plaintext)
```

Even if the database is compromised, individual user data cannot be decrypted without the master key. Even if the master key is known, one user's key cannot decrypt another user's data.

### GDPR compliance

`DELETE /api/v1/users/me` hard-deletes the user and all related data via SQLAlchemy cascade rules. No soft-deletes, no lingering records.

---

## Database & Migrations

Alembic is configured for async SQLAlchemy. The `env.py` auto-discovers all models via `app/models/__init__.py`.

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Create a new migration (autogenerate from model changes)
uv run alembic revision --autogenerate -m "add notifications table"

# Or with make:
make migrate
make migrate-new msg="add notifications table"

# Roll back one migration
make migrate-down

# Show history
make migrate-history
```

Always review autogenerated migrations before applying — Alembic does not detect all column changes (e.g. type changes) perfectly.

---

## Testing

The test suite has 140 tests across three layers:

```
tests/
├── routers/       # Integration: full HTTP cycle, real SQLite DB
│   ├── test_auth.py          (15 tests)
│   ├── test_prayer.py        (7 tests)
│   └── test_features.py      (30 tests — habits, journal, tasks, female)
├── services/      # Unit: pure logic, no HTTP, no DB
│   ├── test_fiqh_engine.py   (35 tests — all 4 madhabs + factory)
│   └── test_services.py      (36 tests — SM-2, bcrypt, JWT, encryption, AI intent)
└── repositories/  # Unit: data layer, real SQLite DB, no HTTP
    └── test_repositories.py  (23 tests)
```

```bash
# Run everything
uv run pytest tests/ -v

# With make
make test

# With coverage
make test-cov

# Single test file
uv run pytest tests/services/test_fiqh_engine.py -v

# Single test
uv run pytest tests/repositories/test_repositories.py::TestPrayerRepository::test_upsert_updates_existing -v
```

The test database uses SQLite in-memory (via `aiosqlite`). Each test function gets a fresh schema — no state leaks between tests.

---

## Deployment

### Railway (recommended free tier)

1. Connect your GitHub repo to Railway
2. Add a PostgreSQL plugin
3. Set all environment variables in the Railway dashboard
4. Railway will detect the `Dockerfile` and build automatically
5. Migrations run automatically on container start (`alembic upgrade head` in the `CMD`)

### Render

1. Create a new Web Service, connect your repo
2. Set Build Command: `docker build -t deen .`
3. Set Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add a PostgreSQL instance and set `DATABASE_URL`
5. Add environment variables

### VPS / self-hosted

```bash
git clone <your-repo>
cd deen-backend
cp .env.example .env          # fill in production values
make build                    # builds the production Docker image
make up                       # starts postgres + redis + api
```

### Production checklist

- [ ] `ENVIRONMENT=production` (disables Swagger docs at `/docs`)
- [ ] `SECRET_KEY` is a cryptographically random 64-byte hex string
- [ ] `ENCRYPTION_MASTER_KEY` is a different 64-byte hex string — back it up securely
- [ ] `DATABASE_URL` points to a persistent PostgreSQL instance with backups enabled
- [ ] HTTPS is terminated at your reverse proxy (nginx / Cloudflare) — never run HTTP in production
- [ ] `ALLOWED_ORIGINS` is set to your production frontend domain only
- [ ] Remove the `ports` entries for `db` and `redis` in `docker-compose.yml` (not needed in production)

---

## Makefile Reference

```
make help           Show all available commands

# Local (uv)
make install        Install all dependencies
make install-dev    Install with dev extras
make dev            Run hot-reload dev server locally
make test           Run test suite
make test-cov       Run tests with coverage report
make lint           Ruff linting
make format         Black + Ruff format

# Alembic
make migrate        Apply all pending migrations
make migrate-new    Create new migration (msg="description")
make migrate-down   Roll back one migration
make migrate-history Show migration history

# Docker
make build          Build production image
make build-dev      Build dev image
make up             Start all services (production)
make dev-up         Start all services with hot-reload
make down           Stop all services
make down-v         Stop and remove volumes (DESTROYS DATA)
make logs           Tail API logs
make logs-dev       Tail dev API logs
make ps             Show service status
make shell          Open shell in API container
make shell-db       Open psql in DB container
make restart        Restart the API service
```

---

## Contributing

This project is open-source under the MIT licence. Contributions are welcome, especially:

- Additional madhab fiqh rules (verified by scholars)
- More duas in the library
- Translations (i18next JSON files)
- v2 modules: meal planning, workout planner, child milestone tracker

For fiqh-related contributions, please cite your scholarly references in the PR description.

---

*Deen is a waqf project — built as a public good for the Muslim community. If it benefits you, please make dua for the team. If you'd like to support hosting costs, an optional donation page is planned for v3.*