from backend.models.schemas import DisruptionBriefingResponse, ToolEvidence
from backend.services.shipment_service import get_shipment_by_id
from backend.services.prediction_service import predict_delay_risk

def run_investigation(shipment_id: str) -> DisruptionBriefingResponse:
    """
    Orchestrates the AI Agent investigation. Strictly enforces the Risk Gate:
    only shipments flagged as requiring investigation are processed.
    """
    # 1. ENFORCE THE GATE: Run prediction first
    prediction = predict_delay_risk(shipment_id)
    if not prediction.requires_investigation:
        # If the risk is LOW, we reject the request to save compute/LLM costs
        raise ValueError(f"Shipment {shipment_id} is LOW risk ({prediction.delay_probability}) and does not require AI investigation.")
        
    # 2. Fetch the shipment facts
    shipment = get_shipment_by_id(shipment_id)
    
    # 3. WAKE UP THE AGENT (Simulated tool calling for structural testing)
    # Soon, LangGraph will dynamically populate this by calling your external APIs
    evidence = ToolEvidence(
        weather_summary="Heavy thunderstorms reported along the primary transit route.",
        supplier_status="Supplier operating normally; no origin delays detected.",
        inventory_coverage_days=12
    )
    
    # 4. GENERATE THE BRIEFING (Simulated Azure OpenAI + RAG synthesis)
    return DisruptionBriefingResponse(
        shipment_id=shipment_id,
        risk_level=prediction.risk_level,
        delay_probability=prediction.delay_probability,
        evidence=evidence,
        rag_policy_citations=["SOP-04: Extreme Weather Rerouting", "SOP-12: Inventory Buffer Utilization"],
        summary=f"Shipment {shipment_id} containing {shipment.product_category} bound for {shipment.destination} is at a {prediction.risk_level.value} risk of delay. Weather APIs indicate severe storms on the route, but supplier operations remain unaffected.",
        recommended_actions=[
            "Authorize immediate rerouting through the secondary transit hub.",
            "Notify the receiving facility of a potential 24-48 hour arrival variance."
        ]
    )