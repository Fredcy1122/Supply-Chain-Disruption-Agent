from fastapi import APIRouter, HTTPException
from backend.models.schemas import PredictionResponse
from backend.services.prediction_service import predict_delay_risk

router = APIRouter(prefix="/api/predictions", tags=["Predictions & Risk Gate"])

@router.post("/evaluate/{shipment_id}", response_model=PredictionResponse)
def evaluate_shipment_risk(shipment_id: str):
    """
    Run ML inference on a shipment and determine whether an AI agent 
    investigation is triggered.
    """
    try:
        prediction = predict_delay_risk(shipment_id)
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction evaluation failed: {str(e)}")