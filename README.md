# NYC Weather vs Taxi Trips

An end-to-end data engineering project that correlates NYC yellow taxi trip volume with daily weather conditions. Raw data is ingested from two public sources, aggregated in a PostgreSQL data warehouse, and exposed through a REST API with an interactive dashboard.

**Data sources:** NYC TLC yellow taxi trip records (Parquet) · Open-Meteo historical weather API  
**Stack:** PySpark · PostgreSQL · FastAPI · Chart.js · Docker Compose

## Architecture

```
NYC TLC Parquet  ─┐
                   ├─▶  PySpark ETL  ─▶  PostgreSQL DWH  ─▶  FastAPI  ─▶  Browser (Chart.js)
Open-Meteo API  ──┘
                        staging.*            analytics.*
```

The pipeline runs in two phases:

1. **Ingest** — downloads TLC Parquet files and Open-Meteo API responses to `/tmp`, loads raw records into `staging.fact_trip` and `staging.fact_weather`
2. **Transform** — aggregates staging data into `analytics.daily_trips`, `analytics.daily_weather`, and `analytics.daily_correlation`

See [docs/architecture/c4.md](docs/architecture/c4.md) for C4 Context and Container diagrams.

## Quick start

```bash
docker compose up -d
```

| Service | URL |
|---------|-----|
| Frontend / Dashboard | http://localhost:8000/ |
| REST API (Swagger UI) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

## Running the ETL

With the stack running, execute ingestion inside the ETL container:

```bash
docker compose exec etl-runner uv run python main.py --year 2023 --start-month 1 --end-month 1
```

Arguments:

| Flag | Default | Description |
|------|---------|-------------|
| `--year` | `2023` | Calendar year to ingest |
| `--start-month` | `1` | First month (inclusive) |
| `--end-month` | `1` | Last month (inclusive) |

> **Note:** the first month is written with `mode=overwrite`; subsequent months append. Re-running a partial range will duplicate data — always re-run the full range.

## Running tests

```bash
# Unit tests (no DB required)
uv run pytest tests/unit/ -v

# With coverage report
uv run pytest tests/unit/ -v --cov=src --cov-fail-under=70

# Performance / load tests (requires running API)
uv run locust -f tests/performance/locustfile.py --headless -u 50 -r 10 --run-time 60s --host http://localhost:8000
```

Docker alternative

```bash
docker compose -f docker-compose.test.yml run --rm test-runner
```


## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/trips/daily` | Daily trip aggregates |
| `GET` | `/api/weather/daily` | Daily weather aggregates |
| `GET` | `/api/correlation/` | Joined trips + weather |
| `GET` | `/api/health` | Health check |

All list endpoints accept optional `start` and `end` query params (ISO date, e.g. `?start=2023-01-01&end=2023-01-31`).

## Production deployment

```bash
cp .env.example .env   # fill in credentials
docker compose -f docker-compose.prod.yml up -d
```

| Service | URL |
|---------|-----|
| Frontend / Dashboard | http://localhost:8082/ |
| REST API (Swagger UI) | http://localhost:8082/docs |

nginx proxies `/api/` to FastAPI and serves the frontend at `/`. The API port (8000) is not exposed directly in prod.

### Running the ETL in production

```bash
docker compose -f docker-compose.prod.yml exec etl-runner \
  uv run python main.py --year 2023 --start-month 1 --end-month 1
```

### Fresh start / reset

```bash
docker compose -f docker-compose.prod.yml down -v   # removes containers and pgdata_prod volume
docker compose -f docker-compose.prod.yml up -d
```

## Project layout

```
src/
  ingest/      PySpark ETL — downloads TLC Parquet + Open-Meteo API → staging tables
  transform/   PySpark aggregation — staging → analytics tables
  api/         FastAPI — REST endpoints + Swagger, reads analytics tables
    routers/   trips.py · weather.py · correlation.py
    models.py  Pydantic response schemas
  db/          schema.sql — idempotent DDL for all tables
  frontend/    index.html — single-file Chart.js dashboard (no build step)
tests/
  unit/        pytest, mocked DB via make_get_conn() — no real DB needed
  performance/ locust load tests
docker/
  Dockerfile.api   python:3.13-slim + uv
  Dockerfile.etl   python:3.12-slim + JRE + uv
  nginx.conf       reverse proxy config for prod
docs/
  architecture/    C4 diagrams (Mermaid)
  tech_choices.md  Design rationale
```
