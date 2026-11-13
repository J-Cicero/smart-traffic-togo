from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_renvoie_200_et_bon_json() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "application": "Traffic Togo",
    }
