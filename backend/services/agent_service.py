from dataclasses import dataclass
from typing import Any, Callable, Generator

from pydantic import BaseModel

from backend.exceptions import (
    InvestigationNotRequiredError,
    WeatherServiceError,
)
from backend.models.schemas import (
    DisruptionBriefingResponse,
    ShipmentResponse,
    ToolCall,
    ToolCallStatus,
    ToolEvidence,
)
from backend.services.agent_tools import (
    get_delay_risk,
    get_destination_weather,
    get_historical_delay_context,
    get_shipment,
    get_alternative_suppliers,
)
from backend.services.briefing_service import (
    generate_rag_briefing,
)
from backend.services.supplier_service import (
    SupplierNotFoundError,
    SupplierServiceError,
)


WEATHER_SCOPE_LIMITATION = (
    "Weather describes the geocoded destination city over an "
    "approximate window from the order date through the scheduled "
    "shipping period. It does not represent the full shipment route."
)


UNCOLLECTED_EVIDENCE_LIMITATIONS = [
    (
        "Inventory coverage was not collected because no inventory "
        "data source is currently connected."
    ),
    (
        "Supplier records and retrieved operational procedures are "
        "synthetic demonstration data and are not real company "
        "records or policies."
    ),
]


TOOL_START = "tool_start"
TOOL_COMPLETE = "tool_complete"
TOOL_ERROR = "tool_error"
MESSAGE = "message"
DONE = "done"


@dataclass(frozen=True)
class InvestigationEvent:
    """
    One progress event produced during an investigation.

    The data value is JSON-serializable so it can be returned through
    the streaming agent API.
    """

    event: str
    data: dict[str, Any]


def _tool_event(
    event: str,
    call: ToolCall,
) -> InvestigationEvent:
    """
    Convert a completed ToolCall into an investigation progress event.
    """
    data = call.model_dump(
        mode="json",
        exclude={"tool"},
    )

    return InvestigationEvent(
        event=event,
        data={
            "name": call.tool,
            **data,
        },
    )


def _call_tool(
    tool_trace: list[ToolCall],
    tool: str,
    tool_input: dict[str, Any],
    function: Callable[[], Any],
) -> Generator[InvestigationEvent, None, Any]:
    """
    Run one tool, record its output, and emit progress events.
    """
    yield InvestigationEvent(
        event=TOOL_START,
        data={
            "name": tool,
            "input": tool_input,
        },
    )

    try:
        result = function()

    except Exception as exc:
        call = ToolCall(
            tool=tool,
            input=tool_input,
            status=ToolCallStatus.ERROR,
            error=str(exc),
        )

        tool_trace.append(call)

        yield _tool_event(
            TOOL_ERROR,
            call,
        )

        raise

    output = (
        result.model_dump(mode="json")
        if isinstance(result, BaseModel)
        else result
    )

    call = ToolCall(
        tool=tool,
        input=tool_input,
        output=output,
        status=ToolCallStatus.SUCCESS,
    )

    tool_trace.append(call)

    yield _tool_event(
        TOOL_COMPLETE,
        call,
    )

    return result


def _summarize_shipment(
    shipment: ShipmentResponse,
) -> str:
    """
    Produce a leakage-safe shipment summary.
    """
    return (
        f"{shipment.shipment_reference}: "
        f"{shipment.quantity} x {shipment.product_name} "
        f"({shipment.category}) to "
        f"{shipment.destination_city}, "
        f"{shipment.destination_country} by "
        f"{shipment.shipping_mode}, scheduled for "
        f"{shipment.scheduled_shipping_days} days, ordered "
        f"{shipment.order_date:%Y-%m-%d}."
    )


def _summarize_historical_context(
    context: dict[str, Any],
) -> str:
    """
    Summarize the historical delay evidence returned by the tool.
    """
    rates = context["historical_delay_rates"]

    return (
        "Historical delay rates: "
        f"product {rates['product']:.1%}, "
        f"market {rates['market']:.1%}, "
        f"shipping mode {rates['shipping_mode']:.1%}. "
        f"Highest: {context['highest_delay_rate_factor']}."
    )


def _summarize_weather(
    weather: dict[str, Any],
) -> str:
    """
    Summarize destination weather evidence.
    """
    return (
        f"Observed weather in {weather['destination']}, "
        f"{weather['window_start']} to "
        f"{weather['window_end']}: "
        f"{weather['precipitation_total_mm']:.1f} mm "
        f"precipitation "
        f"(max {weather['precipitation_max_mm']:.1f} mm/day), "
        f"max wind {weather['max_wind_speed_kmh']:.1f} km/h; "
        f"worst condition "
        f"{weather['worst_weather_description']} "
        f"({weather['severity']} severity)."
    )

def _summarize_supplier_recommendation(
    recommendation,
) -> str:
    """
    Summarize the synthetic Supplier Tool result for the briefing.
    """
    supplier = (
        recommendation.recommended_supplier
    )

    if supplier is None:
        return (
            "No LOW- or MEDIUM-risk synthetic supplier could be "
            "recommended. Available candidates require additional "
            "human review."
        )

    return (
        "Synthetic alternative supplier candidate: "
        f"{supplier.supplier_id} "
        f"({supplier.supplier_name}), "
        f"located in {supplier.supplier_country}; "
        f"category {supplier.product_category}; "
        f"average lead time "
        f"{supplier.average_lead_time_days:.1f} days; "
        f"on-time delivery rate "
        f"{supplier.on_time_delivery_rate:.1%}; "
        f"supplier risk "
        f"{supplier.supplier_risk_level.value} "
        f"({supplier.supplier_risk_score:.2f}/100). "
        "Quantity capacity and contractual availability are not "
        "verified."
    )

def iter_investigation(
    shipment_id: str,
) -> Generator[
    InvestigationEvent,
    None,
    DisruptionBriefingResponse,
]:
    """
    Run the complete investigation workflow.

    Flow:
        prediction
        risk gate
        shipment lookup
        historical-delay evidence
        destination weather
        RAG retrieval
        disruption briefing
    """
    tool_trace: list[ToolCall] = []
    limitations: list[str] = []

    prediction = yield from _call_tool(
        tool_trace=tool_trace,
        tool="get_delay_risk",
        tool_input={
            "shipment_id": shipment_id,
        },
        function=lambda: get_delay_risk(
            shipment_id
        ),
    )

    if not prediction.requires_investigation:
        raise InvestigationNotRequiredError(
            f"Shipment {shipment_id} is "
            f"{prediction.risk_level.value} risk "
            f"({prediction.delay_probability}) and does not require "
            "AI investigation."
        )

    shipment_reference = prediction.shipment_id

    shipment = yield from _call_tool(
        tool_trace=tool_trace,
        tool="get_shipment",
        tool_input={
            "shipment_id": shipment_reference,
        },
        function=lambda: get_shipment(
            shipment_reference
        ),
    )

    historical_delay_summary = None

    try:
        historical_context = yield from _call_tool(
            tool_trace=tool_trace,
            tool="get_historical_delay_context",
            tool_input={
                "shipment_id": shipment_reference,
            },
            function=lambda: (
                get_historical_delay_context(
                    shipment
                )
            ),
        )

        historical_delay_summary = (
            _summarize_historical_context(
                historical_context
            )
        )

    except Exception as exc:
        limitations.append(
            "Historical delay context was not collected: "
            f"{exc}"
        )

    weather_summary = None

    try:
        weather = yield from _call_tool(
            tool_trace=tool_trace,
            tool="get_destination_weather",
            tool_input={
                "shipment_id": shipment_reference,
            },
            function=lambda: (
                get_destination_weather(
                    shipment
                )
            ),
        )

        weather_summary = _summarize_weather(
            weather
        )

    except WeatherServiceError as exc:
        limitations.append(
            "Weather evidence was not collected: "
            f"{exc}"
        )
    supplier_status = None

    try:
        supplier_recommendation = yield from _call_tool(
            tool_trace=tool_trace,
            tool="find_alternative_supplier",
            tool_input={
                "category": shipment.category,
                "destination_country": (
                    shipment.destination_country
                ),
                "required_quantity": shipment.quantity,
                "limit": 3,
            },
            function=lambda: get_alternative_suppliers(
                shipment=shipment,
                limit=3,
            ),
        )

        supplier_status = (
            _summarize_supplier_recommendation(
                supplier_recommendation
            )
        )

        limitations.append(
            supplier_recommendation.limitation
        )

    except SupplierNotFoundError as exc:
        limitations.append(
            "No category-compatible synthetic supplier was found: "
            f"{exc}"
        )

    except SupplierServiceError as exc:
        limitations.append(
            "Supplier evidence was not collected because the "
            f"supplier service failed: {exc}"
        )
    evidence = ToolEvidence(
        shipment_summary=_summarize_shipment(
            shipment
        ),
        historical_delay_summary=(
            historical_delay_summary
        ),
        weather_summary=weather_summary,
        supplier_status=supplier_status,
        inventory_coverage_days=None,
    )

    limitations.append(
        WEATHER_SCOPE_LIMITATION
    )

    limitations.extend(
        UNCOLLECTED_EVIDENCE_LIMITATIONS
    )

    briefing = generate_rag_briefing(
        shipment_id=shipment_reference,
        risk_level=prediction.risk_level,
        delay_probability=(
            prediction.delay_probability
        ),
        evidence=evidence,
    )

    briefing = briefing.model_copy(
        update={
            "tool_trace": tool_trace,
            "limitations": limitations,
        }
    )

    yield InvestigationEvent(
        event=MESSAGE,
        data={
            "role": "agent",
            "content": briefing.summary,
        },
    )

    yield InvestigationEvent(
        event=DONE,
        data=briefing.model_dump(
            mode="json"
        ),
    )

    return briefing


def run_investigation(
    shipment_id: str,
) -> DisruptionBriefingResponse:
    """
    Run the investigation to completion and return the briefing.
    """
    events = iter_investigation(
        shipment_id
    )

    while True:
        try:
            next(events)

        except StopIteration as finished:
            return finished.value
