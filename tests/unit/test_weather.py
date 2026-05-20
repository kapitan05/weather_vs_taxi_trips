from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, patch

COLS = ["weather_date", "avg_temperature", "total_precipitation", "dominant_weathercode"]
ROWS = [
    (date(2024, 1, 1), -2.5, 0.0, 3),
    (date(2024, 1, 2), 1.0, 5.2, 61),
]


def make_get_conn(cols, rows):
    cur = MagicMock()
    cur.description = [(c,) for c in cols]
    cur.fetchall.return_value = rows
    cur.__enter__ = lambda s: cur
    cur.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur

    @contextmanager
    def _get_conn():
        yield conn

    return _get_conn


def test_weather_no_filter(client):
    with patch("src.api.routers.weather.get_conn", make_get_conn(COLS, ROWS)):
        resp = client.get("/api/weather/daily")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["weather_date"] == "2024-01-01"
    assert set(data[0].keys()) == set(COLS)


def test_weather_start_filter(client):
    with patch("src.api.routers.weather.get_conn", make_get_conn(COLS, ROWS)):
        resp = client.get("/api/weather/daily?start=2024-01-01")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_weather_end_filter(client):
    with patch("src.api.routers.weather.get_conn", make_get_conn(COLS, ROWS)):
        resp = client.get("/api/weather/daily?end=2024-01-02")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_weather_both_filters(client):
    with patch("src.api.routers.weather.get_conn", make_get_conn(COLS, ROWS)):
        resp = client.get("/api/weather/daily?start=2024-01-01&end=2024-01-02")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
