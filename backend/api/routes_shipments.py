from fastapi import APIRouter, HTTPException, status

from backend.models.schemas import ShipmentResponse
from backend.services.shipment_service import (
    InvalidShipmentReferenceError,
    ShipmentDataUnavailableError,
    ShipmentDataValidationError,
    ShipmentNotFoundError,
    get_shipment_by_id,
)


router = APIRouter(
    prefix="/api/shipments",
    tags=["Shipments"],
)


@router.get(
    "/{shipment_reference}",
    response_model=ShipmentResponse,
    summary="Retrieve a shipment",
    description=(
        "Retrieve leakage-safe shipment information using a public "
        "shipment reference such as SHP-153440."
    ),
)
def fetch_shipment(
    shipment_reference: str,
) -> ShipmentResponse:
    """
    Retrieve a shipment from shipment_tool_data.csv.

    Possible responses:

    - 200: Shipment successfully retrieved
    - 400: Invalid shipment reference format
    - 404: Shipment does not exist
    - 422: Shipment record violates the API contract
    - 503: Shipment dataset is missing, unreadable, or invalid
    """

    try:
        return get_shipment_by_id(
            shipment_reference
        )

    except InvalidShipmentReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except ShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ShipmentDataValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except ShipmentDataUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc