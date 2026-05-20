from datetime import date

from fastapi import APIRouter

from src.api.db import get_conn
from src.api.models import DailyWeather

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("/daily", response_model=list[DailyWeather])
def get_daily_weather(start: date | None = None, end: date | None = None):
    sql = "SELECT weather_date, avg_temperature, total_precipitation, dominant_weathercode FROM analytics.daily_weather"
    params = []
    where = []
    if start:
        where.append("weather_date >= %s")
        params.append(start)
    if end:
        where.append("weather_date <= %s")
        params.append(end)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY weather_date ASC"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [DailyWeather(**dict(zip(cols, row))) for row in cur.fetchall()]
