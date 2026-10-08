from pathlib import Path

import pytest

from backend.exceptions import (
    AzureOpenAIServiceError,
)
from backend.models.schemas import (
    LLMBriefingContent,
    RiskLevel,
    ToolEvidence,
    InventoryStatusResponse,
)
from backend.services import briefing_service
from backend.services.briefing_service import (
    generate_rag_briefing,
)


@pytest.fixture(autouse=True)
def mock_external_briefing_dependencies(
    monkeypatch,
):
    """
    Mock RAG retrieval and Azure OpenAI synthesis.

    These tests verify briefing-service behavior without making real
    Azure requests or depending on Chroma retrieval ranking.
    """
    retrieved_documents = [
        {
            "rank": 1,
            "source": (
                "01_shipment_delay_escalation.pdf"
            ),
            "source_path": (
                "01_shipment_delay_escalation.pdf"
            ),
            "relevance_score": 0.91,
            "content": (
                "Medium-risk shipments require investigation and "
                "collection of available operational evidence."
            ),
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
            "relevance_score": 0.84,
            "content": (
                "Low-severity destination weather does not "
                "independently justify shipment rerouting."
            ),
            "metadata": {
                "data_source": "SYNTHETIC_MVP",
            },
        },
    ]

    monkeypatch.setattr(
        briefing_service,
        "retrieve_operational_knowledge",
        lambda query, k=5: retrieved_documents,
    )

    def mock_generate_azure_briefing(
        shipment_id,
        risk_level,
        delay_probability,
        evidence,
        retrieved_knowledge,
    ):
        """
        Return deterministic Azure-style structured content.
        """
        summary_parts = [
            (
                f"Shipment {shipment_id} has a "
                f"{risk_level.value} predicted delay risk of "
                f"{delay_probability:.1%}."
            )
        ]

        risk_factors = []

        if evidence.shipment_summary:
            summary_parts.append(
                evidence.shipment_summary
            )

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
                evidence.supplier_status
            )

            risk_factors.append(
                evidence.supplier_status
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

        recommended_actions = [
            "Continue human operational review.",
        ]

        if evidence.historical_delay_summary:
            recommended_actions.append(
                "Review the elevated historical delay factors."
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

            if severe_weather and not low_weather:
                recommended_actions.append(
                    "Evaluate transport alternatives because the "
                    "collected weather evidence indicates potentially "
                    "severe conditions."
                )

            elif low_weather:
                recommended_actions.append(
                    "Continue monitoring destination weather, but do "
                    "not reroute solely on the current low-severity "
                    "weather evidence."
                )

            else:
                recommended_actions.append(
                    "Continue monitoring destination weather before "
                    "making any rerouting decision."
                )

        if evidence.supplier_status:
            recommended_actions.append(
                "Validate the synthetic supplier geographically, "
                "commercially, and operationally before considering "
                "a supplier change."
            )
        else:
            recommended_actions.append(
                "Obtain supplier availability and performance "
                "evidence before recommending an alternative."
            )

        if evidence.inventory_coverage_days is None:
            recommended_actions.append(
                "Obtain inventory coverage before determining "
                "stockout exposure."
            )

        elif evidence.inventory_coverage_days <= 3:
            recommended_actions.append(
                "Escalate potential stockout exposure because "
                "inventory coverage is three days or less."
            )

        else:
            recommended_actions.append(
                "Compare the expected disruption duration with "
                "available inventory coverage."
            )

        return LLMBriefingContent(
            summary=" ".join(summary_parts),
            risk_factors=risk_factors,
            recommended_actions=recommended_actions,
        )

    monkeypatch.setattr(
        briefing_service,
        "generate_azure_briefing",
        mock_generate_azure_briefing,
    )

def make_inventory_evidence(
    risk_level: RiskLevel,
    coverage: float,
    available_stock: int,
    safety_stock: int,
    reorder_point: int,
    incoming_quantity: int = 0,
    destination_country_match: bool = True,
) -> ToolEvidence:
    inventory = InventoryStatusResponse(
        inventory_id="INV-TEST",
        product_id="PROD-TEST",
        product_name="Trail Running Shoe",
        category="Cleats",
        department="Footwear",
        warehouse_id="WH-TEST",
        warehouse_location="Sao Paulo",
        warehouse_country="Brazil",
        supplier_id="SUP-TEST",
        current_stock=(
            available_stock + 100
        ),
        reserved_stock=100,
        available_stock=available_stock,
        daily_demand=50,
        safety_stock=safety_stock,
        reorder_point=reorder_point,
        incoming_quantity=(
            incoming_quantity
        ),
        expected_replenishment_date=None,
        inventory_coverage_days=coverage,
        stockout_risk=risk_level,
        below_safety_stock=(
            available_stock
            <= safety_stock
        ),
        below_reorder_point=(
            available_stock
            <= reorder_point
        ),
        calculation_verified=True,
        destination_country="Brasil",
        destination_country_match=(
            destination_country_match
        ),
        data_source="SYNTHETIC_MVP",
        limitation=(
            "Inventory records are synthetic "
            "demonstration data."
        ),
    )

    return ToolEvidence(
        inventory_summary=(
            "Synthetic inventory evidence for Trail Running Shoe: "
            f"{available_stock} units available, "
            f"{coverage:g} days of coverage, and "
            f"{risk_level.value} stockout risk."
        ),
        inventory_status=inventory,
        inventory_coverage_days=coverage,
    )

def make_briefing(
    evidence: ToolEvidence,
    probability: float = 0.55,
):
    """
    Generate a briefing using the mocked external dependencies.
    """
    return generate_rag_briefing(
        shipment_id="SHP-153440",
        risk_level=RiskLevel.MEDIUM,
        delay_probability=probability,
        evidence=evidence,
    )

def test_rag_query_contains_structured_inventory():
    evidence = make_inventory_evidence(
        risk_level=RiskLevel.HIGH,
        coverage=3.93,
        available_stock=428,
        safety_stock=572,
        reorder_point=888,
        incoming_quantity=0,
        destination_country_match=False,
    )

    query = briefing_service.build_rag_query(
        shipment_id="SHP-153444",
        risk_level=RiskLevel.HIGH,
        delay_probability=0.82,
        evidence=evidence,
    )

    assert (
        "Available inventory stock: 428 units."
        in query
    )

    assert (
        "Inventory coverage: 3.93 days."
        in query
    )

    assert (
        "Safety stock: 572 units."
        in query
    )

    assert (
        "Reorder point: 888 units."
        in query
    )

    assert (
        "Stockout risk: HIGH."
        in query
    )

    assert (
        "Incoming replenishment quantity: 0 units."
        in query
    )

    assert (
        "Delay probability is not a prediction "
        "of the number of delay days."
        in query
    )

def test_high_inventory_risk_escalates_human_review():
    evidence = make_inventory_evidence(
        risk_level=RiskLevel.HIGH,
        coverage=3.93,
        available_stock=428,
        safety_stock=572,
        reorder_point=888,
    )

    actions = (
        briefing_service
        .build_deterministic_actions(
            risk_level=RiskLevel.HIGH,
            evidence=evidence,
            retrieved_knowledge=[],
        )
    )

    assert any(
        (
            "at or below safety stock"
            in action.lower()
        )
        for action in actions
    )


def test_medium_inventory_risk_reviews_replenishment():
    evidence = make_inventory_evidence(
        risk_level=RiskLevel.MEDIUM,
        coverage=6.0,
        available_stock=300,
        safety_stock=200,
        reorder_point=450,
        incoming_quantity=200,
    )

    actions = (
        briefing_service
        .build_deterministic_actions(
            risk_level=RiskLevel.MEDIUM,
            evidence=evidence,
            retrieved_knowledge=[],
        )
    )

    assert any(
        (
            "review replenishment timing"
            in action.lower()
        )
        for action in actions
    )

    assert any(
        (
            "confirm the recorded incoming quantity"
            in action.lower()
        )
        for action in actions
    )


def test_low_inventory_risk_recommends_monitoring():
    evidence = make_inventory_evidence(
        risk_level=RiskLevel.LOW,
        coverage=16.0,
        available_stock=800,
        safety_stock=200,
        reorder_point=450,
    )

    actions = (
        briefing_service
        .build_deterministic_actions(
            risk_level=RiskLevel.MEDIUM,
            evidence=evidence,
            retrieved_knowledge=[],
        )
    )

    assert any(
        (
            "low stockout risk"
            in action.lower()
        )
        for action in actions
    )   

def test_summary_formats_probability_as_clean_percentage(
    shipment_data,
):
    briefing = make_briefing(
        ToolEvidence(),
        probability=0.55,
    )

    assert (
        "MEDIUM predicted delay risk of 55.0%"
        in briefing.summary
    )

    assert briefing.delay_probability == 0.55
    assert briefing.risk_level == RiskLevel.MEDIUM


def test_summary_reports_unavailable_evidence(
    shipment_data,
):
    briefing = make_briefing(
        ToolEvidence()
    )

    assert (
        "Supplier availability has not yet "
        "been assessed."
        in briefing.summary
    )

    assert (
        "Inventory coverage has not yet "
        "been assessed."
        in briefing.summary
    )

    assert (
        "environmental evidence"
        not in briefing.summary
    )

    assert (
        "RAG policy suggests immediate intervention"
        not in briefing.summary
    )


def test_summary_includes_collected_evidence(
    shipment_data,
):
    evidence = ToolEvidence(
        weather_summary=(
            "Heavy rain at the destination."
        ),
        historical_delay_summary=(
            "Historical delay rates: "
            "product 57.0%."
        ),
        inventory_coverage_days=12,
    )

    briefing = make_briefing(
        evidence
    )

    assert (
        "Heavy rain at the destination."
        in briefing.summary
    )

    assert (
        "Historical delay rates: "
        "product 57.0%."
        in briefing.summary
    )

    assert (
        "Available inventory coverage is "
        "12.0 days."
        in briefing.summary
    )


def test_briefing_returns_real_pdf_citations(
    shipment_data,
):
    briefing = make_briefing(
        ToolEvidence()
    )

    assert briefing.rag_policy_citations

    available_documents = {
        path.name
        for path in Path(
            "rag/documents"
        ).glob("*.pdf")
    }

    assert set(
        briefing.rag_policy_citations
    ).issubset(
        available_documents
    )


def test_briefing_does_not_return_placeholder_sops(
    shipment_data,
):
    briefing = make_briefing(
        ToolEvidence()
    )

    placeholder_citations = {
        (
            "SOP-04: Extreme Weather "
            "Rerouting Protocol"
        ),
        (
            "SOP-12: Inventory Buffer "
            "Utilization for High-Risk "
            "Categories"
        ),
    }

    assert not (
        placeholder_citations
        & set(briefing.rag_policy_citations)
    )


def test_low_severity_weather_does_not_trigger_rerouting(
    shipment_data,
):
    evidence = ToolEvidence(
        weather_summary=(
            "Observed destination weather showed "
            "light drizzle with low severity."
        ),
    )

    briefing = make_briefing(
        evidence
    )

    assert any(
        (
            "do not reroute solely"
            in action.lower()
        )
        for action in briefing.recommended_actions
    )

    assert not any(
        (
            "reroute via secondary transit hub "
            "immediately"
            in action.lower()
        )
        for action in briefing.recommended_actions
    )


def test_severe_weather_supports_transport_review(
    shipment_data,
):
    evidence = ToolEvidence(
        weather_summary=(
            "Observed destination weather showed "
            "heavy rain with high severity."
        ),
    )

    briefing = make_briefing(
        evidence
    )

    assert any(
        (
            "evaluate transport alternatives"
            in action.lower()
        )
        for action in briefing.recommended_actions
    )


def test_supplier_evidence_requires_validation(
    shipment_data,
):
    evidence = ToolEvidence(
        supplier_status=(
            "Synthetic supplier SUP003 has MEDIUM risk, "
            "but geographic suitability is unverified."
        ),
    )

    briefing = make_briefing(
        evidence
    )

    assert (
        evidence.supplier_status
        in briefing.summary
    )

    assert any(
        (
            "validate the synthetic supplier"
            in action.lower()
        )
        for action in briefing.recommended_actions
    )


def test_azure_failure_uses_deterministic_fallback(
    shipment_data,
    monkeypatch,
):
    def broken_azure_generation(**kwargs):
        raise AzureOpenAIServiceError(
            "simulated Azure outage"
        )

    monkeypatch.setattr(
        briefing_service,
        "generate_azure_briefing",
        broken_azure_generation,
    )

    evidence = ToolEvidence(
        historical_delay_summary=(
            "Historical product delay rate is elevated."
        ),
        weather_summary=(
            "Destination weather has low severity."
        ),
        supplier_status=(
            "Synthetic supplier evidence requires "
            "human validation."
        ),
        inventory_coverage_days=None,
    )

    briefing = make_briefing(
        evidence
    )

    assert briefing.summary

    assert (
        "Historical product delay rate is elevated."
        in briefing.summary
    )

    assert (
        "Destination weather has low severity."
        in briefing.summary
    )

    assert briefing.recommended_actions

    assert any(
        (
            "human"
            in action.lower()
            or "monitor"
            in action.lower()
        )
        for action in briefing.recommended_actions
    )