from fastapi import FastAPI

from src.api.routers.correlation import router as correlation_router
from src.api.routers.trips import router as trips_router
from src.api.routers.weather import router as weather_router

app = FastAPI(
    title="Weather vs Taxi Trips API",
    version="0.1.0",
    description="Correlation analysis between NYC weather conditions and yellow taxi trips",
)

app.include_router(trips_router)
app.include_router(weather_router)
app.include_router(correlation_router)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
