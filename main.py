import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

from pyspark.sql import SparkSession

from src.ingest.taxi_ingest import ingest_tlc_data
from src.ingest.weather_ingest import ingest_weather_data


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("NYCTaxiWeatherIngestion")
        .config("spark.jars", "/home/jovyan/work/postgresql-42.6.0.jar")
        .getOrCreate()
    )


def main() -> None:
    spark = build_spark()
    try:
        ingest_tlc_data(spark)
        ingest_weather_data(spark)
    except Exception:
        logging.exception("Ingestion failed")
        sys.exit(1)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
