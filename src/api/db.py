import os
from contextlib import contextmanager

from psycopg2.pool import ThreadedConnectionPool

_pool: ThreadedConnectionPool | None = None


def init_pool() -> None:
    global _pool
    _pool = ThreadedConnectionPool(
        minconn=2,
        maxconn=10,
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "nyc_weather_taxi"),
        user=os.getenv("DB_USER", "data_engineer"),
        password=os.getenv("DB_PASSWORD", "password123"),
    )


def close_pool() -> None:
    if _pool:
        _pool.closeall()


@contextmanager
def get_conn():
    conn = _pool.getconn()
    try:
        yield conn
    finally:
        _pool.putconn(conn)
