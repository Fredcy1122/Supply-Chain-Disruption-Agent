from functools import lru_cache
from pathlib import Path
from typing import Any
import unicodedata

import pandas as pd

from backend.config import settings
from backend.exceptions import (
    InventoryNotFoundError,
    InventoryServiceError,
)
from backend.models.schemas import (
    InventoryStatusResponse,
    RiskLevel,
)


REQUIRED_COLUMNS = {
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
}


REQUIRED_TEXT_COLUMNS = [
    "inventory_id",
    "product_id",
    "product_name",
    "category",
    "department",
    "warehouse_id",
    "warehouse_location",
    "warehouse_country",
    "supplier_id",
    "stockout_risk",
    "data_source",
]


NUMERIC_COLUMNS = [
    "current_stock",
    "reserved_stock",
    "available_stock",
    "daily_demand",
    "safety_stock",
    "reorder_point",
    "incoming_quantity",
    "inventory_coverage_days",
    "calculated_available_stock",
    "calculated_coverage",
]


INTEGER_COLUMNS = [
    "current_stock",
    "reserved_stock",
    "available_stock",
    "daily_demand",
    "safety_stock",
    "reorder_point",
    "incoming_quantity",
    "calculated_available_stock",
]


COUNTRY_ALIASES = {
    "brasil": "brazil",
    "ee. uu.": "united states",
    "estados unidos": "united states",
    "reino unido": "united kingdom",
    "paises bajos": "netherlands",
    "francia": "france",
    "alemania": "germany",
    "japon": "japan",
    "canada": "canada",
    "espana": "spain",
}


CALCULATION_TOLERANCE = 0.02


def normalize_text(
    value: str,
) -> str:
    """
    Normalize text for case-insensitive and accent-insensitive matching.
    """
    normalized = unicodedata.normalize(
        "NFKD",
        str(value).strip(),
    )

    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(
            character
        )
    ).casefold()


def normalize_country(
    value: str,
) -> str:
    """
    Normalize country names and known DataCo country aliases.
    """
    normalized = normalize_text(
        value
    )

    return COUNTRY_ALIASES.get(
        normalized,
        normalized,
    )


def calculate_stockout_risk(
    available_stock: int,
    safety_stock: int,
    inventory_coverage_days: float,
) -> RiskLevel:
    """
    Calculate stockout risk using the policy used to generate the
    synthetic inventory dataset.

    HIGH:
        Available stock is at or below safety stock.

    MEDIUM:
        Available stock is above safety stock but coverage is seven
        days or less.

    LOW:
        Available stock is above safety stock and coverage is more
        than seven days.
    """
    if available_stock <= safety_stock:
        return RiskLevel.HIGH

    if inventory_coverage_days <= 7:
        return RiskLevel.MEDIUM

    return RiskLevel.LOW


def _validate_required_values(
    dataframe: pd.DataFrame,
) -> None:
    """
    Validate required text and numeric values.
    """
    required_columns = (
        REQUIRED_TEXT_COLUMNS
        + NUMERIC_COLUMNS
    )

    missing_counts = (
        dataframe[required_columns]
        .isna()
        .sum()
    )

    missing_counts = missing_counts[
        missing_counts > 0
    ]

    if not missing_counts.empty:
        raise InventoryServiceError(
            "The inventory dataset contains missing or invalid "
            "required values: "
            + ", ".join(
                f"{column}={int(count)}"
                for column, count
                in missing_counts.items()
            )
        )

    empty_text_counts = {
        column: int(
            dataframe[column]
            .astype(str)
            .str.strip()
            .eq("")
            .sum()
        )
        for column in REQUIRED_TEXT_COLUMNS
    }

    empty_text_counts = {
        column: count
        for column, count
        in empty_text_counts.items()
        if count > 0
    }

    if empty_text_counts:
        raise InventoryServiceError(
            "The inventory dataset contains empty required text "
            "values: "
            + ", ".join(
                f"{column}={count}"
                for column, count
                in empty_text_counts.items()
            )
        )


def _validate_unique_records(
    dataframe: pd.DataFrame,
) -> None:
    """
    Validate inventory and product uniqueness.
    """
    unique_columns = [
        "inventory_id",
        "product_id",
        "_normalized_product_name",
    ]

    for column in unique_columns:
        duplicates = dataframe[
            column
        ].duplicated(
            keep=False
        )

        if duplicates.any():
            duplicate_count = int(
                duplicates.sum()
            )

            raise InventoryServiceError(
                f"Column '{column}' contains "
                f"{duplicate_count} duplicate record(s)."
            )


def _validate_numeric_values(
    dataframe: pd.DataFrame,
) -> None:
    """
    Validate inventory quantities and demand values.
    """
    non_negative_columns = [
        "current_stock",
        "reserved_stock",
        "available_stock",
        "safety_stock",
        "reorder_point",
        "incoming_quantity",
        "inventory_coverage_days",
        "calculated_available_stock",
        "calculated_coverage",
    ]

    for column in non_negative_columns:
        invalid = (
            dataframe[column] < 0
        )

        if invalid.any():
            raise InventoryServiceError(
                f"Column '{column}' contains "
                f"{int(invalid.sum())} negative value(s)."
            )

    invalid_daily_demand = (
        dataframe["daily_demand"] <= 0
    )

    if invalid_daily_demand.any():
        raise InventoryServiceError(
            "'daily_demand' contains "
            f"{int(invalid_daily_demand.sum())} "
            "non-positive value(s)."
        )

    reserved_exceeds_current = (
        dataframe["reserved_stock"]
        > dataframe["current_stock"]
    )

    if reserved_exceeds_current.any():
        raise InventoryServiceError(
            "'reserved_stock' exceeds 'current_stock' in "
            f"{int(reserved_exceeds_current.sum())} record(s)."
        )


def _validate_calculations(
    dataframe: pd.DataFrame,
) -> None:
    """
    Validate stock and coverage calculations.
    """
    expected_available_stock = (
        dataframe["current_stock"]
        - dataframe["reserved_stock"]
    )

    available_matches = (
        dataframe["available_stock"]
        == expected_available_stock
    )

    calculated_available_matches = (
        dataframe[
            "calculated_available_stock"
        ]
        == expected_available_stock
    )

    if not available_matches.all():
        raise InventoryServiceError(
            "'available_stock' does not equal current stock minus "
            "reserved stock in "
            f"{int((~available_matches).sum())} record(s)."
        )

    if not calculated_available_matches.all():
        raise InventoryServiceError(
            "'calculated_available_stock' is inconsistent in "
            f"{int((~calculated_available_matches).sum())} record(s)."
        )

    expected_coverage = (
        expected_available_stock
        / dataframe["daily_demand"]
    )

    supplied_coverage_difference = (
        dataframe["inventory_coverage_days"]
        - expected_coverage
    ).abs()

    calculated_coverage_difference = (
        dataframe["calculated_coverage"]
        - expected_coverage
    ).abs()

    supplied_coverage_matches = (
        supplied_coverage_difference
        <= CALCULATION_TOLERANCE
    )

    calculated_coverage_matches = (
        calculated_coverage_difference
        <= CALCULATION_TOLERANCE
    )

    if not supplied_coverage_matches.all():
        raise InventoryServiceError(
            "'inventory_coverage_days' is inconsistent in "
            f"{int((~supplied_coverage_matches).sum())} record(s)."
        )

    if not calculated_coverage_matches.all():
        raise InventoryServiceError(
            "'calculated_coverage' is inconsistent in "
            f"{int((~calculated_coverage_matches).sum())} record(s)."
        )


def _validate_risk_classifications(
    dataframe: pd.DataFrame,
) -> None:
    """
    Validate stored stockout-risk classifications.
    """
    valid_risk_levels = {
        risk_level.value
        for risk_level in RiskLevel
    }

    invalid_risk_levels = (
        set(
            dataframe["stockout_risk"]
        )
        - valid_risk_levels
    )

    if invalid_risk_levels:
        raise InventoryServiceError(
            "The inventory dataset contains unsupported stockout "
            "risk levels: "
            + ", ".join(
                sorted(
                    invalid_risk_levels
                )
            )
        )

    calculated_risk = dataframe.apply(
        lambda row: calculate_stockout_risk(
            available_stock=int(
                row["available_stock"]
            ),
            safety_stock=int(
                row["safety_stock"]
            ),
            inventory_coverage_days=float(
                row["inventory_coverage_days"]
            ),
        ).value,
        axis=1,
    )

    matches = (
        calculated_risk
        == dataframe["stockout_risk"]
    )

    if not matches.all():
        raise InventoryServiceError(
            "The inventory dataset contains "
            f"{int((~matches).sum())} stockout-risk "
            "classification mismatch(es)."
        )


def _validate_replenishment_dates(
    dataframe: pd.DataFrame,
) -> None:
    """
    Validate optional replenishment dates.
    """
    raw_dates = (
        dataframe[
            "expected_replenishment_date"
        ]
    )

    parsed_dates = pd.to_datetime(
        raw_dates,
        errors="coerce",
    )

    invalid_dates = (
        raw_dates.notna()
        & raw_dates.astype(str)
        .str.strip()
        .ne("")
        & parsed_dates.isna()
    )

    if invalid_dates.any():
        raise InventoryServiceError(
            "'expected_replenishment_date' contains "
            f"{int(invalid_dates.sum())} invalid date value(s)."
        )

    dataframe[
        "_parsed_replenishment_date"
    ] = parsed_dates


@lru_cache(maxsize=1)
def load_inventory_data() -> pd.DataFrame:
    """
    Load, validate, normalize, and cache the synthetic inventory
    dataset.
    """
    inventory_path = Path(
        settings.inventory_data_path
    )

    if not inventory_path.exists():
        raise InventoryServiceError(
            "Inventory data was not found at: "
            f"{inventory_path}"
        )

    try:
        dataframe = pd.read_csv(
            inventory_path,
            low_memory=False,
        )
    except Exception as exc:
        raise InventoryServiceError(
            "Unable to load inventory data from "
            f"'{inventory_path}': {exc}"
        ) from exc

    if dataframe.empty:
        raise InventoryServiceError(
            "The inventory dataset is empty."
        )

    missing_columns = (
        REQUIRED_COLUMNS
        - set(
            dataframe.columns
        )
    )

    if missing_columns:
        raise InventoryServiceError(
            "The inventory dataset is missing columns: "
            + ", ".join(
                sorted(
                    missing_columns
                )
            )
        )

    dataframe = dataframe.copy()

    for column in REQUIRED_TEXT_COLUMNS:
        dataframe[column] = (
            dataframe[column]
            .astype("string")
            .str.strip()
        )

    for column in NUMERIC_COLUMNS:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    _validate_required_values(
        dataframe
    )

    for column in INTEGER_COLUMNS:
        fractional_values = (
            dataframe[column] % 1
        ).ne(0)

        if fractional_values.any():
            raise InventoryServiceError(
                f"Column '{column}' contains "
                f"{int(fractional_values.sum())} "
                "non-integer value(s)."
            )

        dataframe[column] = (
            dataframe[column]
            .astype(int)
        )

    dataframe["data_source"] = (
        dataframe["data_source"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    if not dataframe[
        "data_source"
    ].eq(
        "SYNTHETIC_MVP"
    ).all():
        raise InventoryServiceError(
            "Every inventory record must be labelled "
            "'SYNTHETIC_MVP'."
        )

    dataframe["stockout_risk"] = (
        dataframe["stockout_risk"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    dataframe[
        "_normalized_product_name"
    ] = (
        dataframe["product_name"]
        .map(
            normalize_text
        )
    )

    dataframe[
        "_normalized_warehouse_country"
    ] = (
        dataframe["warehouse_country"]
        .map(
            normalize_country
        )
    )

    _validate_unique_records(
        dataframe
    )

    _validate_numeric_values(
        dataframe
    )

    _validate_calculations(
        dataframe
    )

    _validate_risk_classifications(
        dataframe
    )

    _validate_replenishment_dates(
        dataframe
    )

    return dataframe


def _row_to_inventory_status(
    row: pd.Series,
    destination_country: str,
) -> InventoryStatusResponse:
    """
    Convert one inventory row into the public response schema.
    """
    normalized_destination = (
        normalize_country(
            destination_country
        )
    )

    country_match = (
        row[
            "_normalized_warehouse_country"
        ]
        == normalized_destination
    )

    expected_date = row[
        "_parsed_replenishment_date"
    ]

    expected_replenishment_date = (
        None
        if pd.isna(expected_date)
        else expected_date.date()
    )

    available_stock = int(
        row["available_stock"]
    )

    safety_stock = int(
        row["safety_stock"]
    )

    reorder_point = int(
        row["reorder_point"]
    )

    coverage = float(
        row["inventory_coverage_days"]
    )

    limitation_parts = [
        (
            "Inventory records are synthetic demonstration data "
            "and do not represent live warehouse stock."
        ),
        (
            "Available stock, reservations, average demand, and "
            "incoming replenishment require operational validation."
        ),
    ]

    if country_match:
        limitation_parts.append(
            "The synthetic warehouse country matches the normalized "
            "shipment destination country."
        )
    else:
        limitation_parts.append(
            "The synthetic warehouse country does not match the "
            "shipment destination country, so geographic suitability "
            "requires additional review."
        )

    if int(
        row["incoming_quantity"]
    ) > 0:
        if expected_replenishment_date is None:
            limitation_parts.append(
                "Incoming inventory is recorded, but no expected "
                "replenishment date is available."
            )
        else:
            limitation_parts.append(
                "Incoming inventory is recorded, but its arrival "
                "and availability are not verified."
            )

    calculation_verified = (
        int(
            row[
                "calculated_available_stock"
            ]
        )
        == available_stock
        and abs(
            float(
                row[
                    "calculated_coverage"
                ]
            )
            - coverage
        )
        <= CALCULATION_TOLERANCE
    )

    return InventoryStatusResponse(
        inventory_id=str(
            row["inventory_id"]
        ),
        product_id=str(
            row["product_id"]
        ),
        product_name=str(
            row["product_name"]
        ),
        category=str(
            row["category"]
        ),
        department=str(
            row["department"]
        ),
        warehouse_id=str(
            row["warehouse_id"]
        ),
        warehouse_location=str(
            row["warehouse_location"]
        ),
        warehouse_country=str(
            row["warehouse_country"]
        ),
        supplier_id=str(
            row["supplier_id"]
        ),
        current_stock=int(
            row["current_stock"]
        ),
        reserved_stock=int(
            row["reserved_stock"]
        ),
        available_stock=available_stock,
        daily_demand=int(
            row["daily_demand"]
        ),
        safety_stock=safety_stock,
        reorder_point=reorder_point,
        incoming_quantity=int(
            row["incoming_quantity"]
        ),
        expected_replenishment_date=(
            expected_replenishment_date
        ),
        inventory_coverage_days=round(
            coverage,
            2,
        ),
        stockout_risk=RiskLevel(
            str(
                row["stockout_risk"]
            )
        ),
        below_safety_stock=(
            available_stock
            <= safety_stock
        ),
        below_reorder_point=(
            available_stock
            <= reorder_point
        ),
        calculation_verified=(
            calculation_verified
        ),
        destination_country=(
            destination_country
        ),
        destination_country_match=bool(
            country_match
        ),
        data_source=str(
            row["data_source"]
        ),
        limitation=" ".join(
            limitation_parts
        ),
    )


def get_inventory_status(
    product_name: str,
    destination_country: str,
) -> InventoryStatusResponse:
    """
    Return synthetic inventory evidence for an exact shipment product.

    Product matching is exact after case and accent normalization.
    Fuzzy and category-level matching are intentionally excluded
    because all shipment products have exact inventory matches.
    """
    normalized_product = (
        normalize_text(
            product_name
        )
    )

    if not normalized_product:
        raise ValueError(
            "The product name cannot be empty."
        )

    normalized_destination = (
        normalize_country(
            destination_country
        )
    )

    if not normalized_destination:
        raise ValueError(
            "The destination country cannot be empty."
        )

    dataframe = load_inventory_data()

    matches = dataframe.loc[
        dataframe[
            "_normalized_product_name"
        ]
        == normalized_product
    ]

    if matches.empty:
        raise InventoryNotFoundError(
            "No synthetic inventory record was found for "
            f"product '{product_name}'."
        )

    if len(matches) > 1:
        raise InventoryServiceError(
            "Multiple synthetic inventory records were found for "
            f"product '{product_name}'."
        )

    return _row_to_inventory_status(
        row=matches.iloc[0],
        destination_country=(
            destination_country
        ),
    )


def clear_inventory_cache() -> None:
    """
    Clear cached inventory data for tests or dataset replacement.
    """
    load_inventory_data.cache_clear()