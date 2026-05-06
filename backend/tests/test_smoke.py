from fastapi.testclient import TestClient

from app.main import app


def test_risk_score_smoke():
    client = TestClient(app)
    response = client.post(
        "/v1/risk-score",
        json={
            "user_id": "test",
            "features": {
                "sleep_duration_h": 6,
                "sleep_efficiency": 0.8,
                "steps": 5000,
                "transport_mode": "car",
                "speed_mean_kmh": 40,
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert 0 <= data["total_risk_score"] <= 1
    assert "accident_proxy" in data["proxy_scores"]
