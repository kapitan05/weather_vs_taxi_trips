import calendar
import logging
import os

import pandas as pd
import requests
from pyspark.sql import SparkSession
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

WEATHER_API_BASE = (
    "https://archive-api.open-meteo.com/v1/archive"
    "?latitude=40.7128&longitude=-74.0060"
    "&start_date={start_date}&end_date={end_date}"
    "&hourly=temperature_2m,precipitation,weathercode"
)
HOURLY_FIELDS = {"time", "temperature_2m", "precipitation", "weathercode"}

DB_URL = os.getenv("DB_URL", "jdbc:postgresql://postgres-dwh:5432/nyc_weather_taxi")
DB_PROPERTIES = {
    "user": os.getenv("DB_USER", "data_engineer"),
    "password": os.getenv("DB_PASSWORD", "password123"),
    "driver": "org.postgresql.Driver",
}


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _validate_response(data: dict) -> None:
    if "hourly" not in data:
        raise ValueError("Missing 'hourly' key in Open-Meteo response")
    missing = HOURLY_FIELDS - set(data["hourly"].keys())
    if missing:
        raise ValueError(f"Missing hourly fields: {missing}")


def ingest_weather_data(spark: SparkSession, year: int, month: int, mode: str = "overwrite") -> int:
    last_day = calendar.monthrange(year, month)[1]
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-{last_day:02d}"
    url = WEATHER_API_BASE.format(start_date=start_date, end_date=end_date)

    logger.info("Fetching weather data", extra={"url": url, "year": year, "month": month})
    session = _build_session()
    response = session.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    _validate_response(data)

    df_pandas = pd.DataFrame(
        {
            "time": pd.to_datetime(data["hourly"]["time"]),
            "temperature_2m": data["hourly"]["temperature_2m"],
            "precipitation": data["hourly"]["precipitation"],
            "weathercode": data["hourly"]["weathercode"],
        }
    )

    df_weather = spark.createDataFrame(df_pandas)
    count = len(df_pandas)

    logger.info("Writing weather records", extra={"count": count, "table": "staging.fact_weather", "mode": mode})
    df_weather.write.jdbc(
        url=DB_URL,
        table="staging.fact_weather",
        mode=mode,
        properties=DB_PROPERTIES,
    )

    logger.info("Weather ingestion complete", extra={"year": year, "month": month, "written": count})
    return count
