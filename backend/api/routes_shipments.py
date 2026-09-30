from fastapi import APIRouter, HTTPException
from backend.models.schemas import ShipmentResponse
from backend.services.shipment_service import get_shipment_by_id

# APIRouter acts as a "mini FastAPI" application for specific modules
router = APIRouter(prefix="/api/shipments", tags=["Shipments"])

@router.get("/{shipment_id}", response_model=ShipmentResponse)
def fetch_shipment(shipment_id: str):
    """
    Retrieve shipment details by ID. 
    This acts as the primary data lookup for the React dashboard.
    """
    try:
        shipment = get_shipment_by_id(shipment_id)
        return shipment
    except Exception as e:
        raise HTTPException(status_code=404, detail="Shipment not found")