# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

- In all interactions and commit messages, be extremely concise and sacrifice grammar for the sake of concision.

## Project Overview

End-to-end data pipeline: NYC TLC yellow taxi trip records (Parquet) + Open-Meteo weather API → PostgreSQL DWH → FastAPI REST backend → HTML/JS frontend showing weather/trip correlation.

## Architecture

```
src/
  ingest/          # Phase 2 — PySpark ETL: TLC Parquet + Open-Meteo API → staging tables
  transform/       # Phase 3 — PySpark aggregation: staging → analytics tables
  api/             # Phase 4 — FastAPI: reads analytics tables, exposes REST + Swagger
    routers/       # trips.py, weather.py, correlation.py
  db/              # schema.sql — idempotent DDL for all tables
  frontend/        # Phase 5 — HTML/JS (Chart.js) served by nginx in prod
tests/
  unit/            # pytest
  performance/     # locust
docker/
  Dockerfile.api   # python:3.13-slim + uv
  Dockerfile.etl   # jupyter/pyspark-notebook base
  nginx.conf       # reverse proxy for prod
```

**DB schemas:**
- `staging.fact_trip` / `staging.fact_weather` — raw data, overwritten by each PySpark run
- `analytics.daily_trips` / `analytics.daily_weather` / `analytics.daily_correlation` — aggregated, read by API

## Commands

```bash
# Install / update dependencies
uv sync              # all deps (runtime + dev)
uv sync --no-dev     # runtime only

# Run tests
uv run pytest tests/unit/ -v --cov=src
uv run pytest tests/unit/test_foo.py::test_name -v   # single test
uv run locust -f tests/performance/locustfile.py      # load test (needs API running)

# Start API locally (needs postgres running)
uv run uvicorn src.api.main:app --reload
# Swagger UI: http://localhost:8000/docs

# Docker environments
docker compose up -d                                  # dev  (Jupyter :8888, API :8000, PG :5432)
docker compose -f docker-compose.test.yml up --abort-on-container-exit   # test
docker compose -f docker-compose.prod.yml up -d       # prod (nginx :80, no Jupyter)

# Run ingestion inside ETL container
docker compose exec etl-runner /app/.venv/bin/python /app/main.py
```

## Env Vars

Two separate sets — `.env.example` only documents compose service vars, not these:

| Component | Vars |
|-----------|------|
| API (`src/api/db.py`) | `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (default to localhost dev) |
| ETL (`src/ingest/`, `src/transform/`) | `DB_URL` (full JDBC string), `DB_USER`, `DB_PASSWORD` |

## Key Constraints

- **Spark session** is created in `main.py` and passed into ingest/transform functions — never module-level.
- **JDBC table names** use schema-qualified form: `staging.fact_trip`, `analytics.daily_correlation`, etc.
- **JDBC writes** use `mode="overwrite"` for staging (full reload). Analytics tables use `overwrite` too until incremental loads are added.
- **JDBC driver JAR** expected at `/home/jovyan/work/postgresql-42.6.0.jar` inside the ETL container.
- **prod credentials** come from a `.env` file (see `docker-compose.prod.yml`); dev uses hardcoded values.
- `db-init` service runs `schema.sql` once on `docker compose up`; it depends on `postgres-dwh` being healthy.
- **Ingest overwrite/append**: `main.py` writes first month with `mode="overwrite"`, subsequent months with `"append"`. Re-running the same range is idempotent only if the full range is identical; partial re-runs will duplicate data.
- **Tests**: `conftest.py` patches `init_pool`/`close_pool` globally; inject fake DB rows via `make_get_conn()` — no real DB needed for unit tests.
- **No linting config**: `pyproject.toml` only has `[tool.pytest.ini_options]`; no ruff/black/pylint rules configured.
- **CORS**: API allows all origins (`allow_origins=["*"]`) — intentional for dev/demo.
