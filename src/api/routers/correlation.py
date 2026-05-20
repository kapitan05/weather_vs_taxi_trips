from datetime import date

from fastapi import APIRouter

from src.api.models import DailyCorrelation

router = APIRouter(prefix="/api/correlation", tags=["correlation"])


@router.get("/", response_model=list[DailyCorrelation])
def get_correlation(start: date | None = None, end: date | None = None):
    # TODO: Phase 4 — query analytics.daily_correlation with psycopg2 pool
    return []
