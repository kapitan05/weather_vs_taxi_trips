import argparse
import logging
import sys

from src.ingest.logging_config import setup_json_logging

setup_json_logging()

from pyspark.sql import SparkSession

from src.ingest.taxi_ingest import ingest_tlc_data
from src.ingest.weather_ingest import ingest_weather_data
from src.transform.pipeline import run_pipeline

logger = logging.getLogger(__name__)


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("NYCTaxiWeatherIngestion")
        .config("spark.jars", "/home/jovyan/work/postgresql-42.6.0.jar")
        .getOrCreate()
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest TLC + weather data into PostgreSQL")
    p.add_argument("--year", type=int, default=2023)
    p.add_argument("--start-month", type=int, default=1, dest="start_month")
    p.add_argument("--end-month", type=int, default=1, dest="end_month")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    months = list(range(args.start_month, args.end_month + 1))
    logger.info("Ingestion started", extra={"year": args.year, "months": months})

    spark = build_spark()
    try:
        for i, month in enumerate(months):
            write_mode = "overwrite" if i == 0 else "append"
            ingest_tlc_data(spark, year=args.year, month=month, mode=write_mode)
            ingest_weather_data(spark, year=args.year, month=month, mode=write_mode)
        run_pipeline(spark)
    except Exception:
        logger.exception("Ingestion failed")
        sys.exit(1)
    finally:
        spark.stop()

    logger.info("Ingestion finished", extra={"year": args.year, "months": months})


if __name__ == "__main__":
    main()
