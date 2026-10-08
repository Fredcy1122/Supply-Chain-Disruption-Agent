from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from backend.exceptions import (
    InventoryNotFoundError,
    InventoryServiceError,
)
from backend.models.schemas import (
    InventoryStatusResponse,
)
from backend.services.inventory_service import (
    get_inventory_status,
)
from backend.services.shipment_service import (
    InvalidShipmentReferenceError,
    ShipmentDataUnavailableError,
    ShipmentDataValidationError,
    ShipmentNotFoundError,
    get_shipment_by_id,
)


router = APIRouter(
    prefix="/api/inventory",
    tags=["Inventory"],
)


@router.get(
    "/shipment/{shipment_reference}",
    response_model=InventoryStatusResponse,
    summary="Retrieve inventory evidence for a shipment",
    description=(
        "Retrieve synthetic inventory evidence for the product "
        "associated with a public shipment reference such as "
        "SHP-153440."
    ),
)
def fetch_shipment_inventory(
    shipment_reference: str,
) -> InventoryStatusResponse:
    """
    Retrieve synthetic inventory evidence for a shipment.

    The endpoint first retrieves the leakage-safe shipment record,
    then matches its product name to the synthetic Inventory Tool
    dataset.

    Possible responses:

    - 200: Inventory evidence successfully retrieved
    - 400: Invalid shipment-reference format
    - 404: Shipment or matching inventory record does not exist
    - 422: Shipment record violates the API contract
    - 503: Shipment or inventory data is unavailable or invalid
    """
    try:
        shipment = get_shipment_by_id(
            shipment_reference
        )

        return get_inventory_status(
            product_name=(
                shipment.product_name
            ),
            destination_country=(
                shipment.destination_country
            ),
        )

    except InvalidShipmentReferenceError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except ShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(exc),
        ) from exc

    except InventoryNotFoundError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(exc),
        ) from exc

    except ShipmentDataValidationError as exc:
        raise HTTPException(
            status_code=(
                status
                .HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=str(exc),
        ) from exc

    except ShipmentDataUnavailableError as exc:
        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=str(exc),
        ) from exc

    except InventoryServiceError as exc:
        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=str(exc),
        ) from exc