from fastapi import APIRouter, HTTPException
from backend.models.schemas import DisruptionBriefingResponse
from backend.services.agent_service import run_investigation
from backend.services.shipment_service import ShipmentNotFoundError

router = APIRouter(prefix="/api/agent", tags=["AI Agent Investigation"])

@router.post("/investigate/{shipment_id}", response_model=DisruptionBriefingResponse)
def investigate_shipment(shipment_id: str):
    """
    Triggers the AI Agent to investigate a high-risk shipment, gather evidence,
    and generate an actionable disruption briefing.
    """
    try:
        briefing = run_investigation(shipment_id)
        return briefing
    except ValueError as ve:
        # A 400 Bad Request if the user tries to investigate a safe shipment
        raise HTTPException(status_code=400, detail=str(ve))
    except ShipmentNotFoundError as nf:
        # A 404 Not Found if the shipment reference does not exist
        raise HTTPException(status_code=404, detail=str(nf))
    except Exception as e:
        # A 500 Internal Server Error if the LLM or tools fail
        raise HTTPException(status_code=500, detail=f"Agent investigation failed: {str(e)}")