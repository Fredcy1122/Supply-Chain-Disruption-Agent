from typing import Any

from backend.models.schemas import (
    DisruptionBriefingResponse,
    RiskLevel,
    ToolEvidence,
)
from backend.services.shipment_service import get_shipment_by_id
from rag.retrieval import (
    RAGRetrievalError,
    retrieve_operational_knowledge,
)


def build_rag_query(
    shipment_id: str,
    risk_level: RiskLevel,
    delay_probability: float,
    evidence: ToolEvidence,
) -> str:
    """
    Build a grounded retrieval query from evidence collected by
    the agent tools.
    """
    query_parts = [
        "Supply-chain shipment disruption investigation.",
        f"Shipment reference: {shipment_id}",
        f"Risk level: {risk_level.value}",
        f"Delay probability: {delay_probability:.4f}",
    ]

    if evidence.shipment_summary:
        query_parts.append(
            f"Shipment evidence: {evidence.shipment_summary}"
        )

    if evidence.historical_delay_summary:
        query_parts.append(
            "Historical delay evidence: "
            f"{evidence.historical_delay_summary}"
        )

    if evidence.weather_summary:
        query_parts.append(
            f"Weather evidence: {evidence.weather_summary}"
        )

    if evidence.supplier_status:
        query_parts.append(
            f"Supplier evidence: {evidence.supplier_status}"
        )
    else:
        query_parts.append(
            "Supplier evidence is not currently available."
        )

    if evidence.inventory_coverage_days is not None:
        query_parts.append(
            "Inventory coverage: "
            f"{evidence.inventory_coverage_days} days."
        )
    else:
        query_parts.append(
            "Inventory coverage is not currently available."
        )

    query_parts.extend(
        [
            "Retrieve the most relevant operational procedures.",
            "Identify appropriate monitoring, escalation, weather, "
            "supplier, inventory, and rerouting guidance.",
            "Do not assume facts that are not contained in the "
            "collected evidence.",
        ]
    )

    return "\n".join(query_parts)


def extract_rag_citations(
    retrieved_knowledge: list[dict[str, Any]],
) -> list: 
    """
    Extract unique source filenames in retrieval-ranked order.
    """
    citations: list[str] = []
    seen_sources: set[str] = set()

    for result in retrieved_knowledge:
        source = str(
            result.get("source", "")
        ).strip()

        if not source:
            continue

        if source in seen_sources:
            continue

        citations.append(source)
        seen_sources.add(source)

    return citations


def build_guidance_summary(
    retrieved_knowledge: list[dict[str, Any]],
) -> str:
    """
    Build a short deterministic summary using at most one excerpt
    from each retrieved source.

    Azure OpenAI synthesis can replace this implementation later.
    """
    if not retrieved_knowledge:
        return (
            "No relevant operational guidance was retrieved from "
            "the knowledge base."
        )

    guidance_parts: list[str] = []
    seen_sources: set[str] = set()

    for result in retrieved_knowledge:
        source = str(
            result.get(
                "source",
                "Unknown source",
            )
        ).strip()

        if not source or source in seen_sources:
            continue

        content = " ".join(
            str(
                result.get(
                    "content",
                    "",
                )
            ).split()
        )

        if not content:
            continue

        excerpt = content[:300].rstrip()

        if len(content) > 300:
            excerpt += "..."

        guidance_parts.append(
            f"{source}: {excerpt}"
        )

        seen_sources.add(source)

        if len(guidance_parts) == 3:
            break

    if not guidance_parts:
        return (
            "Operational documents were retrieved, but no usable "
            "guidance text was available."
        )

    return (
        "Retrieved synthetic operational guidance: "
        + " ".join(guidance_parts)
    )


def build_recommended_actions(
    risk_level: RiskLevel,
    evidence: ToolEvidence,
    retrieved_knowledge: list[dict[str, Any]],
) -> list:
    """
    Build conservative recommendations from collected evidence and
    retrieved operational knowledge.
    """
    actions: list[str] = []

    if risk_level == RiskLevel.HIGH:
        actions.append(
            "Escalate the shipment for immediate human operational "
            "review."
        )
    elif risk_level == RiskLevel.MEDIUM:
        actions.append(
            "Continue the disruption investigation and actively "
            "monitor the shipment."
        )
    else:
        actions.append(
            "Continue routine monitoring because immediate "
            "investigation is not required."
        )

    if evidence.historical_delay_summary:
        actions.append(
            "Consider the elevated historical delay factors during "
            "the operational review."
        )

    if evidence.weather_summary:
        weather_text = evidence.weather_summary.lower()

        severe_weather_terms = (
            "high severity",
            "severe weather",
            "thunderstorm",
            "heavy rain",
            "heavy snow",
            "extreme weather",
            "flood",
            "hurricane",
            "tornado",
        )

        low_weather_terms = (
            "low severity",
            "light drizzle",
            "clear sky",
            "mainly clear",
            "partly cloudy",
        )

        severe_weather = any(
            term in weather_text
            for term in severe_weather_terms
        )

        low_weather = any(
            term in weather_text
            for term in low_weather_terms
        )

        if severe_weather and not low_weather:
            actions.append(
                "Evaluate transport alternatives because the "
                "collected weather evidence indicates potentially "
                "severe conditions."
            )
        elif low_weather:
            actions.append(
                "Continue monitoring destination weather, but do not "
                "reroute solely on the current low-severity weather "
                "evidence."
            )
        else:
            actions.append(
                "Continue monitoring destination weather before "
                "making any rerouting decision."
            )

    if evidence.supplier_status:
        actions.append(
            "Use the collected supplier evidence when evaluating "
            "alternative sourcing options."
        )
    else:
        actions.append(
            "Obtain supplier availability and performance evidence "
            "before recommending an alternative supplier."
        )

    if evidence.inventory_coverage_days is not None:
        if evidence.inventory_coverage_days <= 3:
            actions.append(
                "Escalate potential stockout exposure because "
                "inventory coverage is three days or less."
            )
        else:
            actions.append(
                "Compare the likely disruption duration with the "
                "available inventory coverage."
            )
    else:
        actions.append(
            "Obtain current inventory coverage before determining "
            "the shipment's stockout impact."
        )

    if retrieved_knowledge:
        actions.append(
            "Review the retrieved synthetic operational procedures "
            "before approving any mitigation action."
        )

    return actions


def generate_rag_briefing(
    shipment_id: str,
    risk_level: RiskLevel,
    delay_probability: float,
    evidence: ToolEvidence,
) -> DisruptionBriefingResponse:
    """
    Retrieve operational knowledge from Chroma and create an
    evidence-based disruption briefing.

    The RAG citations are real source filenames retrieved from the
    synthetic PDF knowledge base.
    """
    shipment = get_shipment_by_id(shipment_id)

    rag_query = build_rag_query(
        shipment_id=shipment_id,
        risk_level=risk_level,
        delay_probability=delay_probability,
        evidence=evidence,
    )

    try:
        retrieved_knowledge = (
            retrieve_operational_knowledge(
                query=rag_query,
                k=5,
            )
        )
    except RAGRetrievalError as exc:
        raise RAGRetrievalError(
            "The investigation tools completed, but operational "
            f"knowledge retrieval failed: {exc}"
        ) from exc

    if not retrieved_knowledge:
        raise RAGRetrievalError(
            "The operational knowledge search returned no results."
        )

    rag_policy_citations = extract_rag_citations(
        retrieved_knowledge
    )

    if not rag_policy_citations:
        raise RAGRetrievalError(
            "Operational knowledge was retrieved, but no source "
            "citations were available."
        )

    destination = ", ".join(
        part
        for part in [
            shipment.destination_city,
            shipment.destination_state,
            shipment.destination_country,
        ]
        if part
    )

    summary_parts = [
        (
            f"Shipment {shipment_id}, containing "
            f"{shipment.quantity} x {shipment.product_name}, has a "
            f"{risk_level.value} predicted delay risk of "
            f"{delay_probability:.1%}."
        ),
        (
            f"The shipment is scheduled for {destination} using "
            f"{shipment.shipping_mode}."
        ),
    ]

    if evidence.historical_delay_summary:
        summary_parts.append(
            evidence.historical_delay_summary
        )

    if evidence.weather_summary:
        summary_parts.append(
            evidence.weather_summary
        )

    if evidence.supplier_status:
        summary_parts.append(
            f"Supplier evidence: {evidence.supplier_status}"
        )
    else:
        summary_parts.append(
            "Supplier availability has not yet been assessed."
        )

    if evidence.inventory_coverage_days is not None:
        summary_parts.append(
            "Available inventory coverage is "
            f"{evidence.inventory_coverage_days} days."
        )
    else:
        summary_parts.append(
            "Inventory coverage has not yet been assessed."
        )

    summary_parts.append(
        build_guidance_summary(
            retrieved_knowledge
        )
    )

    recommended_actions = build_recommended_actions(
        risk_level=risk_level,
        evidence=evidence,
        retrieved_knowledge=retrieved_knowledge,
    )

    return DisruptionBriefingResponse(
        shipment_id=shipment_id,
        risk_level=risk_level,
        delay_probability=delay_probability,
        evidence=evidence,
        rag_policy_citations=rag_policy_citations,
        summary=" ".join(summary_parts),
        recommended_actions=recommended_actions,
    )