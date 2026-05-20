# Weather vs Taxi Trips

End-to-end data pipeline correlating NYC yellow taxi trip volume with daily weather conditions.

**Data sources:** NYC TLC Parquet files + Open-Meteo historical weather API  
**Stack:** PySpark · PostgreSQL · FastAPI · Chart.js · Docker Compose

## Architecture

See [docs/architecture/c4.md](docs/architecture/c4.md) for C4 Context and Container diagrams.

```
NYC TLC Parquet
Open-Meteo API   →  PySpark ETL  →  PostgreSQL  →  FastAPI  →  Browser (Chart.js)
```

## Quick start (dev)

```bash
docker compose up -d
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:8000/ |
| Swagger UI | http://localhost:8000/docs |
| Jupyter / PySpark | http://localhost:8888 |
| PostgreSQL | localhost:5432 |

## Run ETL

```bash
docker compose exec etl-runner /app/.venv/bin/python /app/main.py
```

## Run tests

```bash
# Unit tests + coverage
uv run pytest tests/unit/ -v --cov=src

# Performance tests (requires running API)
uv run locust -f tests/performance/locustfile.py --headless -u 50 -r 10 --run-time 60s --host http://localhost:8000
```

## Production

```bash
cp .env.example .env   # fill in credentials
docker compose -f docker-compose.prod.yml up -d
```

Prod exposes nginx on port 80. Frontend is served at `/`, API proxied at `/api/`.

## Project layout

```
src/
  ingest/      PySpark ETL — TLC Parquet + Open-Meteo API → staging tables
  transform/   PySpark aggregation — staging → analytics tables
  api/         FastAPI — reads analytics tables, exposes REST + Swagger
  db/          schema.sql — idempotent DDL
  frontend/    index.html — Chart.js dashboard
tests/
  unit/        pytest with mocked DB
  performance/ locust load tests
docs/
  architecture/  C4 diagrams (Mermaid)
  tech_choices.md
```
