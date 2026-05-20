import logging
import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import col

logger = logging.getLogger(__name__)

TLC_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet"

DB_URL = os.getenv("DB_URL", "jdbc:postgresql://postgres-dwh:5432/nyc_weather_taxi")
DB_PROPERTIES = {
    "user": os.getenv("DB_USER", "data_engineer"),
    "password": os.getenv("DB_PASSWORD", "password123"),
    "driver": "org.postgresql.Driver",
}


def ingest_tlc_data(spark: SparkSession) -> int:
    """Read TLC yellow taxi Parquet, filter invalid rows, write to staging.fact_trip.

    Returns the number of records written.
    """
    logger.info("Starting TLC ingestion from %s", TLC_URL)
    df_raw = spark.read.parquet(TLC_URL)
    logger.info("Raw record count: %d", df_raw.count())

    df_clean = df_raw.filter(
        (col("total_amount") > 0)
        & (col("trip_distance") > 0)
        & (col("passenger_count") > 0)
    )

    count = df_clean.count()
    logger.info("Writing %d clean records to staging.fact_trip", count)

    df_clean.write.jdbc(
        url=DB_URL,
        table="staging.fact_trip",
        mode="overwrite",
        properties=DB_PROPERTIES,
    )

    logger.info("TLC ingestion complete")
    return count
