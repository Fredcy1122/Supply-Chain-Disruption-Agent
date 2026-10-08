import json
from types import SimpleNamespace
from datetime import date

import pytest

from backend.exceptions import (
    AzureOpenAIServiceError,
)
from backend.models.schemas import (
    RiskLevel,
    ToolEvidence,
    InventoryStatusResponse,
)
from backend.services import azure_openai_service


@pytest.fixture(autouse=True)
def clear_client_cache():
    azure_openai_service.clear_azure_openai_client_cache()

    yield

    azure_openai_service.clear_azure_openai_client_cache()


@pytest.fixture
def evidence():
    return ToolEvidence(
        shipment_summary=(
            "SHP-153444: 1 x Perfect Fitness Perfect Rip Deck "
            "to Indaial, Brasil by Standard Class."
        ),
        historical_delay_summary=(
            "Historical delay rates: product 55.0%, "
            "market 54.3%, shipping mode 38.1%."
        ),
        weather_summary=(
            "Observed destination weather showed light drizzle "
            "with low severity."
        ),
        supplier_status=(
            "Synthetic supplier candidate SUP003 is located in "
            "Bhutan and has MEDIUM risk. Geographic suitability "
            "for Brazil has not been verified."
        ),
        inventory_coverage_days=None,
    )

@pytest.fixture
def inventory_evidence():
    inventory = InventoryStatusResponse(
        inventory_id="INV-TEST",
        product_id="PROD-TEST",
        product_name=(
            "Perfect Fitness Perfect Rip Deck"
        ),
        category="Cleats",
        department="Apparel",
        warehouse_id="WH-015",
        warehouse_location="Singapore",
        warehouse_country="Singapore",
        supplier_id="SUP013",
        current_stock=453,
        reserved_stock=25,
        available_stock=428,
        daily_demand=109,
        safety_stock=572,
        reorder_point=888,
        incoming_quantity=0,
        expected_replenishment_date=None,
        inventory_coverage_days=3.93,
        stockout_risk=RiskLevel.HIGH,
        below_safety_stock=True,
        below_reorder_point=True,
        calculation_verified=True,
        destination_country="Brasil",
        destination_country_match=False,
        data_source="SYNTHETIC_MVP",
        limitation=(
            "Inventory records are synthetic "
            "demonstration data."
        ),
    )

    return ToolEvidence(
        shipment_summary=(
            "SHP-153444: 1 x Perfect Fitness Perfect Rip Deck "
            "to Indaial, Brasil by Standard Class."
        ),
        inventory_summary=(
            "Synthetic inventory evidence indicates 428 units "
            "available and 3.93 days of coverage with HIGH "
            "stockout risk."
        ),
        inventory_status=inventory,
        inventory_coverage_days=3.93,
    )

@pytest.fixture
def retrieved_knowledge():
    return [
        {
            "rank": 1,
            "source": (
                "01_shipment_delay_escalation.pdf"
            ),
            "source_path": (
                "01_shipment_delay_escalation.pdf"
            ),
            "content": (
                "Medium-risk shipments require investigation "
                "and collection of available evidence."
            ),
            "relevance_score": 0.91,
            "metadata": {
                "data_source": "SYNTHETIC_MVP",
            },
        },
        {
            "rank": 2,
            "source": (
                "02_weather_disruption_sop.pdf"
            ),
            "source_path": (
                "02_weather_disruption_sop.pdf"
            ),
            "content": (
                "Low-severity weather does not independently "
                "justify immediate rerouting."
            ),
            "relevance_score": 0.84,
            "metadata": {
                "data_source": "SYNTHETIC_MVP",
            },
        },
    ]


def make_mock_client(
    response_content: str,
):
    message = SimpleNamespace(
        content=response_content
    )

    choice = SimpleNamespace(
        message=message
    )

    response = SimpleNamespace(
        choices=[choice]
    )

    completions = SimpleNamespace(
        create=lambda **kwargs: response
    )

    chat = SimpleNamespace(
        completions=completions
    )

    return SimpleNamespace(
        chat=chat
    )

def test_build_llm_input_contains_structured_inventory(
    inventory_evidence,
    retrieved_knowledge,
):
    result = (
        azure_openai_service
        .build_llm_input(
            shipment_id="SHP-153444",
            risk_level=RiskLevel.HIGH,
            delay_probability=0.82,
            evidence=inventory_evidence,
            retrieved_knowledge=(
                retrieved_knowledge
            ),
        )
    )

    payload = json.loads(
        result
    )

    inventory = payload[
        "collected_evidence"
    ]["inventory_status"]

    assert inventory[
        "available_stock"
    ] == 428

    assert inventory[
        "daily_demand"
    ] == 109

    assert inventory[
        "inventory_coverage_days"
    ] == 3.93

    assert inventory[
        "stockout_risk"
    ] == "HIGH"

    assert inventory[
        "below_safety_stock"
    ] is True

    assert inventory[
        "below_reorder_point"
    ] is True

    assert inventory[
        "incoming_quantity"
    ] == 0

    assert inventory[
        "destination_country_match"
    ] is False

    assert (
        payload["shipment"][
            "delay_duration_days"
        ]
        is None
    )

    assert (
        payload["shipment"][
            "delay_duration_available"
        ]
        is False
    )

def test_build_llm_input_contains_grounded_evidence(
    evidence,
    retrieved_knowledge,
):
    result = azure_openai_service.build_llm_input(
        shipment_id="SHP-153444",
        risk_level=RiskLevel.MEDIUM,
        delay_probability=0.4033,
        evidence=evidence,
        retrieved_knowledge=retrieved_knowledge,
    )

    payload = json.loads(result)

    assert (
        payload["shipment"]["shipment_id"]
        == "SHP-153444"
    )

    assert (
        payload["shipment"]["risk_level"]
        == "MEDIUM"
    )

    assert (
        payload["shipment"]["delay_probability"]
        == 0.4033
    )

    assert (
        payload["collected_evidence"]["weather_summary"]
        == evidence.weather_summary
    )

    assert (
        payload["collected_evidence"]["supplier_status"]
        == evidence.supplier_status
    )

    assert (
        payload[
            "collected_evidence"
        ]["inventory_coverage_days"]
        is None
    )

    assert (
        payload[
            "retrieved_operational_guidance"
        ][0]["source"]
        == "01_shipment_delay_escalation.pdf"
    )

    assert (
        payload[
            "retrieved_operational_guidance"
        ][0]["data_source"]
        == "SYNTHETIC_MVP"
    )


def test_parse_valid_llm_response():
    content = json.dumps(
        {
            "summary": (
                "The shipment requires active monitoring."
            ),
            "risk_factors": [
                "Historical product delay rate is elevated.",
            ],
            "recommended_actions": [
                "Continue monitoring the shipment.",
            ],
        }
    )

    result = (
        azure_openai_service
        .parse_llm_response(content)
    )

    assert result.summary == (
        "The shipment requires active monitoring."
    )

    assert result.risk_factors == [
        "Historical product delay rate is elevated.",
    ]

    assert result.recommended_actions == [
        "Continue monitoring the shipment.",
    ]


def test_parse_empty_response_raises():
    with pytest.raises(
        AzureOpenAIServiceError,
        match="empty briefing response",
    ):
        azure_openai_service.parse_llm_response(
            ""
        )


def test_parse_invalid_json_raises():
    with pytest.raises(
        AzureOpenAIServiceError,
        match="invalid JSON",
    ):
        azure_openai_service.parse_llm_response(
            "This is not JSON."
        )


def test_parse_wrong_schema_raises():
    content = json.dumps(
        {
            "risk_factors": [],
            "recommended_actions": [],
        }
    )

    with pytest.raises(
        AzureOpenAIServiceError,
        match="does not match the briefing schema",
    ):
        azure_openai_service.parse_llm_response(
            content
        )


def test_generate_azure_briefing_returns_structured_content(
    evidence,
    retrieved_knowledge,
    monkeypatch,
):
    response_content = json.dumps(
        {
            "summary": (
                "Shipment SHP-153444 requires active monitoring."
            ),
            "risk_factors": [
                (
                    "Historical product and market delay rates "
                    "are elevated."
                ),
                (
                    "Supplier geographic suitability is "
                    "not verified."
                ),
            ],
            "recommended_actions": [
                "Continue monitoring the shipment.",
                (
                    "Validate the synthetic supplier before "
                    "considering a change."
                ),
                "Obtain inventory coverage.",
            ],
        }
    )

    mock_client = make_mock_client(
        response_content
    )

    monkeypatch.setattr(
        azure_openai_service,
        "get_azure_openai_client",
        lambda: mock_client,
    )

    monkeypatch.setattr(
        azure_openai_service.settings,
        "azure_openai_chat_deployment",
        "logistics-llm",
    )

    result = (
        azure_openai_service
        .generate_azure_briefing(
            shipment_id="SHP-153444",
            risk_level=RiskLevel.MEDIUM,
            delay_probability=0.4033,
            evidence=evidence,
            retrieved_knowledge=(
                retrieved_knowledge
            ),
        )
    )

    assert result.summary == (
        "Shipment SHP-153444 requires active monitoring."
    )

    assert len(result.risk_factors) == 2
    assert len(result.recommended_actions) == 3


def test_generate_requires_retrieved_knowledge(
    evidence,
):
    with pytest.raises(
        AzureOpenAIServiceError,
        match=(
            "requires retrieved operational knowledge"
        ),
    ):
        azure_openai_service.generate_azure_briefing(
            shipment_id="SHP-153444",
            risk_level=RiskLevel.MEDIUM,
            delay_probability=0.4033,
            evidence=evidence,
            retrieved_knowledge=[],
        )


def test_generate_rejects_invalid_probability(
    evidence,
    retrieved_knowledge,
):
    with pytest.raises(
        ValueError,
        match=(
            "Delay probability must be between 0 and 1"
        ),
    ):
        azure_openai_service.generate_azure_briefing(
            shipment_id="SHP-153444",
            risk_level=RiskLevel.MEDIUM,
            delay_probability=1.5,
            evidence=evidence,
            retrieved_knowledge=(
                retrieved_knowledge
            ),
        )


def test_system_prompt_prohibits_invention():
    prompt = " ".join(
        azure_openai_service
        .SYSTEM_PROMPT
        .lower()
        .split()
    )

    assert (
        "do not invent shipment facts"
        in prompt
    )

    assert (
        "do not invent weather conditions"
        in prompt
    )

    assert (
        "do not invent inventory"
        in prompt
    )

    assert (
        "do not invent policy citations"
        in prompt
    )

    assert "synthetic_mvp" in prompt

    assert (
        "does not justify immediate rerouting"
        in prompt
    )

    assert (
        "delay probability"
        in prompt
    )

    assert (
        "not a prediction of delay duration"
        in prompt
    )

    assert (
        "do not claim that a stockout is certain"
        in prompt
    )

    assert (
        "do not treat incoming inventory as guaranteed"
        in prompt
    )

    assert (
        "inventory records"
        in prompt
    )

    assert (
        "synthetic_mvp"
        in prompt
    )

    assert (
        "demonstration data"
        in prompt
    )


def test_azure_failure_uses_service_exception(
    evidence,
    retrieved_knowledge,
    monkeypatch,
):
    def raise_azure_error(**kwargs):
        raise RuntimeError(
            "simulated Azure outage"
        )

    completions = SimpleNamespace(
        create=raise_azure_error
    )

    chat = SimpleNamespace(
        completions=completions
    )

    mock_client = SimpleNamespace(
        chat=chat
    )

    monkeypatch.setattr(
        azure_openai_service,
        "get_azure_openai_client",
        lambda: mock_client,
    )

    monkeypatch.setattr(
        azure_openai_service.settings,
        "azure_openai_chat_deployment",
        "logistics-llm",
    )

    with pytest.raises(
        AzureOpenAIServiceError,
        match="briefing generation failed",
    ):
        azure_openai_service.generate_azure_briefing(
            shipment_id="SHP-153444",
            risk_level=RiskLevel.MEDIUM,
            delay_probability=0.4033,
            evidence=evidence,
            retrieved_knowledge=(
                retrieved_knowledge
            ),
        )