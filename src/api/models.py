from datetime import date

from pydantic import BaseModel


class DailyTrips(BaseModel):
    trip_date: date
    trip_count: int
    avg_fare: float
    avg_distance: float
    avg_passengers: float


class DailyWeather(BaseModel):
    weather_date: date
    avg_temperature: float
    total_precipitation: float
    dominant_weathercode: int


class DailyCorrelation(BaseModel):
    record_date: date
    trip_count: int
    avg_fare: float
    avg_distance: float
    avg_temperature: float
    total_precipitation: float
    dominant_weathercode: int
