import logging
import os

import requests
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

logger = logging.getLogger(__name__)

TLC_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{year:04d}-{month:02d}.parquet"

DB_URL = os.getenv("DB_URL", "jdbc:postgresql://postgres-dwh:5432/nyc_weather_taxi")
DB_PROPERTIES = {
    "user": os.getenv("DB_USER", "data_engineer"),
    "password": os.getenv("DB_PASSWORD", "password123"),
    "driver": "org.postgresql.Driver",
}


def ingest_tlc_data(spark: SparkSession, year: int, month: int, mode: str = "overwrite") -> int:
    url = TLC_BASE_URL.format(year=year, month=month)
    local_path = f"/tmp/yellow_tripdata_{year:04d}-{month:02d}.parquet"
    logger.info("Downloading TLC parquet", extra={"url": url, "dest": local_path})

    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)

    try:
        df_raw = spark.read.parquet(local_path)
        raw_count = df_raw.count()
        logger.info("Raw record count", extra={"count": raw_count, "year": year, "month": month})

        df_clean = df_raw.filter(
            (col("total_amount") > 0)
            & (col("trip_distance") > 0)
            & (col("passenger_count") > 0)
        )

        count = df_clean.count()
        logger.info("Writing clean records", extra={"count": count, "table": "staging.fact_trip", "mode": mode})

        df_clean.write.jdbc(
            url=DB_URL,
            table="staging.fact_trip",
            mode=mode,
            properties=DB_PROPERTIES,
        )
    finally:
        os.remove(local_path)

    logger.info("TLC ingestion complete", extra={"year": year, "month": month, "written": count})
    return count
