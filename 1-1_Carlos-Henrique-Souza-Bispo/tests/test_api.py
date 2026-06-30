from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_and_prediction(high_risk_payload: dict[str, object]) -> None:
    with TestClient(app) as client:
        health = client.get("/health")
        response = client.post("/api/v1/predict", json=high_risk_payload)

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["churn_probability"] <= 1
    assert body["model_source"] == "modelo"
    assert len(body["recommendations"]) <= 3


def test_api_returns_friendly_validation_error(
    high_risk_payload: dict[str, object],
) -> None:
    high_risk_payload["tenure"] = -1

    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=high_risk_payload)

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_input"
    assert response.json()["message"] == "Revise os dados informados."


def test_interface_is_served() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "RetentionAI" in response.text
