from datetime import date

from fastapi import APIRouter

from src.api.db import get_conn
from src.api.models import DailyCorrelation

router = APIRouter(prefix="/api/correlation", tags=["correlation"])


@router.get("/", response_model=list[DailyCorrelation])
def get_correlation(start: date | None = None, end: date | None = None):
    sql = "SELECT record_date, trip_count, avg_fare, avg_distance, avg_temperature, total_precipitation, dominant_weathercode FROM analytics.daily_correlation"
    params = []
    where = []
    if start:
        where.append("record_date >= %s")
        params.append(start)
    if end:
        where.append("record_date <= %s")
        params.append(end)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY record_date ASC"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [DailyCorrelation(**dict(zip(cols, row))) for row in cur.fetchall()]
