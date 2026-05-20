# Implementation Plan — Weather vs Taxi Trips

Full data pipeline: NYC TLC taxi data + Open-Meteo weather → PostgreSQL DWH → FastAPI REST backend → HTML/JS frontend showing correlation charts.

## Grading targets (28/30 points mapped)

| Criterion | Pts | Phase |
|---|---|---|
| Layered architecture | 3 | Phase 1 |
| ≥2 data sources | 2 | Phase 2 |
| Key components (ingest, process, DB, API, UI) | 2 | All |
| C4/UML diagrams | 1 | Phase 8 |
| Full sensible pipeline | 3 | Phases 2–4 |
| Working REST API | 2 | Phase 4 |
| Working frontend | 2 | Phase 5 |
| Error handling & resilience | 1 | Phase 4 |
| Unit + performance tests | 2 | Phase 7 |
| Logging & debugging | 1 | Phase 2+ |
| Code readability & structure | 1 | All |
| Git history | 1 | All |
| Docker: dev + test + prod | 3 | Phase 1 ✅ |
| Architecture docs + responsibilities | 2 | Phase 8 |
| Swagger / API docs | 1 | Phase 4 (auto via FastAPI) |
| Tech choice justification | 1 | Phase 8 |

---

## Phase 1 — Project Structure & DB Schema ✅ DONE

- Reorganised repo into `src/ingest/`, `src/transform/`, `src/api/`, `src/db/`, `src/frontend/`, `tests/`
- `src/db/schema.sql` — idempotent DDL for `staging.*` and `analytics.*` tables
- Docker: `docker-compose.yml` (dev), `docker-compose.test.yml` (test), `docker-compose.prod.yml` (prod)
- `docker/Dockerfile.api`, `docker/Dockerfile.etl`, `docker/nginx.conf`
- `pyproject.toml` updated: added `fastapi`, `uvicorn`, dev group with `pytest`, `pytest-cov`, `httpx`, `locust`

---

## Phase 2 — Ingestion

Enhance `src/ingest/taxi_ingest.py` and `src/ingest/weather_ingest.py`:

- Parameterise date range (year/month args instead of hardcoded Jan 2023)
- Support multi-month ingestion loop
- Add structured logging (JSON formatter) throughout
- `requests` retry logic for weather API (backoff on 429/5xx)
- Validate response schema before writing to DB

---

## Phase 3 — PySpark Transform Pipeline

Implement `src/transform/pipeline.py`:

- Read `staging.fact_trip` → aggregate by date: `trip_count`, `avg_fare`, `avg_distance`, `avg_passengers` → write `analytics.daily_trips`
- Read `staging.fact_weather` → aggregate by date: `avg_temperature`, `total_precipitation`, `dominant_weathercode` → write `analytics.daily_weather`
- Join both on date → write `analytics.daily_correlation`
- Wire into `main.py` after ingestion

---

## Phase 4 — FastAPI Backend

Implement the stub routers in `src/api/routers/`:

- DB connection pool via `psycopg2` (module-level pool, closed on shutdown)
- `GET /api/trips/daily?start=&end=` → queries `analytics.daily_trips`
- `GET /api/weather/daily?start=&end=` → queries `analytics.daily_weather`
- `GET /api/correlation?start=&end=` → queries `analytics.daily_correlation`
- Global exception handler → JSON error responses (no raw 500 HTML)
- Swagger auto-generated at `/docs` (built into FastAPI)

---

## Phase 5 — Frontend

`src/frontend/index.html` + `src/frontend/static/app.js`:

- **Chart 1**: time series — trip count (line) + temperature (line, secondary axis) using Chart.js
- **Chart 2**: scatter plot — trips vs temperature per day
- **Chart 3**: bar chart — avg trips grouped by weather code (clear / rain / snow)
- Date range picker to re-fetch from `/api/correlation`
- Served by FastAPI `StaticFiles` in dev, nginx in prod

---

## Phase 6 — Docker Environments ✅ DONE (delivered in Phase 1)

| File | Environment | Key differences |
|---|---|---|
| `docker-compose.yml` | dev | hot-reload, Jupyter on :8888, hardcoded creds |
| `docker-compose.test.yml` | test | ephemeral DB, `test-runner` exits after pytest |
| `docker-compose.prod.yml` | prod | nginx, `.env` creds, `restart: always`, no Jupyter |

---

## Phase 7 — Tests

**Unit tests** (`tests/unit/`, pytest):
- `test_taxi_ingest.py` — mock Spark read, assert filter logic removes bad rows
- `test_weather_ingest.py` — mock `requests.get`, assert DataFrame columns/shape
- `test_pipeline.py` — small in-memory Spark DF fixtures, assert aggregation output
- `test_api.py` — FastAPI `TestClient`, assert endpoint shapes + error cases

**Performance tests** (`tests/performance/`, locust):
- `locustfile.py` — concurrent users hitting `GET /api/correlation`
- Target: p95 < 200 ms at 50 concurrent users

---

## Phase 8 — Documentation

- `docs/architecture/` — C4 Context + Container diagrams in Mermaid (renders in GitHub)
- `docs/tech_choices.md` — one paragraph per technology: Python/PySpark (Parquet scale), FastAPI (auto-Swagger), PostgreSQL (relational joins), Chart.js (zero-build frontend), Docker (reproducible environments)
- Update `README.md` with setup instructions and architecture overview
