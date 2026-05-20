# Technology Choices

## Python 3.13 + PySpark
PySpark processes NYC TLC Parquet files distributed across partitions — necessary for multi-month datasets that exceed single-machine memory. Python 3.13 is the current stable release with the latest type-hint improvements used throughout the codebase.

## FastAPI
FastAPI generates Swagger UI at `/docs` automatically from type annotations, eliminating manual API documentation. Its Pydantic integration validates response shapes at the boundary, catching schema mismatches before they reach the client.

## PostgreSQL 15
PostgreSQL supports schema namespacing (`staging.*`, `analytics.*`) for clean separation between raw and aggregated data. Relational joins between `daily_trips` and `daily_weather` on date are trivial in SQL; the same join in a NoSQL store would require application-level code.

## psycopg2 ThreadedConnectionPool
The API runs multiple concurrent requests under uvicorn workers. `ThreadedConnectionPool` reuses existing connections instead of opening a new one per request, keeping latency low without requiring an async driver.

## Chart.js
Chart.js runs entirely in the browser with no build step — a single CDN `<script>` tag. It supports dual-axis line charts, scatter plots, and bar charts out of the box, covering all three visualisations required by this project.

## Docker Compose
Three Compose files (`dev`, `test`, `prod`) give identical database schemas across all environments. The `prod` file adds nginx as a reverse proxy and uses `.env` credentials; `test` uses an ephemeral database and exits after pytest completes.
