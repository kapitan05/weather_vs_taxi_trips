import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.db import close_pool, init_pool
from src.api.routers.correlation import router as correlation_router
from src.api.routers.trips import router as trips_router
from src.api.routers.weather import router as weather_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    yield
    close_pool()


app = FastAPI(
    title="Weather vs Taxi Trips API",
    version="0.1.0",
    description="Correlation analysis between NYC weather conditions and yellow taxi trips",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trips_router)
app.include_router(weather_router)
app.include_router(correlation_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url)
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}
