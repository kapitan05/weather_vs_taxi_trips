from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, patch

COLS = ["record_date", "trip_count", "avg_fare", "avg_distance", "avg_temperature", "total_precipitation", "dominant_weathercode"]
ROWS = [
    (date(2024, 1, 1), 1200, 14.5, 2.8, -2.5, 0.0, 3),
    (date(2024, 1, 2), 980, 13.1, 2.5, 1.0, 5.2, 61),
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


def test_correlation_no_filter(client):
    with patch("src.api.routers.correlation.get_conn", make_get_conn(COLS, ROWS)):
        resp = client.get("/api/correlation/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["record_date"] == "2024-01-01"
    assert set(data[0].keys()) == set(COLS)


def test_correlation_start_filter(client):
    with patch("src.api.routers.correlation.get_conn", make_get_conn(COLS, ROWS)):
        resp = client.get("/api/correlation/?start=2024-01-01")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_correlation_end_filter(client):
    with patch("src.api.routers.correlation.get_conn", make_get_conn(COLS, ROWS)):
        resp = client.get("/api/correlation/?end=2024-01-02")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_correlation_both_filters(client):
    with patch("src.api.routers.correlation.get_conn", make_get_conn(COLS, ROWS)):
        resp = client.get("/api/correlation/?start=2024-01-01&end=2024-01-02")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
