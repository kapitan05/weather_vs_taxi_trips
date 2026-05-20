import logging

from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)


def run_pipeline(spark: SparkSession) -> None:
    """Aggregate staging tables into analytics tables.

    Reads staging.fact_trip and staging.fact_weather, aggregates by date,
    joins them, and writes to analytics.daily_trips, analytics.daily_weather,
    and analytics.daily_correlation.
    """
    # TODO: Phase 3
    raise NotImplementedError("Transform pipeline — implement in Phase 3")
