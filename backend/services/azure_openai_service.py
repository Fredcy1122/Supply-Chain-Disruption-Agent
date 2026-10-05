import json
from functools import lru_cache
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from backend.config import settings
from backend.exceptions import AzureOpenAIServiceError
from backend.models.schemas import (
    LLMBriefingContent,
    RiskLevel,
    ToolEvidence,
)


SYSTEM_PROMPT = """
You are a supply-chain disruption analyst.

Generate a concise operational briefing using only the evidence and
retrieved guidance supplied by the application.

Grounding rules:

1. Do not invent shipment facts.
2. Do not invent weather conditions.
3. Do not invent supplier availability or supplier performance.
4. Do not invent inventory levels or inventory coverage.
5. Do not invent policy citations.
6. Do not claim that a recommended action has already been executed.
7. Clearly distinguish model prediction from collected evidence.
8. Treat supplier records and operational documents labelled
   SYNTHETIC_MVP as demonstration data.
9. Recommend human review before changing suppliers, rerouting a
   shipment, reallocating inventory, or changing customer commitments.
10. Low-severity weather alone does not justify immediate rerouting.

Return valid JSON containing exactly these fields:

{
  "summary": "A concise evidence-based assessment.",
  "risk_factors": [
    "A supported risk factor."
  ],
  "recommended_actions": [
    "A grounded action requiring human review where appropriate."
  ]
}
""".strip()


def validate_azure_chat_configuration() -> None:
    """
    Ensure all settings required for Azure chat generation exist.
    """
    missing_settings: list[str] = []

    if not settings.azure_openai_endpoint:
        missing_settings.append(
            "AZURE_OPENAI_ENDPOINT"
        )

    if not settings.azure_openai_api_key:
        missing_settings.append(
            "AZURE_OPENAI_API_KEY"
        )

    if not settings.azure_openai_chat_deployment:
        missing_settings.append(
            "AZURE_OPENAI_CHAT_DEPLOYMENT"
        )

    if missing_settings:
        raise AzureOpenAIServiceError(
            "Missing Azure OpenAI chat configuration: "
            + ", ".join(missing_settings)
        )


@lru_cache(maxsize=1)
def get_azure_openai_client() -> OpenAI:
    """
    Create and cache an OpenAI-compatible client for Azure.
    """
    validate_azure_chat_configuration()

    endpoint = str(
        settings.azure_openai_endpoint
    ).rstrip("/")

    return OpenAI(
        base_url=f"{endpoint}/openai/v1/",
        api_key=settings.azure_openai_api_key,
    )


def build_llm_input(
    shipment_id: str,
    risk_level: RiskLevel,
    delay_probability: float,
    evidence: ToolEvidence,
    retrieved_knowledge: list[dict[str, Any]],
) -> str:
    """
    Build the grounded user input passed to Azure OpenAI.
    """
    knowledge_items: list[dict[str, Any]] = []

    for item in retrieved_knowledge:
        knowledge_items.append(
            {
                "source": item.get(
                    "source",
                    "Unknown source",
                ),
                "content": item.get(
                    "content",
                    "",
                ),
                "relevance_score": item.get(
                    "relevance_score",
                ),
                "data_source": (
                    item.get(
                        "metadata",
                        {},
                    ).get(
                        "data_source",
                        "SYNTHETIC_MVP",
                    )
                ),
            }
        )

    payload = {
        "shipment": {
            "shipment_id": shipment_id,
            "risk_level": risk_level.value,
            "delay_probability": (
                delay_probability
            ),
        },
        "collected_evidence": (
            evidence.model_dump(
                mode="json"
            )
        ),
        "retrieved_operational_guidance": (
            knowledge_items
        ),
        "instructions": [
            (
                "Use only the supplied prediction, evidence, "
                "and retrieved guidance."
            ),
            (
                "Keep the briefing concise and suitable for "
                "an operations team."
            ),
            (
                "Do not recommend immediate rerouting when weather "
                "severity is low unless other supplied evidence "
                "supports rerouting."
            ),
            (
                "Do not describe synthetic suppliers as approved "
                "or contracted suppliers."
            ),
            (
                "Do not claim inventory impact when inventory "
                "coverage is unavailable."
            ),
        ],
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )


def parse_llm_response(
    content: str,
) -> LLMBriefingContent:
    """
    Parse and validate the JSON returned by Azure OpenAI.
    """
    normalized_content = content.strip()

    if not normalized_content:
        raise AzureOpenAIServiceError(
            "Azure OpenAI returned an empty briefing response."
        )

    try:
        response_data = json.loads(
            normalized_content
        )
    except json.JSONDecodeError as exc:
        raise AzureOpenAIServiceError(
            "Azure OpenAI returned invalid JSON: "
            f"{exc}"
        ) from exc

    try:
        return LLMBriefingContent.model_validate(
            response_data
        )
    except ValidationError as exc:
        raise AzureOpenAIServiceError(
            "Azure OpenAI returned JSON that does not match "
            f"the briefing schema: {exc}"
        ) from exc


def generate_azure_briefing(
    shipment_id: str,
    risk_level: RiskLevel,
    delay_probability: float,
    evidence: ToolEvidence,
    retrieved_knowledge: list[dict[str, Any]],
) -> LLMBriefingContent:
    """
    Generate a grounded structured briefing using Azure OpenAI.
    """
    if not 0 <= delay_probability <= 1:
        raise ValueError(
            "Delay probability must be between 0 and 1."
        )

    if not retrieved_knowledge:
        raise AzureOpenAIServiceError(
            "Azure briefing generation requires retrieved "
            "operational knowledge."
        )

    client = get_azure_openai_client()

    user_input = build_llm_input(
        shipment_id=shipment_id,
        risk_level=risk_level,
        delay_probability=delay_probability,
        evidence=evidence,
        retrieved_knowledge=retrieved_knowledge,
    )

    try:
        response = client.chat.completions.create(
            model=(
                settings
                .azure_openai_chat_deployment
            ),
            temperature=0,
            response_format={
                "type": "json_object",
            },
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_input,
                },
            ],
        )
    except Exception as exc:
        raise AzureOpenAIServiceError(
            "Azure OpenAI briefing generation failed: "
            f"{exc}"
        ) from exc

    if not response.choices:
        raise AzureOpenAIServiceError(
            "Azure OpenAI returned no briefing choices."
        )

    content = (
        response
        .choices[0]
        .message
        .content
    )

    if content is None:
        raise AzureOpenAIServiceError(
            "Azure OpenAI returned a briefing without content."
        )

    return parse_llm_response(
        content
    )


def clear_azure_openai_client_cache() -> None:
    """
    Clear the cached Azure OpenAI client for tests or configuration
    replacement.
    """
    get_azure_openai_client.cache_clear()