# Component Build Report

How the four major components were built, with references to the code that implements each decision.

---

## 1. Database

**File:** `src/db/schema.sql`

Two PostgreSQL schemas isolate concerns:

- `staging.*` — raw data written by PySpark JDBC. No primary keys; Spark's `mode=overwrite` drops and recreates the table on each full reload, so constraints would just add friction.
- `analytics.*` — aggregated daily tables consumed by the API. Each has a `DATE PRIMARY KEY` and a B-tree index on that date column (e.g. `idx_daily_trips_date`), which makes the API's optional `?start=`/`?end=` range queries efficient.

Three analytics tables:

| Table | Primary key | Written by |
|---|---|---|
| `analytics.daily_trips` | `trip_date` | `run_pipeline()` |
| `analytics.daily_weather` | `weather_date` | `run_pipeline()` |
| `analytics.daily_correlation` | `record_date` | `run_pipeline()` |

Schema is idempotent (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`) — safe to re-run. In Docker Compose, the `db-init` service runs `psql … -f /schema.sql` against the live database before the API starts (`depends_on: db-init: condition: service_completed_successfully` in `docker-compose.yml:66`).

---

## 2. ETL

Entry point: `main.py`. Three modules under `src/ingest/` and `src/transform/`.

### Spark session

`main.py:18–23` builds a single `SparkSession` with the PostgreSQL JDBC driver loaded via Maven (`spark.jars.packages = org.postgresql:postgresql:42.6.0`). The session is shared across all ingest and transform calls, then stopped in `finally`.

### TLC taxi ingest — `src/ingest/taxi_ingest.py`

1. Downloads a monthly Parquet file from the TLC CloudFront CDN to `/tmp` using a streaming `requests.get` (1 MB chunks, 120 s timeout) — `taxi_ingest.py:25–30`.
2. Reads it with `spark.read.parquet(local_path)`.
3. Filters rows where `total_amount > 0 AND trip_distance > 0 AND passenger_count > 0` — `taxi_ingest.py:36–40`. This removes nulls, free rides, and zero-distance records before loading.
4. Writes to `staging.fact_trip` via JDBC — `taxi_ingest.py:45–51`.
5. Deletes the local Parquet in `finally` — `taxi_ingest.py:52`.

### Weather ingest — `src/ingest/weather_ingest.py`

1. Builds a `requests.Session` with `urllib3.Retry` (3 retries, exponential backoff, retries on 429/5xx) — `weather_ingest.py:29–38`. No equivalent retry in the taxi path because the TLC CDN is more reliable than the Open-Meteo API.
2. Fetches hourly JSON from `archive-api.open-meteo.com` for NYC (lat 40.7128, lon -74.0060) — `weather_ingest.py:13–18`.
3. Validates the response shape (`_validate_response`) before touching the data — `weather_ingest.py:41–46`.
4. Converts hourly JSON to a Pandas DataFrame, serialises it to a local Parquet, then reads that Parquet into Spark — `weather_ingest.py:63–78`. This avoids creating a Spark DataFrame directly from a Python dict, which requires the Spark driver to hold all data in memory.
5. Writes to `staging.fact_weather` via JDBC, then deletes the local file in `finally`.

### Write mode per month

`main.py:41–44`: the first month in the requested range uses `mode="overwrite"` (truncates staging); subsequent months use `mode="append"`. This means re-running a partial range (e.g. month 2 alone, after a full 1–3 run) will duplicate data — always re-run the full range.

### Transform pipeline — `src/transform/pipeline.py`

Called once after all months are ingested (`main.py:46`). Steps:

1. Reads `staging.fact_trip` and `staging.fact_weather` via JDBC.
2. Aggregates trips per day: `trip_count`, `avg_fare`, `avg_distance`, `avg_passengers` — `pipeline.py:28–38`.
3. Aggregates weather per day: `avg_temperature`, `total_precipitation`, and **dominant weathercode** — the WMO weathercode that appears most often in the 24 hourly rows for that day, computed via a `row_number()` window function — `pipeline.py:43–57`.
4. Joins trips and weather on date to produce `daily_correlation` — `pipeline.py:71–83`.
5. Writes all three analytics tables with `mode="overwrite"` (transform always rebuilds from staging) — `pipeline.py:87–93`.

### Logging

`src/ingest/logging_config.py` installs a `JsonFormatter` on the root logger before Spark is imported (`main.py:6–7`, before the `pyspark` import on line 9). Every log call in the ingest and transform modules passes structured fields via `extra={}`, producing machine-readable JSON lines suitable for log aggregation.

### Containers

`docker/Dockerfile.etl` uses `python:3.12-slim` + `default-jre-headless` (required by PySpark). Dependencies are installed via `uv sync --frozen` with the uv layer cached via `--mount=type=cache`. The container's default CMD is `tail -f /dev/null` — the ETL is run on demand with `docker compose exec etl-runner uv run python main.py …`, not as an always-on service.

---

## 3. API

**Root:** `src/api/`

### App setup — `src/api/main.py`

FastAPI app with a `lifespan` context manager that calls `init_pool()` on startup and `close_pool()` on shutdown — `main.py:17–21`. This ensures the connection pool exists before any request is served and is cleanly released on process exit.

Three routers registered: `trips_router`, `weather_router`, `correlation_router`. A global exception handler catches any unhandled exception and returns a `500` JSON response with the error string — `main.py:43–46`.

The frontend is served as a `FileResponse` at `/` and static files are mounted at `/static` — `main.py:54–59`. No separate web server in dev; nginx handles this in prod.

### Connection pool — `src/api/db.py`

`psycopg2.ThreadedConnectionPool` with `minconn=2 / maxconn=10` — `db.py:10–19`. The `get_conn()` context manager borrows a connection from the pool and returns it on exit — `db.py:27–33`. Every router calls `get_conn()` as a context manager; there is no global connection state.

All connection parameters come from env vars (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`) with defaults pointing to the Docker service name `postgres-dwh`.

### Routers — `src/api/routers/`

All three routers (`trips.py`, `weather.py`, `correlation.py`) follow the same pattern:

1. Accept optional `start: date | None` and `end: date | None` query params.
2. Build a parameterised SQL string with `%s` placeholders (no f-string interpolation — no SQL injection risk).
3. Execute against `analytics.*` via `get_conn()`.
4. Zip column names from `cur.description` with row values and construct Pydantic model instances.

The routers read only from `analytics.*` — they never touch `staging.*`.

### Response models — `src/api/models.py`

Three Pydantic `BaseModel` classes (`DailyTrips`, `DailyWeather`, `DailyCorrelation`) typed with `date`, `int`, and `float`. FastAPI uses these as `response_model=` on each endpoint, which: (a) validates the shape before sending, (b) generates the OpenAPI schema automatically visible at `/docs`.

### Containers

`docker/Dockerfile.api` uses `python:3.13-slim` — no JVM. The dev compose command adds `--reload` so code changes in the volume-mounted `./src` are picked up without rebuilding the image.

---

## 4. Docs

**Directory:** `docs/`

| File | Content |
|---|---|
| `docs/tech_choices.md` | Rationale for each technology choice (PySpark, FastAPI, PostgreSQL, psycopg2, Chart.js, Docker Compose) |
| `docs/plan.md` | Original project plan and grading rubric |
| `docs/file_index.md` | Flat file inventory with one-line descriptions |
| `docs/components.md` | This file — how each component was built |

The `README.md` at the repo root covers quick-start, ETL arguments, API endpoints, test commands, and project layout.

---

## Cross-cutting: `src/ingest.py`

This file at `src/ingest.py` is a **dead prototype** — hardcoded credentials, a module-level `SparkSession`, and no parameterisation. It is not imported anywhere. The real implementation is `src/ingest/taxi_ingest.py` and `src/ingest/weather_ingest.py`.
