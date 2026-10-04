from functools import lru_cache
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from backend.models.schemas import ShipmentResponse


# ============================================================
# DATASET CONFIGURATION
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "shipment_tool_data.csv"
)


REQUIRED_COLUMNS = {
    "order_id",
    "shipment_id",
    "product_name",
    "category",
    "department",
    "market",
    "customer_country",
    "destination_country",
    "destination_region",
    "destination_state",
    "destination_city",
    "shipping_mode",
    "scheduled_shipping_days",
    "quantity",
    "product_price",
    "sales",
    "discount",
    "order_date",
    "latitude",
    "longitude",
    "historical_product_delay_rate",
    "historical_market_delay_rate",
    "historical_shipping_mode_delay_rate",
    "shipment_reference",
}


# ============================================================
# CUSTOM EXCEPTIONS
# ============================================================


class ShipmentServiceError(RuntimeError):
    """
    Base exception for Shipment Tool failures.
    """


class ShipmentDataUnavailableError(ShipmentServiceError):
    """
    Raised when the Shipment Tool dataset cannot be found or read.
    """


class ShipmentDataValidationError(ShipmentServiceError):
    """
    Raised when the Shipment Tool dataset has an invalid structure.
    """


class ShipmentNotFoundError(LookupError):
    """
    Raised when the requested shipment reference does not exist.
    """


class InvalidShipmentReferenceError(ValueError):
    """
    Raised when a shipment reference has an invalid format.
    """


# ============================================================
# SHIPMENT REFERENCE VALIDATION
# ============================================================


def normalize_shipment_reference(
    shipment_reference: str,
) -> str:
    """
    Validate and normalize a public shipment reference.

    The accepted format is SHP-<numeric shipment ID>.

    Example:
        SHP-153440
    """

    normalized_reference = shipment_reference.strip().upper()

    if not normalized_reference.startswith("SHP-"):
        raise InvalidShipmentReferenceError(
            "Invalid shipment reference. "
            "Expected format: SHP-<shipment_id>."
        )

    numeric_identifier = normalized_reference.removeprefix(
        "SHP-"
    ).strip()

    if not numeric_identifier:
        raise InvalidShipmentReferenceError(
            "Invalid shipment reference. "
            "The numeric shipment ID is missing."
        )

    if not numeric_identifier.isdigit():
        raise InvalidShipmentReferenceError(
            "Invalid shipment reference. "
            "The value after 'SHP-' must be numeric."
        )

    return f"SHP-{numeric_identifier}"


# ============================================================
# DATASET LOADING
# ============================================================


@lru_cache(maxsize=1)
def load_shipment_data() -> pd.DataFrame:
    """
    Load and validate the Shipment Tool dataset.

    The dataset is loaded once and cached in memory for subsequent
    shipment lookups.
    """

    if not DATA_PATH.exists():
        raise ShipmentDataUnavailableError(
            "Shipment Tool dataset was not found at "
            f"'{DATA_PATH}'."
        )

    try:
        dataframe = pd.read_csv(
            DATA_PATH,
            low_memory=False,
            dtype={
                "shipment_reference": "string",
                "product_name": "string",
                "category": "string",
                "department": "string",
                "market": "string",
                "customer_country": "string",
                "destination_country": "string",
                "destination_region": "string",
                "destination_state": "string",
                "destination_city": "string",
                "shipping_mode": "string",
                "order_date": "string",
            },
        )

    except Exception as exc:
        raise ShipmentDataUnavailableError(
            "The Shipment Tool dataset could not be read. "
            f"Original error: {exc}"
        ) from exc

    missing_columns = REQUIRED_COLUMNS.difference(
        dataframe.columns
    )

    if missing_columns:
        missing_columns_text = ", ".join(
            sorted(missing_columns)
        )

        raise ShipmentDataValidationError(
            "The Shipment Tool dataset is missing required "
            f"columns: {missing_columns_text}"
        )

    if dataframe.empty:
        raise ShipmentDataValidationError(
            "The Shipment Tool dataset contains no records."
        )

    dataframe["shipment_reference"] = (
        dataframe["shipment_reference"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    missing_references = (
        dataframe["shipment_reference"].isna().sum()
    )

    if missing_references:
        raise ShipmentDataValidationError(
            "The Shipment Tool dataset contains "
            f"{missing_references} missing shipment references."
        )

    duplicate_mask = dataframe[
        "shipment_reference"
    ].duplicated(keep=False)

    if duplicate_mask.any():
        duplicate_examples = (
            dataframe.loc[
                duplicate_mask,
                "shipment_reference",
            ]
            .dropna()
            .unique()
            .tolist()[:5]
        )

        examples_text = ", ".join(duplicate_examples)

        raise ShipmentDataValidationError(
            "The Shipment Tool dataset contains duplicate "
            "shipment references. "
            f"Examples: {examples_text}"
        )

    expected_references = (
        "SHP-"
        + dataframe["shipment_id"].astype(str)
    )

    mismatched_references = (
        dataframe["shipment_reference"]
        != expected_references
    )

    if mismatched_references.any():
        mismatch_count = int(
            mismatched_references.sum()
        )

        raise ShipmentDataValidationError(
            f"{mismatch_count} shipment references do not "
            "match the expected SHP-<shipment_id> format."
        )

    return dataframe


# ============================================================
# SHIPMENT TOOL
# ============================================================


def get_shipment_by_id(
    shipment_reference: str,
) -> ShipmentResponse:
    """
    Retrieve one shipment using its public shipment reference.

    This function keeps the original name to avoid breaking existing
    backend imports. Despite the function name, the lookup uses the
    public `shipment_reference`, such as SHP-153440.
    """

    normalized_reference = normalize_shipment_reference(
        shipment_reference
    )

    dataframe = load_shipment_data()

    matching_records = dataframe.loc[
        dataframe["shipment_reference"]
        == normalized_reference
    ]

    if matching_records.empty:
        raise ShipmentNotFoundError(
            f"Shipment '{normalized_reference}' was not found."
        )

    shipment_record = matching_records.iloc[0].to_dict()

    try:
        return ShipmentResponse.model_validate(
            shipment_record
        )

    except ValidationError as exc:
        raise ShipmentDataValidationError(
            "The shipment record exists but does not satisfy "
            "the API response contract. "
            f"Shipment: {normalized_reference}. "
            f"Validation error: {exc}"
        ) from exc


def get_shipment_status(
    shipment_reference: str,
) -> ShipmentResponse:
    """
    Agent-tool-friendly alias for shipment lookup.
    """

    return get_shipment_by_id(shipment_reference)


def clear_shipment_data_cache() -> None:
    """
    Clear the cached dataframe.

    This is useful during testing or after replacing the CSV while
    the application is running.
    """

    load_shipment_data.cache_clear()
