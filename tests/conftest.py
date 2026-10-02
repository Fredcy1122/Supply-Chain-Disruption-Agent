import pandas as pd
import pytest

from backend.models.schemas import PredictionResponse, RiskLevel
from backend.services import agent_tools, shipment_service


SHIPMENT_RECORD = {
    "order_id": 61458,
    "shipment_id": 153440,
    "shipment_reference": "SHP-153440",
    "product_name": "Trail Running Shoe",
    "category": "Cleats",
    "department": "Footwear",
    "market": "LATAM",
    "customer_country": "EE. UU.",
    "destination_country": "Brasil",
    "destination_region": "South America",
    "destination_state": "Rio de Janeiro",
    "destination_city": "Vassouras",
    "shipping_mode": "Standard Class",
    "scheduled_shipping_days": 4,
    "quantity": 2,
    "product_price": 59.99,
    "sales": 119.98,
    "discount": 6.0,
    "order_date": "2017-05-01 10:30:00",
    "latitude": 39.8166,
    "longitude": -74.9847,
    "historical_product_delay_rate": 0.57,
    "historical_market_delay_rate": 0.55,
    "historical_shipping_mode_delay_rate": 0.38,
}


@pytest.fixture
def shipment_data(monkeypatch):
    """
    Replace the Shipment Tool dataset with one known record.
    """
    dataframe = pd.DataFrame([SHIPMENT_RECORD])
    monkeypatch.setattr(
        shipment_service,
        "load_shipment_data",
        lambda: dataframe,
    )
    return dataframe


@pytest.fixture
def shipment(shipment_data):
    return shipment_service.get_shipment_by_id("SHP-153440")


def make_prediction(
    risk_level: RiskLevel,
    probability: float,
    requires_investigation: bool,
) -> PredictionResponse:
    return PredictionResponse(
        shipment_id="SHP-153440",
        delay_probability=probability,
        risk_level=risk_level,
        requires_investigation=requires_investigation,
    )


@pytest.fixture
def high_risk(monkeypatch, shipment_data):
    """
    Mock the model so the shipment passes the risk gate.
    """
    prediction = make_prediction(RiskLevel.HIGH, 0.82, True)
    monkeypatch.setattr(
        agent_tools,
        "predict_delay_risk",
        lambda shipment_id: prediction,
    )
    return prediction


@pytest.fixture
def low_risk(monkeypatch, shipment_data):
    """
    Mock the model so the shipment is stopped by the risk gate.
    """
    prediction = make_prediction(RiskLevel.LOW, 0.12, False)
    monkeypatch.setattr(
        agent_tools,
        "predict_delay_risk",
        lambda shipment_id: prediction,
    )
    return prediction
