import pandas as pd
import requests
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

# --- 1. Configuration & Setup ---
DB_URL = "jdbc:postgresql://postgres-dwh:5432/nyc_weather_taxi"
DB_PROPERTIES = {
    "user": "data_engineer",
    "password": "password123",
    "driver": "org.postgresql.Driver",
}

# Initialize Spark Session with PostgreSQL JDBC Driver
spark = (
    SparkSession.builder.appName("NYCTaxiWeatherIngestion")
    .config("spark.jars", "/home/jovyan/work/postgresql-42.6.0.jar")
    .getOrCreate()
)


# --- 2. Ingest TLC Trip Record Data (Parquet) ---
def ingest_tlc_data():
    print("Starting TLC Data Ingestion...")
    # Example: Yellow Taxi data for January 2023 directly from TLC website
    tlc_url = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet"

    # Read Parquet
    df_taxi = spark.read.parquet(tlc_url)

    # Transform: Clean TLC Data (as per your report)
    df_taxi_clean = df_taxi.filter(
        (col("total_amount") > 0)
        & (col("trip_distance") > 0)
        & (col("passenger_count") > 0)
    )

    # Load to PostgreSQL (Overwrites for testing, change to 'append' for production)
    print("Writing TLC data to PostgreSQL...")
    df_taxi_clean.write.jdbc(
        url=DB_URL,
        table="staging_fact_trip",
        mode="overwrite",
        properties=DB_PROPERTIES,
    )
    print("TLC Data Ingestion Complete.")


# --- 3. Ingest Open-Meteo Data (JSON API) ---
def ingest_weather_data():
    print("Starting Open-Meteo Data Ingestion...")
    # Example: NYC Coordinates (Lat: 40.71, Lon: -74.00) for Jan 2023
    api_url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        "latitude=40.7128&longitude=-74.0060"
        "&start_date=2023-01-01&end_date=2023-01-31"
        "&hourly=temperature_2m,precipitation,weathercode"
    )

    # Extract
    response = requests.get(api_url)
    data = response.json()

    # Transform JSON to Pandas, then to Spark DataFrame
    # Open-Meteo returns hourly data, which fits your "hourly aggregation" requirement natively
    df_pandas = pd.DataFrame(
        {
            "time": data["hourly"]["time"],
            "temperature_2m": data["hourly"]["temperature_2m"],
            "precipitation": data["hourly"]["precipitation"],
            "weathercode": data["hourly"]["weathercode"],
        }
    )

    df_weather = spark.createDataFrame(df_pandas)

    # Load to PostgreSQL
    print("Writing Weather data to PostgreSQL...")
    df_weather.write.jdbc(
        url=DB_URL,
        table="staging_fact_weather",
        mode="overwrite",
        properties=DB_PROPERTIES,
    )
    print("Weather Data Ingestion Complete.")


# --- 4. Execution ---
if __name__ == "__main__":
    ingest_tlc_data()
    ingest_weather_data()
    spark.stop()
