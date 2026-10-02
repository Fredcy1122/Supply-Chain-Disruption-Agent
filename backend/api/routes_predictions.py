from fastapi import APIRouter, HTTPException, status

from backend.exceptions import (
    ModelArtifactError,
    ModelFeatureError,
    ModelInferenceError,
    ThresholdConfigurationError,
)
from backend.models.schemas import PredictionResponse
from backend.services.prediction_service import (
    predict_delay_risk,
)
from backend.services.shipment_service import (
    ShipmentDataError,
    ShipmentNotFoundError,
)


router = APIRouter(
    prefix="/api/predictions",
    tags=["Predictions & Risk Gate"],
)


@router.post(
    "/evaluate/{shipment_id}",
    response_model=PredictionResponse,
)
def evaluate_shipment_risk(
    shipment_id: str,
) -> PredictionResponse:
    """
    Run real ML inference and determine whether an investigation should
    be triggered.
    """
    try:
        return predict_delay_risk(shipment_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except ShipmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ShipmentDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except (
        ModelArtifactError,
        ModelFeatureError,
        ModelInferenceError,
        ThresholdConfigurationError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc