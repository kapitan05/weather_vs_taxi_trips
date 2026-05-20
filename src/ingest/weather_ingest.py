import logging

import pandas as pd
import requests
from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)

WEATHER_API_URL = (
    "https://archive-api.open-meteo.com/v1/archive"
    "?latitude=40.7128&longitude=-74.0060"
    "&start_date=2023-01-01&end_date=2023-01-31"
    "&hourly=temperature_2m,precipitation,weathercode"
)

DB_URL = "jdbc:postgresql://postgres-dwh:5432/nyc_weather_taxi"
DB_PROPERTIES = {
    "user": "data_engineer",
    "password": "password123",
    "driver": "org.postgresql.Driver",
}


def ingest_weather_data(spark: SparkSession) -> int:
    """Fetch Open-Meteo hourly data for NYC Jan 2023, write to staging.fact_weather.

    Returns the number of records written.
    """
    logger.info("Fetching weather data from Open-Meteo")
    response = requests.get(WEATHER_API_URL, timeout=30)
    response.raise_for_status()
    data = response.json()

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

    logger.info("Writing %d weather records to staging.fact_weather", count)
    df_weather.write.jdbc(
        url=DB_URL,
        table="staging.fact_weather",
        mode="overwrite",
        properties=DB_PROPERTIES,
    )

    logger.info("Weather ingestion complete")
    return count
