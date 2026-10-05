from pathlib import Path

from backend.models.schemas import (
    RiskLevel,
    ToolEvidence,
    LLMBriefingContent,
)
from backend.services.briefing_service import (
    generate_rag_briefing,
)
from backend.exceptions import (
    AzureOpenAIServiceError,
)
from backend.services import briefing_service

import pytest


@pytest.fixture(autouse=True)
def mock_external_briefing_dependencies(
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
        (
            "backend.services.briefing_service."
            "retrieve_operational_knowledge"
        ),
        lambda query, k=5: retrieved_documents,
    )

    def mock_generate_azure_briefing(
        shipment_id,
        risk_level,
        delay_probability,
        evidence,
        retrieved_knowledge,
    ):
        summary_parts = [
            (
                f"Shipment {shipment_id} has a "
                f"{risk_level.value} predicted delay risk of "
                f"{delay_probability:.1%}."
            )
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
                evidence.supplier_status
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

        return LLMBriefingContent(
            summary=" ".join(summary_parts),
            risk_factors=[],
            recommended_actions=[
                "Continue human operational review.",
            ],
        )

    monkeypatch.setattr(
        (
            "backend.services.briefing_service."
            "generate_azure_briefing"
        ),
        mock_generate_azure_briefing,
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
        "human"
        in action.lower()
        or "monitor"
        in action.lower()
        for action in briefing.recommended_actions
    )
