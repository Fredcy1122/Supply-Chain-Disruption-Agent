from typing import Any, Callable

from pydantic import BaseModel

from backend.models.schemas import (
    DisruptionBriefingResponse,
    ShipmentResponse,
    ToolCall,
    ToolCallStatus,
    ToolEvidence,
)
from backend.services.agent_tools import (
    get_delay_risk,
    get_historical_delay_context,
    get_shipment,
)
from backend.services.briefing_service import generate_rag_briefing


# Evidence that this version of the investigation does not collect yet.
UNCOLLECTED_EVIDENCE_LIMITATIONS = [
    "Weather evidence was not collected: the weather tool is not yet implemented.",
    "Supplier status was not collected: no supplier data source is available.",
    "Inventory coverage was not collected: no inventory data source is available.",
    "Policy citations and recommended actions come from the briefing "
    "service placeholder: RAG retrieval is not yet integrated.",
]


def _call_tool(
    tool_trace: list[ToolCall],
    tool: str,
    tool_input: dict[str, Any],
    function: Callable[[], Any],
) -> Any:
    """
    Run one tool and record the call in the trace.

    The tool is passed as a zero-argument callable so its failure
    happens inside this function and is recorded. A failed call is
    recorded and the exception is re-raised so the caller decides
    whether the investigation can continue. Outputs are stored in JSON
    form so the trace can be returned in the API response.
    """
    try:
        result = function()
    except Exception as exc:
        tool_trace.append(
            ToolCall(
                tool=tool,
                input=tool_input,
                status=ToolCallStatus.ERROR,
                error=str(exc),
            )
        )
        raise

    output = (
        result.model_dump(mode="json")
        if isinstance(result, BaseModel)
        else result
    )

    tool_trace.append(
        ToolCall(
            tool=tool,
            input=tool_input,
            output=output,
            status=ToolCallStatus.SUCCESS,
        )
    )

    return result


def _summarize_shipment(shipment: ShipmentResponse) -> str:
    return (
        f"{shipment.shipment_reference}: {shipment.quantity} x "
        f"{shipment.product_name} ({shipment.category}) to "
        f"{shipment.destination_city}, {shipment.destination_country} "
        f"by {shipment.shipping_mode}, scheduled for "
        f"{shipment.scheduled_shipping_days} days, ordered "
        f"{shipment.order_date:%Y-%m-%d}."
    )


def _summarize_historical_context(context: dict[str, Any]) -> str:
    rates = context["historical_delay_rates"]
    return (
        f"Historical delay rates: product {rates['product']:.1%}, "
        f"market {rates['market']:.1%}, "
        f"shipping mode {rates['shipping_mode']:.1%}. "
        f"Highest: {context['highest_delay_rate_factor']}."
    )


def run_investigation(shipment_id: str) -> DisruptionBriefingResponse:
    """
    Orchestrates the AI Agent investigation. Strictly enforces the Risk Gate:
    only shipments flagged as requiring investigation are processed.

    Flow: risk gate, shipment facts, historical delay context, evidence,
    briefing. Every tool call is recorded in the response's tool_trace.
    The risk gate and shipment facts are required; other evidence that
    cannot be collected is reported in limitations.
    """
    tool_trace: list[ToolCall] = []
    limitations: list[str] = []

    # 1. ENFORCE THE GATE: Run prediction first
    prediction = _call_tool(
        tool_trace,
        "get_delay_risk",
        {"shipment_id": shipment_id},
        lambda: get_delay_risk(shipment_id),
    )
    if not prediction.requires_investigation:
        # LOW-risk shipments do not require AI investigation.
        raise ValueError(f"Shipment {shipment_id} is LOW risk ({prediction.delay_probability}) and does not require AI investigation.")

    # Use the normalized reference from the prediction (for example
    # "shp-1 " becomes "SHP-1") so every later tool call and the
    # briefing refer to the same shipment.
    shipment_reference = prediction.shipment_id

    # 2. Fetch the shipment facts. Required: the briefing service needs
    # the shipment record, so a failure here ends the investigation.
    shipment = _call_tool(
        tool_trace,
        "get_shipment",
        {"shipment_id": shipment_reference},
        lambda: get_shipment(shipment_reference),
    )

    # 3. Gather historical delay context. Optional: without it the
    # briefing is still valid, so a failure is reported as a limitation
    # (and recorded in the trace) instead of failing the request.
    historical_delay_summary = None
    try:
        context = _call_tool(
            tool_trace,
            "get_historical_delay_context",
            {"shipment_id": shipment_reference},
            lambda: get_historical_delay_context(shipment),
        )
        historical_delay_summary = _summarize_historical_context(context)
    except Exception as exc:
        limitations.append(
            f"Historical delay context was not collected: {exc}"
        )

    # 4. Build the evidence from tool outputs only. Weather, supplier and
    # inventory fields stay empty rather than holding placeholder values.
    evidence = ToolEvidence(
        shipment_summary=_summarize_shipment(shipment),
        historical_delay_summary=historical_delay_summary,
    )
    limitations.extend(UNCOLLECTED_EVIDENCE_LIMITATIONS)

    # 5. Generate the briefing with the existing briefing service
    briefing = generate_rag_briefing(
        shipment_id=shipment_reference,
        risk_level=prediction.risk_level,
        delay_probability=prediction.delay_probability,
        evidence=evidence,
    )

    # The trace and limitations are attached here so the briefing
    # service's interface stays unchanged.
    return briefing.model_copy(
        update={
            "tool_trace": tool_trace,
            "limitations": limitations,
        }
    )
