from datetime import date

from fastapi import APIRouter

from src.api.db import get_conn
from src.api.models import DailyTrips

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.get("/daily", response_model=list[DailyTrips])
def get_daily_trips(start: date | None = None, end: date | None = None):
    sql = "SELECT trip_date, trip_count, avg_fare, avg_distance, avg_passengers FROM analytics.daily_trips"
    params = []
    where = []
    if start:
        where.append("trip_date >= %s")
        params.append(start)
    if end:
        where.append("trip_date <= %s")
        params.append(end)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY trip_date ASC"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [DailyTrips(**dict(zip(cols, row))) for row in cur.fetchall()]
