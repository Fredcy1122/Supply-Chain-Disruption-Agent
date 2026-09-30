from backend.models.schemas import ToolEvidence, DisruptionBriefingResponse, RiskLevel
from backend.services.shipment_service import get_shipment_by_id

def generate_rag_briefing(shipment_id: str, risk_level: RiskLevel, delay_probability: float, evidence: ToolEvidence) -> DisruptionBriefingResponse:
    """
    Takes the raw evidence found by the AI Agent, queries the RAG ChromaDB for relevant SOPs,
    and uses Azure OpenAI to synthesize a final mitigation briefing.
    """
    shipment = get_shipment_by_id(shipment_id)
    
    # --- 1. RAG RETRIEVAL STAGE ---
    # When your ChromaDB is fully populated, you will import your retrieval function here.
    # Example:
    # from backend.rag.retrieval import search_sops
    # rag_query = f"Mitigation for {shipment.product_category} delay. Weather issue: {evidence.weather_summary}"
    # retrieved_sops = search_sops(rag_query)
    
    # Fallback simulation for architectural testing:
    simulated_sops = [
        "SOP-04: Extreme Weather Rerouting Protocol",
        "SOP-12: Inventory Buffer Utilization for High-Risk Categories"
    ]

    # --- 2. LLM SYNTHESIS STAGE ---
    # When Azure OpenAI is active, you will pass the evidence and SOPs into a prompt here.
    # Example:
    # prompt = f"Given SOPs: {simulated_sops}, and Evidence: {evidence}, generate a summary..."
    
    # Fallback LLM generation for architectural testing:
    summary = (
        f"Shipment {shipment_id} ({shipment.product_category} bound for {shipment.destination}) "
        f"faces a {risk_level.value} risk ({delay_probability*100}%). RAG policy suggests immediate "
        f"intervention based on environmental evidence: {evidence.weather_summary}"
    )
    
    recommended_actions = [
        "Trigger SOP-04: Reroute via secondary transit hub immediately.",
        f"Trigger SOP-12: Utilize inventory buffer of {evidence.inventory_coverage_days} days to fulfill active destination orders."
    ]

    return DisruptionBriefingResponse(
        shipment_id=shipment_id,
        risk_level=risk_level,
        delay_probability=delay_probability,
        evidence=evidence,
        rag_policy_citations=simulated_sops,
        summary=summary,
        recommended_actions=recommended_actions
    )