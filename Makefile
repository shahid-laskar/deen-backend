# ─── Deen Backend — Makefile ──────────────────────────────────────────────────
# Usage: make <target>

.PHONY: help install dev test lint format migrate shell build up down logs

help:              ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ─── Local Development (uv) ───────────────────────────────────────────────────

install:           ## Install all dependencies with uv
	uv sync

install-dev:       ## Install with dev extras
	uv sync --extra dev

dev:               ## Run dev server locally (no Docker)
	uv run alembic upgrade head
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:              ## Run test suite
	uv run pytest tests/ -v

test-cov:          ## Run tests with coverage report
	uv run pytest tests/ -v --cov=app --cov-report=term-missing

lint:              ## Lint with ruff
	uv run ruff check app/ tests/

format:            ## Format with black + ruff
	uv run black app/ tests/
	uv run ruff check --fix app/ tests/

# ─── Database / Alembic ───────────────────────────────────────────────────────

migrate:           ## Run all pending migrations
	uv run alembic upgrade head

migrate-new:       ## Create a new migration (usage: make migrate-new msg="add users table")
	uv run alembic revision --autogenerate -m "$(msg)"

migrate-down:      ## Roll back one migration
	uv run alembic downgrade -1

migrate-history:   ## Show migration history
	uv run alembic history --verbose

# ─── Docker ───────────────────────────────────────────────────────────────────

build:             ## Build production Docker image
	docker compose build api

build-dev:         ## Build dev Docker image
	docker compose build api-dev

up:                ## Start all services (production mode)
	docker compose up -d db redis api

dev-up:            ## Start all services with hot-reload
	docker compose --profile dev up -d db redis api-dev

down:              ## Stop all services
	docker compose down

down-v:            ## Stop and remove volumes (DESTROYS DATA)
	docker compose down -v

logs:              ## Tail API logs
	docker compose logs -f api

logs-dev:          ## Tail dev API logs
	docker compose logs -f api-dev

ps:                ## Show service status
	docker compose ps

shell:             ## Open shell in running api container
	docker compose exec api sh

shell-db:          ## Open psql in running db container
	docker compose exec db psql -U $${POSTGRES_USER:-deen_user} $${POSTGRES_DB:-deen_db}

restart:           ## Restart the api service
	docker compose restart api
