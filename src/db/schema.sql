-- ============================================================
-- NYC Weather vs Taxi Trips — Database Schema
-- Run once to initialise both schemas and all tables.
-- Idempotent: safe to re-run.
-- ============================================================

CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;

-- ------------------------------------------------------------
-- STAGING — raw data written by PySpark JDBC (mode=overwrite)
-- Column types match the Parquet / API source exactly.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS staging.fact_trip (
    vendor_id                 INTEGER,
    tpep_pickup_datetime      TIMESTAMP,
    tpep_dropoff_datetime     TIMESTAMP,
    passenger_count           REAL,
    trip_distance             REAL,
    rate_code_id              REAL,
    store_and_fwd_flag        TEXT,
    pu_location_id            INTEGER,
    do_location_id            INTEGER,
    payment_type              INTEGER,
    fare_amount               REAL,
    extra                     REAL,
    mta_tax                   REAL,
    tip_amount                REAL,
    tolls_amount              REAL,
    improvement_surcharge     REAL,
    total_amount              REAL,
    congestion_surcharge      REAL,
    airport_fee               REAL,
    ingested_at               TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS staging.fact_weather (
    time                      TIMESTAMP,
    temperature_2m            REAL,
    precipitation             REAL,
    weathercode               INTEGER,
    ingested_at               TIMESTAMP DEFAULT NOW()
);

-- ------------------------------------------------------------
-- ANALYTICS — aggregated tables written by the transform pipeline.
-- These are the tables the REST API reads from.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS analytics.daily_trips (
    trip_date       DATE PRIMARY KEY,
    trip_count      BIGINT      NOT NULL,
    avg_fare        REAL        NOT NULL,
    avg_distance    REAL        NOT NULL,
    avg_passengers  REAL        NOT NULL,
    updated_at      TIMESTAMP   DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analytics.daily_weather (
    weather_date            DATE PRIMARY KEY,
    avg_temperature         REAL    NOT NULL,
    total_precipitation     REAL    NOT NULL,
    dominant_weathercode    INTEGER NOT NULL,
    updated_at              TIMESTAMP DEFAULT NOW()
);

-- Primary table consumed by the API /correlation endpoint.
-- Joined from daily_trips + daily_weather on date.
CREATE TABLE IF NOT EXISTS analytics.daily_correlation (
    record_date             DATE PRIMARY KEY,
    trip_count              BIGINT  NOT NULL,
    avg_fare                REAL    NOT NULL,
    avg_distance            REAL    NOT NULL,
    avg_temperature         REAL    NOT NULL,
    total_precipitation     REAL    NOT NULL,
    dominant_weathercode    INTEGER NOT NULL,
    updated_at              TIMESTAMP DEFAULT NOW()
);

-- ------------------------------------------------------------
-- Indexes for API range queries on date columns
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_daily_trips_date
    ON analytics.daily_trips (trip_date);

CREATE INDEX IF NOT EXISTS idx_daily_weather_date
    ON analytics.daily_weather (weather_date);

CREATE INDEX IF NOT EXISTS idx_daily_correlation_date
    ON analytics.daily_correlation (record_date);
