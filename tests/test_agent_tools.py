import pytest

from backend.models.schemas import ShipmentResponse
from backend.services import agent_tools
from backend.services.agent_tools import (
    get_delay_risk,
    get_historical_delay_context,
    get_shipment,
)
from backend.services.shipment_service import (
    InvalidShipmentReferenceError,
    ShipmentNotFoundError,
)


def test_get_shipment_returns_shipment_record(shipment_data):
    shipment = get_shipment("shp-153440")

    assert isinstance(shipment, ShipmentResponse)
    assert shipment.shipment_reference == "SHP-153440"
    assert shipment.category == "Cleats"
    assert shipment.destination_city == "Vassouras"


def test_get_shipment_unknown_reference_raises(shipment_data):
    with pytest.raises(ShipmentNotFoundError):
        get_shipment("SHP-999999")


def test_get_shipment_invalid_reference_raises(shipment_data):
    with pytest.raises(InvalidShipmentReferenceError):
        get_shipment("ABC-1")


def test_get_delay_risk_returns_prediction_service_result(monkeypatch):
    calls = []
    sentinel = object()

    def fake_predict(shipment_id):
        calls.append(shipment_id)
        return sentinel

    monkeypatch.setattr(agent_tools, "predict_delay_risk", fake_predict)

    assert get_delay_risk("SHP-153440") is sentinel
    assert calls == ["SHP-153440"]


def test_get_historical_delay_context_reports_recorded_rates(shipment):
    context = get_historical_delay_context(shipment)

    assert context == {
        "product_name": "Trail Running Shoe",
        "market": "LATAM",
        "shipping_mode": "Standard Class",
        "scheduled_shipping_days": 4,
        "historical_delay_rates": {
            "product": 0.57,
            "market": 0.55,
            "shipping_mode": 0.38,
        },
        "highest_delay_rate_factor": "product",
    }


def test_get_historical_delay_context_identifies_highest_factor(shipment):
    shipment = shipment.model_copy(
        update={"historical_shipping_mode_delay_rate": 0.9}
    )

    context = get_historical_delay_context(shipment)

    assert context["highest_delay_rate_factor"] == "shipping_mode"
