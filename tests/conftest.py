from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    with patch("src.api.main.init_pool"), patch("src.api.main.close_pool"):
        with TestClient(app) as c:
            yield c
