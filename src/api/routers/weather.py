from datetime import date

from fastapi import APIRouter

from src.api.models import DailyWeather

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("/daily", response_model=list[DailyWeather])
def get_daily_weather(start: date | None = None, end: date | None = None):
    # TODO: Phase 4 — query analytics.daily_weather with psycopg2 pool
    return []
