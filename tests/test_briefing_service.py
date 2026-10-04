from pathlib import Path

from backend.models.schemas import (
    RiskLevel,
    ToolEvidence,
)
from backend.services.briefing_service import (
    generate_rag_briefing,
)

import pytest


@pytest.fixture(autouse=True)
def mock_rag_retrieval(
    monkeypatch,
):
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
                "Medium-risk shipments require "
                "investigation and collection of "
                "available operational evidence."
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
                "Low-severity destination weather "
                "does not independently justify "
                "shipment rerouting."
            ),
            "metadata": {
                "data_source": "SYNTHETIC_MVP",
            },
        },
    ]

    monkeypatch.setattr(
        (
            "backend.services.briefing_service."
            "retrieve_operational_knowledge"
        ),
        lambda query, k=5: retrieved_documents,
    )


def make_briefing(
    evidence: ToolEvidence,
    probability: float = 0.55,
):
    return generate_rag_briefing(
        shipment_id="SHP-153440",
        risk_level=RiskLevel.MEDIUM,
        delay_probability=probability,
        evidence=evidence,
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
        "12 days."
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