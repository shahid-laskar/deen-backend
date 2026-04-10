# ─── Stage 1: Build dependencies with uv ─────────────────────────────────────
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first (layer cache)
COPY pyproject.toml uv.lock* requirements.txt* ./

# Install dependencies into a virtual environment
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python \
    fastapi uvicorn[standard] sqlalchemy asyncpg alembic \
    "pydantic[email]" pydantic-settings \
    "python-jose[cryptography]" bcrypt cryptography \
    httpx python-dateutil pytz python-multipart \
    google-generativeai groq

# ─── Stage 2: Runtime image ───────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Install system deps needed at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (for migrations via uv run alembic)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

WORKDIR /app

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY . .

# Activate venv by prepending to PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Non-root user for security
RUN useradd -m -u 1000 deen && chown -R deen:deen /app
USER deen

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run migrations then start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]
