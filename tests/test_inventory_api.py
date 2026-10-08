from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import (
    TestClient,
)

from backend.api import (
    routes_inventory,
)
from backend.exceptions import (
    InventoryNotFoundError,
    InventoryServiceError,
)
from backend.models.schemas import (
    InventoryStatusResponse,
    RiskLevel,
)
from backend.services.shipment_service import (
    InvalidShipmentReferenceError,
    ShipmentDataUnavailableError,
    ShipmentDataValidationError,
    ShipmentNotFoundError,
)


@pytest.fixture
def client():
    app = FastAPI()

    app.include_router(
        routes_inventory.router
    )

    return TestClient(
        app
    )


def make_inventory_status():
    """
    Create deterministic inventory evidence for API tests.
    """
    return InventoryStatusResponse(
        inventory_id="INV-TEST",
        product_id="PROD-TEST",
        product_name="Trail Running Shoe",
        category="Cleats",
        department="Footwear",
        warehouse_id="WH-TEST",
        warehouse_location="Sao Paulo",
        warehouse_country="Brazil",
        supplier_id="SUP-TEST",
        current_stock=400,
        reserved_stock=100,
        available_stock=300,
        daily_demand=50,
        safety_stock=200,
        reorder_point=450,
        incoming_quantity=200,
        expected_replenishment_date=date(
            2017,
            5,
            8,
        ),
        inventory_coverage_days=6.0,
        stockout_risk=RiskLevel.MEDIUM,
        below_safety_stock=False,
        below_reorder_point=True,
        calculation_verified=True,
        destination_country="Brasil",
        destination_country_match=True,
        data_source="SYNTHETIC_MVP",
        limitation=(
            "Inventory records are synthetic "
            "demonstration data."
        ),
    )


def test_inventory_endpoint_returns_structured_evidence(
    client,
    shipment,
    monkeypatch,
):
    expected = (
        make_inventory_status()
    )

    calls = []

    monkeypatch.setattr(
        routes_inventory,
        "get_shipment_by_id",
        lambda reference: shipment,
    )

    def fake_inventory_status(
        product_name,
        destination_country,
    ):
        calls.append(
            {
                "product_name":
                    product_name,
                "destination_country":
                    destination_country,
            }
        )

        return expected

    monkeypatch.setattr(
        routes_inventory,
        "get_inventory_status",
        fake_inventory_status,
    )

    response = client.get(
        "/api/inventory/shipment/"
        "SHP-153440"
    )

    assert response.status_code == 200

    body = response.json()

    InventoryStatusResponse.model_validate(
        body
    )

    assert (
        body["product_name"]
        == "Trail Running Shoe"
    )

    assert (
        body["available_stock"]
        == 300
    )

    assert (
        body[
            "inventory_coverage_days"
        ]
        == 6.0
    )

    assert (
        body["stockout_risk"]
        == "MEDIUM"
    )

    assert (
        body["data_source"]
        == "SYNTHETIC_MVP"
    )

    assert calls == [
        {
            "product_name":
                "Trail Running Shoe",
            "destination_country":
                "Brasil",
        },
    ]


def test_inventory_endpoint_returns_400_for_invalid_reference(
    client,
    monkeypatch,
):
    def invalid_reference(
        reference,
    ):
        raise InvalidShipmentReferenceError(
            "Invalid shipment reference."
        )

    monkeypatch.setattr(
        routes_inventory,
        "get_shipment_by_id",
        invalid_reference,
    )

    response = client.get(
        "/api/inventory/shipment/"
        "not-a-shipment"
    )

    assert response.status_code == 400

    assert response.json() == {
        "detail": (
            "Invalid shipment reference."
        ),
    }


def test_inventory_endpoint_returns_404_for_unknown_shipment(
    client,
    monkeypatch,
):
    def shipment_not_found(
        reference,
    ):
        raise ShipmentNotFoundError(
            f"Shipment '{reference}' "
            "was not found."
        )

    monkeypatch.setattr(
        routes_inventory,
        "get_shipment_by_id",
        shipment_not_found,
    )

    response = client.get(
        "/api/inventory/shipment/"
        "SHP-999999"
    )

    assert response.status_code == 404

    assert (
        "was not found"
        in response.json()["detail"]
    )


def test_inventory_endpoint_returns_404_when_inventory_is_missing(
    client,
    shipment,
    monkeypatch,
):
    monkeypatch.setattr(
        routes_inventory,
        "get_shipment_by_id",
        lambda reference: shipment,
    )

    def inventory_not_found(
        product_name,
        destination_country,
    ):
        raise InventoryNotFoundError(
            "No synthetic inventory record "
            "was found."
        )

    monkeypatch.setattr(
        routes_inventory,
        "get_inventory_status",
        inventory_not_found,
    )

    response = client.get(
        "/api/inventory/shipment/"
        "SHP-153440"
    )

    assert response.status_code == 404

    assert (
        "No synthetic inventory record"
        in response.json()["detail"]
    )


def test_inventory_endpoint_returns_422_for_invalid_shipment_record(
    client,
    monkeypatch,
):
    def invalid_shipment_data(
        reference,
    ):
        raise ShipmentDataValidationError(
            "Shipment record is invalid."
        )

    monkeypatch.setattr(
        routes_inventory,
        "get_shipment_by_id",
        invalid_shipment_data,
    )

    response = client.get(
        "/api/inventory/shipment/"
        "SHP-153440"
    )

    assert response.status_code == 422

    assert response.json() == {
        "detail": (
            "Shipment record is invalid."
        ),
    }


def test_inventory_endpoint_returns_503_when_shipment_data_is_unavailable(
    client,
    monkeypatch,
):
    def unavailable_shipment_data(
        reference,
    ):
        raise ShipmentDataUnavailableError(
            "Shipment dataset unavailable."
        )

    monkeypatch.setattr(
        routes_inventory,
        "get_shipment_by_id",
        unavailable_shipment_data,
    )

    response = client.get(
        "/api/inventory/shipment/"
        "SHP-153440"
    )

    assert response.status_code == 503

    assert response.json() == {
        "detail": (
            "Shipment dataset unavailable."
        ),
    }


def test_inventory_endpoint_returns_503_when_inventory_service_fails(
    client,
    shipment,
    monkeypatch,
):
    monkeypatch.setattr(
        routes_inventory,
        "get_shipment_by_id",
        lambda reference: shipment,
    )

    def inventory_failure(
        product_name,
        destination_country,
    ):
        raise InventoryServiceError(
            "Inventory dataset unavailable."
        )

    monkeypatch.setattr(
        routes_inventory,
        "get_inventory_status",
        inventory_failure,
    )

    response = client.get(
        "/api/inventory/shipment/"
        "SHP-153440"
    )

    assert response.status_code == 503

    assert response.json() == {
        "detail": (
            "Inventory dataset unavailable."
        ),
    }