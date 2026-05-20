import logging
import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    avg,
    col,
    count,
    row_number,
    sum,
    to_date,
)
from pyspark.sql.window import Window

logger = logging.getLogger(__name__)

DB_URL = os.getenv("DB_URL", "jdbc:postgresql://postgres-dwh:5432/nyc_weather_taxi")
DB_PROPERTIES = {
    "user": os.getenv("DB_USER", "data_engineer"),
    "password": os.getenv("DB_PASSWORD", "password123"),
    "driver": "org.postgresql.Driver",
}


def run_pipeline(spark: SparkSession) -> None:
    trips_raw = spark.read.jdbc(url=DB_URL, table="staging.fact_trip", properties=DB_PROPERTIES)
    weather_raw = spark.read.jdbc(url=DB_URL, table="staging.fact_weather", properties=DB_PROPERTIES)

    daily_trips = (
        trips_raw
        .withColumn("trip_date", to_date(col("tpep_pickup_datetime")))
        .groupBy("trip_date")
        .agg(
            count("*").alias("trip_count"),
            avg("fare_amount").alias("avg_fare"),
            avg("trip_distance").alias("avg_distance"),
            avg("passenger_count").alias("avg_passengers"),
        )
    )
    trip_count = daily_trips.count()
    logger.info("daily_trips rows: %d", trip_count)

    weather_dated = weather_raw.withColumn("weather_date", to_date(col("time")))

    # dominant weathercode: pick code with highest count per date
    wc_counts = (
        weather_dated
        .groupBy("weather_date", "weathercode")
        .agg(count("*").alias("wc_count"))
    )
    w = Window.partitionBy("weather_date").orderBy(col("wc_count").desc())
    dominant = (
        wc_counts
        .withColumn("rn", row_number().over(w))
        .filter(col("rn") == 1)
        .select("weather_date", col("weathercode").alias("dominant_weathercode"))
    )

    daily_weather = (
        weather_dated
        .groupBy("weather_date")
        .agg(
            avg("temperature_2m").alias("avg_temperature"),
            sum("precipitation").alias("total_precipitation"),
        )
        .join(dominant, "weather_date")
    )
    weather_count = daily_weather.count()
    logger.info("daily_weather rows: %d", weather_count)

    daily_correlation = (
        daily_trips
        .join(daily_weather, daily_trips["trip_date"] == daily_weather["weather_date"])
        .select(
            col("trip_date").alias("record_date"),
            col("trip_count"),
            col("avg_fare"),
            col("avg_distance"),
            col("avg_temperature"),
            col("total_precipitation"),
            col("dominant_weathercode"),
        )
    )
    corr_count = daily_correlation.count()
    logger.info("daily_correlation rows: %d", corr_count)

    daily_trips.write.jdbc(url=DB_URL, table="analytics.daily_trips", mode="overwrite", properties=DB_PROPERTIES)
    logger.info("wrote analytics.daily_trips")

    daily_weather.write.jdbc(url=DB_URL, table="analytics.daily_weather", mode="overwrite", properties=DB_PROPERTIES)
    logger.info("wrote analytics.daily_weather")

    daily_correlation.write.jdbc(url=DB_URL, table="analytics.daily_correlation", mode="overwrite", properties=DB_PROPERTIES)
    logger.info("wrote analytics.daily_correlation")
