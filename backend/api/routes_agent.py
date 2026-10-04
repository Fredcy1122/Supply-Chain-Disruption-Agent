import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from backend.exceptions import InvestigationNotRequiredError
from backend.models.schemas import DisruptionBriefingResponse
from backend.services.agent_service import iter_investigation, run_investigation
from backend.services.shipment_service import ShipmentNotFoundError

router = APIRouter(prefix="/api/agent", tags=["AI Agent Investigation"])

# The stream's own terminal event for a fatal failure. Progress event
# names come from the agent service.
ERROR_EVENT = "error"


def _classify_failure(exc: Exception) -> tuple[int, str, str]:
    """
    Map a fatal investigation failure to (HTTP status, code, detail).

    Shared by both endpoints so the synchronous response and the
    stream's error event always agree.
    """
    if isinstance(exc, InvestigationNotRequiredError):
        # The risk gate rejected a shipment that needs no investigation
        return 400, "investigation_not_required", str(exc)
    if isinstance(exc, ValueError):
        # Other invalid input, such as a malformed shipment reference
        return 400, "invalid_request", str(exc)
    if isinstance(exc, ShipmentNotFoundError):
        # The shipment reference does not exist
        return 404, "shipment_not_found", str(exc)
    # The LLM or a required tool failed
    return 500, "investigation_failed", f"Agent investigation failed: {str(exc)}"


@router.post("/investigate/{shipment_id}", response_model=DisruptionBriefingResponse)
def investigate_shipment(shipment_id: str):
    """
    Triggers the AI Agent to investigate a high-risk shipment, gather evidence,
    and generate an actionable disruption briefing.
    """
    try:
        briefing = run_investigation(shipment_id)
        return briefing
    except Exception as e:
        status_code, _, detail = _classify_failure(e)
        raise HTTPException(status_code=status_code, detail=detail)


def _format_sse(event: str, data: dict[str, Any]) -> str:
    """
    Encode one Server-Sent Event. json.dumps escapes newlines, so the
    payload always fits on a single data line.
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _event_stream(shipment_id: str) -> AsyncIterator[str]:
    """
    Run the investigation and encode each of its events as it happens.

    The investigation is blocking, so each step runs in the threadpool.
    A step is only started when the previous event has been sent, so
    when the client disconnects no further tools are called: the step
    in progress finishes (a thread cannot be interrupted) and the
    investigation is then closed.
    """
    events = iter_investigation(shipment_id)
    try:
        while True:
            try:
                # The default avoids raising StopIteration across threads.
                event = await run_in_threadpool(next, events, None)
            except Exception as exc:
                status_code, code, detail = _classify_failure(exc)
                yield _format_sse(
                    ERROR_EVENT,
                    {"status": status_code, "code": code, "detail": detail},
                )
                return

            if event is None:
                return

            yield _format_sse(event.event, event.data)
    finally:
        events.close()


@router.get(
    "/investigate/{shipment_id}/stream",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": (
                "Server-Sent Events: tool_start, tool_complete, tool_error "
                "and message as the investigation progresses, then exactly "
                "one terminal event. done carries the same body as the "
                "synchronous endpoint; error carries status, code and "
                "detail. A stream that ends without done did not complete."
            ),
            "content": {"text/event-stream": {}},
        }
    },
)
async def investigate_shipment_stream(shipment_id: str):
    """
    Runs the same investigation as the synchronous endpoint and streams
    its progress as Server-Sent Events.

    The response is always 200 once the stream opens, because the risk
    gate is itself the first streamed tool call. Failures are reported
    in the error event, whose status matches the synchronous endpoint's
    HTTP status (400, 404 or 500).
    """
    return StreamingResponse(
        _event_stream(shipment_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Stops reverse proxies such as nginx from buffering events
            "X-Accel-Buffering": "no",
        },
    )
