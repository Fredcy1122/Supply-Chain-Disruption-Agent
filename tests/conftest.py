import pandas as pd
import pytest

from backend.models.schemas import (
    LLMBriefingContent,
    PredictionResponse,
    RiskLevel,
)
from backend.services import (
    agent_service,
    agent_tools,
    briefing_service,
    shipment_service,
    weather_service,
)


WEATHER_EVIDENCE = {
    "destination": "Vassouras, Brazil",
    "latitude": -22.4036,
    "longitude": -43.6625,
    "window_start": "2017-05-01",
    "window_end": "2017-05-05",
    "window_basis": agent_tools.WEATHER_WINDOW_BASIS,
    "daily": [],
    "precipitation_total_mm": 9.2,
    "precipitation_max_mm": 8.9,
    "max_wind_speed_kmh": 17.9,
    "worst_weather_code": 61,
    "worst_weather_description": "slight rain",
    "severity": "low",
    "source": "Open-Meteo historical archive",
}


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


@pytest.fixture(autouse=True)
def no_live_weather(monkeypatch):
    """
    Keep every test offline and independent from the live weather API.

    HTTP calls fail unless a test replaces the mock. Cached weather
    lookups are cleared before and after each test. Agent investigations
    receive fixed weather evidence unless a test explicitly replaces it.
    """

    def network_blocked(*args, **kwargs):
        raise AssertionError(
            "Tests must not call the live weather API."
        )

    monkeypatch.setattr(
        weather_service.requests,
        "get",
        network_blocked,
    )

    monkeypatch.setattr(
        agent_service,
        "get_destination_weather",
        lambda shipment: WEATHER_EVIDENCE,
    )

    weather_service.geocode_city.cache_clear()
    weather_service.get_daily_weather.cache_clear()

    yield

    weather_service.geocode_city.cache_clear()
    weather_service.get_daily_weather.cache_clear()


@pytest.fixture
def mock_azure_briefing(monkeypatch):
    """
    Replace Azure OpenAI synthesis with deterministic content.

    Agent, API, and streaming unit tests use this fixture so they do
    not consume Azure tokens or depend on network availability. Real
    Azure behavior is tested separately by integration tests.
    """

    def deterministic_azure_briefing(
        shipment_id,
        risk_level,
        delay_probability,
        evidence,
        retrieved_knowledge,
    ):
        summary_parts = [
            (
                f"Shipment {shipment_id} has a "
                f"{risk_level.value} predicted delay risk of "
                f"{delay_probability:.1%}."
            )
        ]

        risk_factors = []

        if evidence.shipment_summary:
            summary_parts.append(
                evidence.shipment_summary
            )

        if evidence.historical_delay_summary:
            summary_parts.append(
                evidence.historical_delay_summary
            )

            risk_factors.append(
                evidence.historical_delay_summary
            )

        if evidence.weather_summary:
            summary_parts.append(
                evidence.weather_summary
            )

            risk_factors.append(
                evidence.weather_summary
            )

        if evidence.supplier_status:
            summary_parts.append(
                evidence.supplier_status
            )

            risk_factors.append(
                evidence.supplier_status
            )
        else:
            summary_parts.append(
                "Supplier availability has not yet been assessed."
            )

        if evidence.inventory_coverage_days is not None:
            summary_parts.append(
                "Available inventory coverage is "
                f"{evidence.inventory_coverage_days} days."
            )
        else:
            summary_parts.append(
                "Inventory coverage has not yet been assessed."
            )

        recommended_actions = [
            "Continue human operational review.",
        ]

        if evidence.historical_delay_summary:
            recommended_actions.append(
                "Review the elevated historical delay factors."
            )

        if evidence.weather_summary:
            weather_text = (
                evidence.weather_summary.lower()
            )

            severe_weather_terms = (
                "high severity",
                "severe weather",
                "thunderstorm",
                "heavy rain",
                "heavy snow",
                "extreme weather",
                "flood",
                "hurricane",
                "tornado",
            )

            low_weather_terms = (
                "low severity",
                "light drizzle",
                "clear sky",
                "mainly clear",
                "partly cloudy",
            )

            severe_weather = any(
                term in weather_text
                for term in severe_weather_terms
            )

            low_weather = any(
                term in weather_text
                for term in low_weather_terms
            )

            if severe_weather and not low_weather:
                recommended_actions.append(
                    "Evaluate transport alternatives because the "
                    "collected weather evidence indicates potentially "
                    "severe conditions."
                )
            elif low_weather:
                recommended_actions.append(
                    "Continue monitoring destination weather, but do "
                    "not reroute solely on the current low-severity "
                    "weather evidence."
                )
            else:
                recommended_actions.append(
                    "Continue monitoring destination weather before "
                    "making any rerouting decision."
                )

        if evidence.supplier_status:
            recommended_actions.append(
                "Validate the synthetic supplier geographically, "
                "commercially, and operationally before considering "
                "a supplier change."
            )
        else:
            recommended_actions.append(
                "Obtain supplier availability and performance "
                "evidence before recommending an alternative."
            )

        if evidence.inventory_coverage_days is None:
            recommended_actions.append(
                "Obtain inventory coverage before determining "
                "stockout exposure."
            )
        elif evidence.inventory_coverage_days <= 3:
            recommended_actions.append(
                "Escalate potential stockout exposure because "
                "inventory coverage is three days or less."
            )
        else:
            recommended_actions.append(
                "Compare the expected disruption duration with "
                "available inventory coverage."
            )

        return LLMBriefingContent(
            summary=" ".join(summary_parts),
            risk_factors=risk_factors,
            recommended_actions=recommended_actions,
        )

    monkeypatch.setattr(
        briefing_service,
        "generate_azure_briefing",
        deterministic_azure_briefing,
    )


@pytest.fixture
def shipment_data(monkeypatch):
    """
    Replace the Shipment Tool dataset with one known record.
    """
    dataframe = pd.DataFrame(
        [SHIPMENT_RECORD]
    )

    monkeypatch.setattr(
        shipment_service,
        "load_shipment_data",
        lambda: dataframe,
    )

    return dataframe


@pytest.fixture
def shipment(shipment_data):
    """
    Return the known leakage-safe shipment record.
    """
    return shipment_service.get_shipment_by_id(
        "SHP-153440"
    )


def make_prediction(
    risk_level: RiskLevel,
    probability: float,
    requires_investigation: bool,
) -> PredictionResponse:
    """
    Create a deterministic prediction response for agent tests.
    """
    return PredictionResponse(
        shipment_id="SHP-153440",
        delay_probability=probability,
        risk_level=risk_level,
        requires_investigation=requires_investigation,
    )


@pytest.fixture
def high_risk(
    monkeypatch,
    shipment_data,
):
    """
    Mock the model so the shipment passes the risk gate.
    """
    prediction = make_prediction(
        risk_level=RiskLevel.HIGH,
        probability=0.82,
        requires_investigation=True,
    )

    monkeypatch.setattr(
        agent_tools,
        "predict_delay_risk",
        lambda shipment_id: prediction,
    )

    return prediction


@pytest.fixture
def low_risk(
    monkeypatch,
    shipment_data,
):
    """
    Mock the model so the shipment is stopped by the risk gate.
    """
    prediction = make_prediction(
        risk_level=RiskLevel.LOW,
        probability=0.12,
        requires_investigation=False,
    )

    monkeypatch.setattr(
        agent_tools,
        "predict_delay_risk",
        lambda shipment_id: prediction,
    )

    return prediction