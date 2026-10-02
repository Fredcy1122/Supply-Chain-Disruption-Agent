"""
Deterministic tools used by the investigation agent.

Each tool wraps an existing backend service. The tools only retrieve
data: risk probabilities come from the prediction service and are never
recalculated here.
"""

from typing import Any

from backend.models.schemas import PredictionResponse, ShipmentResponse
from backend.services.prediction_service import predict_delay_risk
from backend.services.shipment_service import get_shipment_by_id


# ============================================================
# SHIPMENT TOOL
# ============================================================


def get_shipment(shipment_id: str) -> ShipmentResponse:
    """
    Retrieve the shipment record for a public shipment reference,
    such as SHP-153440.
    """

    return get_shipment_by_id(shipment_id)


# ============================================================
# RISK TOOL
# ============================================================


def get_delay_risk(shipment_id: str) -> PredictionResponse:
    """
    Return the model's delay probability and risk gate decision.
    """

    return predict_delay_risk(shipment_id)


# ============================================================
# HISTORICAL DELAY CONTEXT TOOL
# ============================================================


def get_historical_delay_context(
    shipment: ShipmentResponse,
) -> dict[str, Any]:
    """
    Report the historical delay rates recorded for the shipment's
    product, market and shipping mode.

    The rates are taken from the shipment record as they are. The
    factor with the highest rate is identified so the briefing can
    point to it; no new rates are estimated.
    """

    delay_rates = {
        "product": shipment.historical_product_delay_rate,
        "market": shipment.historical_market_delay_rate,
        "shipping_mode": shipment.historical_shipping_mode_delay_rate,
    }

    highest_factor = max(
        delay_rates,
        key=delay_rates.get,
    )

    return {
        "product_name": shipment.product_name,
        "market": shipment.market,
        "shipping_mode": shipment.shipping_mode,
        "scheduled_shipping_days": shipment.scheduled_shipping_days,
        "historical_delay_rates": delay_rates,
        "highest_delay_rate_factor": highest_factor,
    }
