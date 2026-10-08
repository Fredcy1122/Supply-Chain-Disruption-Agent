from pathlib import Path

import pandas as pd
import pytest

from backend.config import settings
from backend.exceptions import (
    InventoryNotFoundError,
    InventoryServiceError,
)
from backend.models.schemas import (
    InventoryStatusResponse,
    RiskLevel,
)
from backend.services.inventory_service import (
    calculate_stockout_risk,
    clear_inventory_cache,
    get_inventory_status,
    load_inventory_data,
    normalize_country,
    normalize_text,
)


EXPECTED_COLUMNS = [
    "inventory_id",
    "product_id",
    "product_name",
    "category",
    "department",
    "warehouse_id",
    "warehouse_location",
    "warehouse_country",
    "supplier_id",
    "current_stock",
    "reserved_stock",
    "available_stock",
    "daily_demand",
    "safety_stock",
    "reorder_point",
    "incoming_quantity",
    "expected_replenishment_date",
    "inventory_coverage_days",
    "stockout_risk",
    "data_source",
    "calculated_available_stock",
    "calculated_coverage",
]


@pytest.fixture
def inventory_records():
    return [
        {
            "inventory_id": "INV-LOW",
            "product_id": "PROD-LOW",
            "product_name": "Healthy Product",
            "category": "Cleats",
            "department": "Footwear",
            "warehouse_id": "WH-001",
            "warehouse_location": "Sao Paulo",
            "warehouse_country": "Brazil",
            "supplier_id": "SUP001",
            "current_stock": 1000,
            "reserved_stock": 200,
            "available_stock": 800,
            "daily_demand": 50,
            "safety_stock": 200,
            "reorder_point": 450,
            "incoming_quantity": 500,
            "expected_replenishment_date": "2017-06-23",
            "inventory_coverage_days": 16.0,
            "stockout_risk": "LOW",
            "data_source": "SYNTHETIC_MVP",
            "calculated_available_stock": 800,
            "calculated_coverage": 16.0,
        },
        {
            "inventory_id": "INV-MEDIUM",
            "product_id": "PROD-MEDIUM",
            "product_name": "Limited Product",
            "category": "Cleats",
            "department": "Footwear",
            "warehouse_id": "WH-002",
            "warehouse_location": "Dallas",
            "warehouse_country": "United States",
            "supplier_id": "SUP002",
            "current_stock": 400,
            "reserved_stock": 100,
            "available_stock": 300,
            "daily_demand": 50,
            "safety_stock": 200,
            "reorder_point": 450,
            "incoming_quantity": 200,
            "expected_replenishment_date": "2017-06-25",
            "inventory_coverage_days": 6.0,
            "stockout_risk": "MEDIUM",
            "data_source": "SYNTHETIC_MVP",
            "calculated_available_stock": 300,
            "calculated_coverage": 6.0,
        },
        {
            "inventory_id": "INV-HIGH",
            "product_id": "PROD-HIGH",
            "product_name": "Exposed Product",
            "category": "Cleats",
            "department": "Footwear",
            "warehouse_id": "WH-003",
            "warehouse_location": "Singapore",
            "warehouse_country": "Singapore",
            "supplier_id": "SUP003",
            "current_stock": 300,
            "reserved_stock": 100,
            "available_stock": 200,
            "daily_demand": 50,
            "safety_stock": 250,
            "reorder_point": 500,
            "incoming_quantity": 0,
            "expected_replenishment_date": None,
            "inventory_coverage_days": 4.0,
            "stockout_risk": "HIGH",
            "data_source": "SYNTHETIC_MVP",
            "calculated_available_stock": 200,
            "calculated_coverage": 4.0,
        },
    ]


@pytest.fixture
def inventory_data_path(
    tmp_path,
    monkeypatch,
    inventory_records,
):
    path = (
        tmp_path
        / "inventory_tool_data.csv"
    )

    pd.DataFrame(
        inventory_records,
        columns=EXPECTED_COLUMNS,
    ).to_csv(
        path,
        index=False,
    )

    monkeypatch.setattr(
        settings,
        "inventory_data_path",
        Path(path),
    )

    clear_inventory_cache()

    yield path

    clear_inventory_cache()


def test_inventory_dataset_is_synthetic(
    inventory_data_path,
):
    dataframe = load_inventory_data()

    assert not dataframe.empty

    assert (
        dataframe["data_source"]
        == "SYNTHETIC_MVP"
    ).all()


def test_inventory_dataset_contains_expected_rows(
    inventory_data_path,
):
    dataframe = load_inventory_data()

    assert len(dataframe) == 3

    assert dataframe[
        "inventory_id"
    ].is_unique

    assert dataframe[
        "product_id"
    ].is_unique


def test_inventory_lookup_returns_structured_status(
    inventory_data_path,
):
    result = get_inventory_status(
        product_name="Healthy Product",
        destination_country="Brasil",
    )

    assert isinstance(
        result,
        InventoryStatusResponse,
    )

    assert result.product_id == "PROD-LOW"
    assert result.available_stock == 800
    assert result.inventory_coverage_days == 16.0
    assert result.stockout_risk == RiskLevel.LOW
    assert result.calculation_verified is True
    assert result.destination_country_match is True
    assert result.data_source == "SYNTHETIC_MVP"


def test_inventory_lookup_is_case_and_accent_insensitive(
    inventory_data_path,
):
    result = get_inventory_status(
        product_name="  HEALTHY PRODUCT  ",
        destination_country="Brasil",
    )

    assert result.inventory_id == "INV-LOW"


def test_unknown_product_raises_controlled_error(
    inventory_data_path,
):
    with pytest.raises(
        InventoryNotFoundError,
        match="Unknown Product",
    ):
        get_inventory_status(
            product_name="Unknown Product",
            destination_country="Brasil",
        )


def test_empty_product_name_raises(
    inventory_data_path,
):
    with pytest.raises(
        ValueError,
        match="product name",
    ):
        get_inventory_status(
            product_name=" ",
            destination_country="Brasil",
        )


def test_empty_destination_country_raises(
    inventory_data_path,
):
    with pytest.raises(
        ValueError,
        match="destination country",
    ):
        get_inventory_status(
            product_name="Healthy Product",
            destination_country=" ",
        )


def test_medium_inventory_risk(
    inventory_data_path,
):
    result = get_inventory_status(
        product_name="Limited Product",
        destination_country="Brasil",
    )

    assert result.stockout_risk == RiskLevel.MEDIUM
    assert result.inventory_coverage_days == 6.0
    assert result.below_safety_stock is False
    assert result.below_reorder_point is True


def test_high_inventory_risk(
    inventory_data_path,
):
    result = get_inventory_status(
        product_name="Exposed Product",
        destination_country="Brasil",
    )

    assert result.stockout_risk == RiskLevel.HIGH
    assert result.below_safety_stock is True
    assert result.below_reorder_point is True
    assert result.expected_replenishment_date is None


def test_country_mismatch_is_disclosed(
    inventory_data_path,
):
    result = get_inventory_status(
        product_name="Limited Product",
        destination_country="Brasil",
    )

    assert result.destination_country_match is False

    assert (
        "does not match"
        in result.limitation
    )


@pytest.mark.parametrize(
    (
        "available_stock",
        "safety_stock",
        "coverage",
        "expected",
    ),
    [
        (
            200,
            250,
            4.0,
            RiskLevel.HIGH,
        ),
        (
            300,
            200,
            6.0,
            RiskLevel.MEDIUM,
        ),
        (
            800,
            200,
            16.0,
            RiskLevel.LOW,
        ),
    ],
)
def test_stockout_risk_policy(
    available_stock,
    safety_stock,
    coverage,
    expected,
):
    assert calculate_stockout_risk(
        available_stock=available_stock,
        safety_stock=safety_stock,
        inventory_coverage_days=coverage,
    ) == expected


def test_normalize_country_maps_dataco_names():
    assert normalize_country(
        "Brasil"
    ) == "brazil"

    assert normalize_country(
        "EE. UU."
    ) == "united states"

    assert normalize_country(
        "Reino Unido"
    ) == "united kingdom"

    assert normalize_country(
        "Países Bajos"
    ) == "netherlands"


def test_normalize_text_is_accent_insensitive():
    assert normalize_text(
        "São Paulo"
    ) == "sao paulo"


def test_inconsistent_available_stock_is_rejected(
    inventory_data_path,
):
    dataframe = pd.read_csv(
        inventory_data_path
    )

    dataframe.loc[
        0,
        "available_stock",
    ] = 799

    dataframe.to_csv(
        inventory_data_path,
        index=False,
    )

    clear_inventory_cache()

    with pytest.raises(
        InventoryServiceError,
        match="available_stock",
    ):
        load_inventory_data()


def test_inconsistent_coverage_is_rejected(
    inventory_data_path,
):
    dataframe = pd.read_csv(
        inventory_data_path
    )

    dataframe.loc[
        0,
        "inventory_coverage_days",
    ] = 99.0

    dataframe.to_csv(
        inventory_data_path,
        index=False,
    )

    clear_inventory_cache()

    with pytest.raises(
        InventoryServiceError,
        match="inventory_coverage_days",
    ):
        load_inventory_data()


def test_inconsistent_stockout_risk_is_rejected(
    inventory_data_path,
):
    dataframe = pd.read_csv(
        inventory_data_path
    )

    dataframe.loc[
        0,
        "stockout_risk",
    ] = "HIGH"

    dataframe.to_csv(
        inventory_data_path,
        index=False,
    )

    clear_inventory_cache()

    with pytest.raises(
        InventoryServiceError,
        match="classification mismatch",
    ):
        load_inventory_data()


def test_missing_replenishment_date_is_allowed(
    inventory_data_path,
):
    result = get_inventory_status(
        product_name="Exposed Product",
        destination_country="Brasil",
    )

    assert (
        result.expected_replenishment_date
        is None
    )


def test_real_inventory_dataset_is_valid(
    monkeypatch,
):
    real_path = (
        Path(__file__).resolve()
        .parents[1]
        / "data"
        / "processed"
        / "inventory_tool_data.csv"
    )

    monkeypatch.setattr(
        settings,
        "inventory_data_path",
        real_path,
    )

    clear_inventory_cache()

    dataframe = load_inventory_data()

    assert len(dataframe) == 73

    assert (
        dataframe["product_name"]
        .nunique()
        == 73
    )

    assert (
        dataframe["data_source"]
        == "SYNTHETIC_MVP"
    ).all()