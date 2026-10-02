from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from backend.config import settings
from backend.exceptions import ModelFeatureError


MODEL_IDENTIFIER_CANDIDATES = (
    "Order Item Id",
    "order_item_id",
    "shipment_id",
    "shipment_reference",
)


def normalize_order_item_id(shipment_id: str) -> str:
    """
    Extract the DataCo Order Item Id from a public shipment ID.

    Example:
        SHP-153440 becomes 153440.
    """
    normalized = str(shipment_id).strip().upper()

    if not normalized.startswith("SHP-"):
        raise ModelFeatureError(
            "Invalid shipment ID. Expected format: "
            "SHP-<Order Item Id>."
        )

    order_item_id = normalized.removeprefix("SHP-").strip()

    if not order_item_id:
        raise ModelFeatureError(
            "The shipment ID does not contain an Order Item Id."
        )

    return order_item_id


@lru_cache(maxsize=1)
def load_model_data() -> pd.DataFrame:
    """
    Load and cache the model-input dataset.

    The dataset is loaded once per backend process instead of once for
    every prediction request.
    """
    model_data_path = Path(settings.model_data_path)

    if not model_data_path.exists():
        raise ModelFeatureError(
            "The model-input dataset was not found at: "
            f"{model_data_path}"
        )

    try:
        dataframe = pd.read_csv(
            model_data_path,
            low_memory=False,
        )
    except Exception as exc:
        raise ModelFeatureError(
            "Unable to load the model-input dataset from "
            f"'{model_data_path}': {exc}"
        ) from exc

    if dataframe.empty:
        raise ModelFeatureError(
            "The model-input dataset is empty."
        )

    return dataframe


def find_identifier_column(
    dataframe: pd.DataFrame,
) -> str:
    """
    Find the item-level identifier used by the model dataset.
    """
    for column in MODEL_IDENTIFIER_CANDIDATES:
        if column in dataframe.columns:
            return column

    raise ModelFeatureError(
        "The model-input dataset does not contain a supported "
        "shipment identifier. Expected one of: "
        + ", ".join(MODEL_IDENTIFIER_CANDIDATES)
    )


def normalize_identifier_series(
    series: pd.Series,
    identifier_column: str,
) -> pd.Series:
    """
    Normalize an identifier column for item-level shipment lookup.
    """
    normalized = (
        series
        .astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )

    if identifier_column in {
        "shipment_id",
        "shipment_reference",
    }:
        normalized = normalized.str.upper().str.removeprefix(
            "SHP-"
        )

    return normalized


def get_model_feature_row(
    shipment_id: str,
    expected_features: list[str],
) -> pd.DataFrame:
    """
    Retrieve the exact raw model-input row for a shipment.

    Only columns expected by the fitted preprocessor are returned.
    """
    if not expected_features:
        raise ModelFeatureError(
            "The model's expected feature list is empty."
        )

    dataframe = load_model_data()
    identifier_column = find_identifier_column(dataframe)

    order_item_id = normalize_order_item_id(shipment_id)

    normalized_identifiers = normalize_identifier_series(
        dataframe[identifier_column],
        identifier_column,
    )

    matches = dataframe.loc[
        normalized_identifiers == order_item_id
    ]

    if matches.empty:
        raise ModelFeatureError(
            "No model-input record was found for shipment "
            f"'{shipment_id}' using identifier column "
            f"'{identifier_column}'."
        )

    if len(matches) > 1:
        raise ModelFeatureError(
            "Multiple model-input records were found for shipment "
            f"'{shipment_id}'. The model dataset must contain one "
            "item-level record per shipment."
        )

    missing_features = [
        feature
        for feature in expected_features
        if feature not in dataframe.columns
    ]

    if missing_features:
        raise ModelFeatureError(
            "The model-input dataset does not contain all fields "
            "required by the fitted preprocessor. Missing fields: "
            + ", ".join(missing_features)
        )

    feature_row = matches.loc[
        :,
        expected_features,
    ].copy()

    if feature_row.empty:
        raise ModelFeatureError(
            "Model feature lookup produced an empty DataFrame."
        )

    if feature_row.shape[0] != 1:
        raise ModelFeatureError(
            "Model feature lookup must return exactly one row."
        )

    all_missing_columns = [
        column
        for column in expected_features
        if feature_row[column].isna().all()
    ]

    if all_missing_columns:
        raise ModelFeatureError(
            "The model-input record contains completely missing "
            "required fields: "
            + ", ".join(all_missing_columns)
        )

    return feature_row


def describe_model_feature_contract(
    expected_features: list[str],
) -> dict[str, Any]:
    """
    Return diagnostic information about the model-data contract.
    """
    dataframe = load_model_data()
    identifier_column = find_identifier_column(dataframe)

    available_features = [
        feature
        for feature in expected_features
        if feature in dataframe.columns
    ]

    missing_features = [
        feature
        for feature in expected_features
        if feature not in dataframe.columns
    ]

    return {
        "model_data_path": str(settings.model_data_path),
        "row_count": len(dataframe),
        "column_count": len(dataframe.columns),
        "identifier_column": identifier_column,
        "expected_feature_count": len(expected_features),
        "available_feature_count": len(available_features),
        "missing_feature_count": len(missing_features),
        "missing_features": missing_features,
    }


def clear_model_data_cache() -> None:
    """
    Clear the cached model dataset for tests or dataset replacement.
    """
    load_model_data.cache_clear()