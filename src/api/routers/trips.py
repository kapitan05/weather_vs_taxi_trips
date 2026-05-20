from datetime import date

from fastapi import APIRouter

from src.api.models import DailyTrips

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.get("/daily", response_model=list[DailyTrips])
def get_daily_trips(start: date | None = None, end: date | None = None):
    # TODO: Phase 4 — query analytics.daily_trips with psycopg2 pool
    return []
