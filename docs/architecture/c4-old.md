# C4 Architecture — Weather vs Taxi Trips

---

## Level 1 — System Context

> Who uses the system and what external systems does it depend on?

```mermaid
C4Context
    title System Context — Weather vs Taxi Trips

    Person(analyst, "Data Analyst", "Explores the correlation between NYC weather conditions and yellow taxi trip volumes via a browser dashboard.")

    System(system, "Weather vs Taxi Trips", "End-to-end data pipeline that ingests, processes, and visualises NYC taxi and weather data.")

    System_Ext(tlc, "NYC TLC Open Data", "Publishes monthly yellow taxi trip records as Parquet files on a public CDN.")
    System_Ext(meteo, "Open-Meteo Archive API", "Provides free historical hourly weather observations (temperature, precipitation, weather code) for any location.")

    Rel(analyst, system, "Views correlation dashboard", "HTTPS / Browser")
    Rel(system, tlc, "Downloads monthly Parquet files", "HTTPS")
    Rel(system, meteo, "Fetches hourly weather history", "HTTPS / JSON")
```

---

## Level 2 — Container

> What are the deployable units and how do they communicate?

```mermaid
C4Container
    title Container Diagram — Weather vs Taxi Trips

    Person(analyst, "Data Analyst")

    System_Boundary(sys, "Weather vs Taxi Trips") {
        Container(nginx, "nginx", "nginx:alpine", "Reverse proxy. Serves the static frontend at / and forwards /api/* requests to FastAPI.")
        Container(frontend, "Dashboard", "HTML / JS / Chart.js 4", "Single-page app with a date-range picker. Renders three charts: dual-axis time series, scatter plot, and bar chart grouped by weather condition.")
        Container(api, "REST API", "FastAPI · Python 3.13 · uvicorn", "Exposes GET /api/trips/daily, /api/weather/daily, /api/correlation/ with optional date-range query params. Auto-generates Swagger UI at /docs.")
        Container(etl, "PySpark ETL", "Apache Spark · Python 3.13", "Monthly batch job. Ingests raw taxi Parquet and weather JSON into staging tables, then aggregates them into analytics tables.")
        ContainerDb(db, "Data Warehouse", "PostgreSQL 15", "Holds two schemas: staging (raw data overwritten each run) and analytics (daily aggregates read by the API).")
    }

    System_Ext(tlc, "NYC TLC Open Data")
    System_Ext(meteo, "Open-Meteo Archive API")

    Rel(analyst, nginx, "Opens browser", "HTTPS :80")
    Rel(nginx, frontend, "Serves static files", "file system")
    Rel(nginx, api, "Proxies /api/* requests", "HTTP")
    Rel(frontend, nginx, "Fetches /api/correlation/", "HTTP / JSON")
    Rel(api, db, "Reads analytics.daily_*", "psycopg2 · SQL")
    Rel(etl, db, "Writes staging.* then analytics.*", "JDBC · SQL")
    Rel(etl, tlc, "Downloads yellow_tripdata_YYYY-MM.parquet", "HTTPS")
    Rel(etl, meteo, "GET /v1/archive?latitude=…", "HTTPS / JSON")
```

---

## Level 3 — Component

> What are the major components inside each container?

### REST API

```mermaid
C4Component
    title Component Diagram — REST API (FastAPI)

    Container_Ext(frontend, "Dashboard", "HTML / JS")
    ContainerDb_Ext(db, "PostgreSQL 15", "Data Warehouse")

    Container_Boundary(api, "REST API") {
        Component(main, "Application", "src/api/main.py", "Bootstraps the FastAPI app. Registers middleware (CORS), routers, global exception handler, lifespan hooks, and the static-file mount.")
        Component(pool, "DB Pool", "src/api/db.py", "Manages a psycopg2 ThreadedConnectionPool (2–10 conns). Exposes get_conn() context manager. Initialised on startup, closed on shutdown.")
        Component(models, "Response Models", "src/api/models.py", "Pydantic models (DailyTrips, DailyWeather, DailyCorrelation) that validate and serialise query results.")
        Component(r_trips, "Trips Router", "src/api/routers/trips.py", "GET /api/trips/daily — queries analytics.daily_trips with optional start/end date filters.")
        Component(r_weather, "Weather Router", "src/api/routers/weather.py", "GET /api/weather/daily — queries analytics.daily_weather with optional start/end date filters.")
        Component(r_corr, "Correlation Router", "src/api/routers/correlation.py", "GET /api/correlation/ — queries analytics.daily_correlation with optional start/end date filters.")
    }

    Rel(frontend, main, "HTTP request")
    Rel(main, r_trips, "Routes /api/trips/*")
    Rel(main, r_weather, "Routes /api/weather/*")
    Rel(main, r_corr, "Routes /api/correlation/*")
    Rel(r_trips, pool, "get_conn()")
    Rel(r_weather, pool, "get_conn()")
    Rel(r_corr, pool, "get_conn()")
    Rel(r_trips, models, "DailyTrips")
    Rel(r_weather, models, "DailyWeather")
    Rel(r_corr, models, "DailyCorrelation")
    Rel(pool, db, "psycopg2 · SQL")
```

### PySpark ETL

```mermaid
C4Component
    title Component Diagram — PySpark ETL

    System_Ext(tlc, "NYC TLC Open Data")
    System_Ext(meteo, "Open-Meteo API")
    ContainerDb_Ext(db, "PostgreSQL 15", "Data Warehouse")

    Container_Boundary(etl, "PySpark ETL") {
        Component(entry, "Entry Point", "main.py", "Creates the Spark session and iterates over the requested year/month range, calling ingest then transform.")
        Component(log, "JSON Logger", "src/ingest/logging_config.py", "Configures the root logger with a custom JsonFormatter so all log output is structured JSON lines.")
        Component(taxi, "Taxi Ingestor", "src/ingest/taxi_ingest.py", "Downloads the monthly TLC Parquet via Spark, drops rows with zero fare / distance / passengers, writes to staging.fact_trip (JDBC, mode=overwrite).")
        Component(weather, "Weather Ingestor", "src/ingest/weather_ingest.py", "Calls Open-Meteo with retry/backoff, validates the response schema, converts hourly records to a Spark DataFrame, writes to staging.fact_weather.")
        Component(pipeline, "Transform Pipeline", "src/transform/pipeline.py", "Reads both staging tables, computes daily aggregates (trip_count, avg_fare, avg_distance, avg_passengers, avg_temperature, total_precipitation, dominant_weathercode), joins on date, writes analytics.daily_trips / daily_weather / daily_correlation.")
    }

    Rel(entry, log, "setup_json_logging()")
    Rel(entry, taxi, "ingest_tlc_data(spark, year, month)")
    Rel(entry, weather, "ingest_weather_data(spark, year, month)")
    Rel(entry, pipeline, "run_pipeline(spark)")
    Rel(taxi, tlc, "spark.read.parquet(url)")
    Rel(weather, meteo, "requests.get() with retry")
    Rel(taxi, db, "df.write.jdbc() → staging.fact_trip")
    Rel(weather, db, "df.write.jdbc() → staging.fact_weather")
    Rel(pipeline, db, "spark.read.jdbc() → staging.*")
    Rel(pipeline, db, "df.write.jdbc() → analytics.*")
```

---

## Database Schema

```
staging
├── fact_trip     — raw TLC columns (vendor_id, fare_amount, trip_distance, …)
└── fact_weather  — raw Open-Meteo hourly rows (time, temperature_2m, precipitation, weathercode)

analytics
├── daily_trips        — trip_date PK | trip_count | avg_fare | avg_distance | avg_passengers
├── daily_weather      — weather_date PK | avg_temperature | total_precipitation | dominant_weathercode
└── daily_correlation  — record_date PK | all trip + weather columns joined on date
```
