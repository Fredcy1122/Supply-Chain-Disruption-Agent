from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

# 1. Enums for strict categorization
class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

# 2. Base Shipment Schema (Representing DataCo shipment fields)
class ShipmentBase(BaseModel):
    shipment_id: str = Field(..., description="Unique shipment tracking identifier")
    product_category: str = Field(..., description="Category of goods being transported")
    destination: str = Field(..., description="Destination city/country")
    shipping_mode: str = Field(..., description="Standard Class, First Class, Second Class, etc.")
    days_for_shipping_real: Optional[float] = Field(None, description="Actual transit time if completed")
    days_for_shipment_scheduled: float = Field(..., description="Target transit schedule")

class ShipmentResponse(ShipmentBase):
    current_status: str = Field("Pending", description="Current transit status")

# 3. Machine Learning Prediction Schema (The Risk Gate output)
class PredictionResponse(BaseModel):
    shipment_id: str
    delay_probability: float = Field(..., ge=0.0, le=1.0, description="Model delay probability score between 0 and 1")
    risk_level: RiskLevel = Field(..., description="LOW (<0.40), MEDIUM (0.40-0.69), or HIGH (>=0.70)")
    requires_investigation: bool = Field(..., description="True if risk is MEDIUM or HIGH, triggering the AI Agent")

# 4. Investigation & Briefing Schema (AI Agent & RAG output)
class ToolEvidence(BaseModel):
    weather_summary: Optional[str] = None
    supplier_status: Optional[str] = None
    inventory_coverage_days: Optional[int] = None

class DisruptionBriefingResponse(BaseModel):
    shipment_id: str
    risk_level: RiskLevel
    delay_probability: float
    evidence: ToolEvidence
    rag_policy_citations: List[str] = Field(default_factory=list, description="Retrieved SOP policy references")
    summary: str = Field(..., description="Executive summary of the disruption risk")
    recommended_actions: List[str] = Field(..., description="Actionable next steps for logistics operators")