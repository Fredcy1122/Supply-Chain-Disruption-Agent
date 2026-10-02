from fastapi.testclient import TestClient

from backend.api import routes_predictions
from backend.main import app
from backend.services.shipment_service import ShipmentDataUnavailableError


client = TestClient(app)


def test_application_starts_and_reports_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_application_registers_agent_and_prediction_routes():
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/agent/investigate/{shipment_id}" in paths
    assert "/api/predictions/evaluate/{shipment_id}" in paths


def test_prediction_returns_503_when_shipment_data_unavailable(monkeypatch):
    def unavailable(shipment_id):
        raise ShipmentDataUnavailableError("dataset missing")

    monkeypatch.setattr(routes_predictions, "predict_delay_risk", unavailable)

    response = client.post("/api/predictions/evaluate/SHP-153440")

    assert response.status_code == 503
    assert response.json()["detail"] == "dataset missing"
