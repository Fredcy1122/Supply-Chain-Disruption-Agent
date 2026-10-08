import logging
from typing import Any

from backend.exceptions import AzureOpenAIServiceError
from backend.models.schemas import (
    DisruptionBriefingResponse,
    LLMBriefingContent,
    RiskLevel,
    ToolEvidence,
)
from backend.services.azure_openai_service import (
    generate_azure_briefing,
)
from backend.services.shipment_service import (
    get_shipment_by_id,
)
from rag.retrieval import (
    RAGRetrievalError,
    retrieve_operational_knowledge,
)


logger = logging.getLogger(__name__)

def format_coverage_days(
    coverage: float,
) -> str:
    """
    Format inventory coverage without unnecessary trailing zeros.
    """
    return format(
        coverage,
        "g",
    )


def build_rag_query(
    shipment_id: str,
    risk_level: RiskLevel,
    delay_probability: float,
    evidence: ToolEvidence,
) -> str:
    """
    Build a grounded retrieval query from evidence collected by
    the Agent Tools.

    Delay probability represents the likelihood of delay. It must not
    be interpreted as a delay duration.
    """
    query_parts = [
        "Supply-chain shipment disruption investigation.",
        f"Shipment reference: {shipment_id}",
        f"Risk level: {risk_level.value}",
        f"Delay probability: {delay_probability:.4f}",
        (
            "Delay probability is not a prediction of the number "
            "of delay days."
        ),
    ]

    if evidence.shipment_summary:
        query_parts.append(
            "Shipment evidence: "
            f"{evidence.shipment_summary}"
        )

    if evidence.historical_delay_summary:
        query_parts.append(
            "Historical delay evidence: "
            f"{evidence.historical_delay_summary}"
        )

    if evidence.weather_summary:
        query_parts.append(
            "Weather evidence: "
            f"{evidence.weather_summary}"
        )

    if evidence.supplier_status:
        query_parts.append(
            "Supplier evidence: "
            f"{evidence.supplier_status}"
        )
    else:
        query_parts.append(
            "Supplier evidence is not currently available."
        )

    inventory = evidence.inventory_status

    if inventory is not None:
        coverage_text = format_coverage_days(
            inventory.inventory_coverage_days
        )

        query_parts.extend(
            [
                (
                    "Inventory product: "
                    f"{inventory.product_name}"
                ),
                (
                    "Inventory warehouse: "
                    f"{inventory.warehouse_id}, "
                    f"{inventory.warehouse_location}, "
                    f"{inventory.warehouse_country}"
                ),
                (
                    "Current inventory stock: "
                    f"{inventory.current_stock} units."
                ),
                (
                    "Reserved inventory stock: "
                    f"{inventory.reserved_stock} units."
                ),
                (
                    "Available inventory stock: "
                    f"{inventory.available_stock} units."
                ),
                (
                    "Average daily demand: "
                    f"{inventory.daily_demand} units per day."
                ),
                (
                    "Inventory coverage: "
                    f"{coverage_text} days."
                ),
                (
                    "Safety stock: "
                    f"{inventory.safety_stock} units."
                ),
                (
                    "Reorder point: "
                    f"{inventory.reorder_point} units."
                ),
                (
                    "Stockout risk: "
                    f"{inventory.stockout_risk.value}."
                ),
                (
                    "Below safety stock: "
                    f"{inventory.below_safety_stock}."
                ),
                (
                    "Below reorder point: "
                    f"{inventory.below_reorder_point}."
                ),
                (
                    "Incoming replenishment quantity: "
                    f"{inventory.incoming_quantity} units."
                ),
                (
                    "Expected replenishment date: "
                    + (
                        inventory
                        .expected_replenishment_date
                        .isoformat()
                        if inventory
                        .expected_replenishment_date
                        is not None
                        else "not available"
                    )
                    + "."
                ),
                (
                    "Warehouse country matches shipment destination: "
                    f"{inventory.destination_country_match}."
                ),
                (
                    "Inventory source: synthetic demonstration data."
                ),
            ]
        )

        if evidence.inventory_summary:
            query_parts.append(
                "Inventory evidence summary: "
                f"{evidence.inventory_summary}"
            )
    elif (
        evidence.inventory_coverage_days
        is not None
    ):
        coverage_text = format_coverage_days(
            evidence.inventory_coverage_days
        )

        query_parts.append(
            "Inventory coverage: "
            f"{coverage_text} days."
        )
    else:
        query_parts.append(
            "Inventory coverage is not currently available."
        )

    query_parts.extend(
        [
            (
                "Retrieve the most relevant operational "
                "procedures."
            ),
            (
                "Prioritize shipment escalation, inventory "
                "stockout response, replenishment, supplier, "
                "weather, and rerouting guidance supported by "
                "the collected evidence."
            ),
            (
                "Do not assume facts that are not contained "
                "in the collected evidence."
            ),
            (
                "Do not infer delay duration from delay "
                "probability."
            ),
            (
                "Do not treat incoming inventory as guaranteed "
                "or operationally available."
            ),
        ]
    )

    return "\n".join(
        query_parts
    )

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
    Build a short deterministic guidance summary using at most one
    excerpt from each retrieved source.
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


def build_deterministic_actions(
    risk_level: RiskLevel,
    evidence: ToolEvidence,
    retrieved_knowledge: list[dict[str, Any]],
) -> list:
    """
    Build conservative deterministic recommendations.

    This function is used when Azure OpenAI cannot generate a valid
    briefing. Recommendations remain grounded in collected evidence
    and require human operational review.
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
        weather_text = (
            evidence.weather_summary.lower()
        )

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

        if (
            severe_weather
            and not low_weather
        ):
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
            "Use the collected synthetic supplier evidence when "
            "evaluating alternative sourcing options, subject to "
            "human validation."
        )
    else:
        actions.append(
            "Obtain supplier availability and performance evidence "
            "before recommending an alternative supplier."
        )

    inventory = evidence.inventory_status

    if inventory is not None:
        if (
            inventory.stockout_risk
            == RiskLevel.HIGH
        ):
            actions.append(
                "Escalate the synthetic inventory exposure for "
                "immediate human review because available stock is "
                "at or below safety stock."
            )
        elif (
            inventory.stockout_risk
            == RiskLevel.MEDIUM
        ):
            actions.append(
                "Review replenishment timing because synthetic "
                "inventory coverage is limited or available stock "
                "is at or below the reorder point."
            )
        else:
            actions.append(
                "Continue monitoring inventory coverage because "
                "the synthetic inventory record currently indicates "
                "low stockout risk."
            )

        if inventory.below_reorder_point:
            actions.append(
                "Confirm the replenishment plan because available "
                "stock is at or below the synthetic reorder point."
            )

        if inventory.incoming_quantity > 0:
            actions.append(
                "Confirm the recorded incoming quantity and expected "
                "replenishment date before relying on incoming "
                "inventory as mitigation."
            )
        else:
            actions.append(
                "Review alternative replenishment options because no "
                "incoming inventory quantity is recorded."
            )

        if not inventory.destination_country_match:
            actions.append(
                "Validate warehouse geography and transfer "
                "feasibility because the synthetic warehouse country "
                "does not match the shipment destination country."
            )
    elif (
        evidence.inventory_coverage_days
        is not None
    ):
        if (
            evidence.inventory_coverage_days
            <= 3
        ):
            actions.append(
                "Escalate potential stockout exposure because "
                "inventory coverage is three days or less."
            )
        else:
            actions.append(
                "Review available inventory coverage without "
                "assuming a delay duration that was not predicted."
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


def build_deterministic_briefing(
    shipment_id: str,
    risk_level: RiskLevel,
    delay_probability: float,
    evidence: ToolEvidence,
    retrieved_knowledge: list[dict[str, Any]],
) -> LLMBriefingContent:
    """
    Build a grounded briefing without Azure OpenAI.

    This is the safe fallback when Azure is unavailable or returns an
    invalid response.
    """
    shipment = get_shipment_by_id(
        shipment_id
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

    risk_factors: list[str] = []

    if evidence.historical_delay_summary:
        summary_parts.append(
            evidence.historical_delay_summary
        )

        risk_factors.append(
            evidence.historical_delay_summary
        )

    if evidence.weather_summary:
        summary_parts.append(
            evidence.weather_summary
        )

        risk_factors.append(
            evidence.weather_summary
        )

    if evidence.supplier_status:
        summary_parts.append(
            f"Supplier evidence: {evidence.supplier_status}"
        )

        risk_factors.append(
            evidence.supplier_status
        )
    else:
        summary_parts.append(
            "Supplier availability has not yet been assessed."
        )

    if evidence.inventory_summary:
        summary_parts.append(
            evidence.inventory_summary
        )

        risk_factors.append(
            evidence.inventory_summary
        )
    elif (
        evidence.inventory_coverage_days
        is not None
    ):
        coverage_text = format_coverage_days(
            evidence.inventory_coverage_days
        )

        summary_parts.append(
            "Available inventory coverage is "
            f"{coverage_text} days."
        )
    else:
        summary_parts.append(
            "Inventory coverage has not yet been assessed, so "
            "stockout exposure cannot be confirmed."
        )


    summary_parts.append(
        build_guidance_summary(
            retrieved_knowledge
        )
    )

    return LLMBriefingContent(
        summary=" ".join(summary_parts),
        risk_factors=risk_factors,
        recommended_actions=(
            build_deterministic_actions(
                risk_level=risk_level,
                evidence=evidence,
                retrieved_knowledge=retrieved_knowledge,
            )
        ),
    )


def generate_rag_briefing(
    shipment_id: str,
    risk_level: RiskLevel,
    delay_probability: float,
    evidence: ToolEvidence,
) -> DisruptionBriefingResponse:
    """
    Retrieve operational knowledge and generate a grounded briefing.

    Azure OpenAI is the primary synthesis method. A deterministic,
    evidence-based implementation is retained as a safe fallback.
    """
    get_shipment_by_id(
        shipment_id
    )

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

    try:
        generated_content = generate_azure_briefing(
            shipment_id=shipment_id,
            risk_level=risk_level,
            delay_probability=delay_probability,
            evidence=evidence,
            retrieved_knowledge=retrieved_knowledge,
        )

        logger.info(
            "Azure OpenAI generated the briefing for shipment %s.",
            shipment_id,
        )

    except AzureOpenAIServiceError as exc:
        logger.warning(
            "Azure OpenAI briefing generation failed for shipment "
            "%s. Using deterministic fallback. Error: %s",
            shipment_id,
            exc,
        )

        generated_content = build_deterministic_briefing(
            shipment_id=shipment_id,
            risk_level=risk_level,
            delay_probability=delay_probability,
            evidence=evidence,
            retrieved_knowledge=retrieved_knowledge,
        )

    return DisruptionBriefingResponse(
        shipment_id=shipment_id,
        risk_level=risk_level,
        delay_probability=delay_probability,
        evidence=evidence,
        rag_policy_citations=rag_policy_citations,
        summary=generated_content.summary,
        recommended_actions=(
            generated_content.recommended_actions
        ),
    )