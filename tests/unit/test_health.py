from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.main import app


def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_global_exception_handler():
    with patch("src.api.main.init_pool"), patch("src.api.main.close_pool"):
        with TestClient(app, raise_server_exceptions=False) as c:
            with patch("src.api.routers.trips.get_conn", side_effect=RuntimeError("boom")):
                resp = c.get("/api/trips/daily")
    assert resp.status_code == 500
    assert "error" in resp.json()
