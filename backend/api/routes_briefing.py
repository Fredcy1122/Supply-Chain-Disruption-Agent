from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.models.schemas import ToolEvidence, DisruptionBriefingResponse, RiskLevel
from backend.services.briefing_service import generate_rag_briefing

router = APIRouter(prefix="/api/briefing", tags=["RAG Synthesis & Briefings"])

# We create a specific request model just for this endpoint to enforce strict data entry
class BriefingRequest(BaseModel):
    shipment_id: str
    risk_level: RiskLevel
    delay_probability: float
    evidence: ToolEvidence

@router.post("/generate", response_model=DisruptionBriefingResponse)
def create_briefing(request: BriefingRequest):
    """
    Accepts raw evidence from the AI Agent, runs it through the RAG pipeline,
    and generates the final disruption mitigation report.
    """
    try:
        briefing = generate_rag_briefing(
            shipment_id=request.shipment_id,
            risk_level=request.risk_level,
            delay_probability=request.delay_probability,
            evidence=request.evidence
        )
        return briefing
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG Briefing generation failed: {str(e)}")