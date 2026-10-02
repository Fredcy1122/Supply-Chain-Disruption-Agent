from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Absolute path to the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Central configuration for the backend application."""

    # Application
    app_name: str = "Supply-Chain Disruption Agent API"
    app_environment: str = "development"
    debug: bool = False
    mock_mode: bool = False

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # Shipment Tool
    shipment_data_path: Path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "shipment_tool_data.csv"
    )

    model_data_path: Path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "df_model.zip"
    )

    # Machine-learning artifacts
    model_path: Path = (
        PROJECT_ROOT
        / "models"
        / "xgb_model.joblib"
    )

    preprocessor_path: Path = (
        PROJECT_ROOT
        / "models"
        / "preprocessor.joblib"
    )

    # Provisional until validation-based threshold selection is finalized.
    risk_threshold: float = 0.40
    high_risk_threshold: float = 0.70

    # RAG
    rag_persist_directory: Path = (
        PROJECT_ROOT
        / "rag"
        / "vector_store"
    )
    rag_collection_name: str = "operational_sops"

    # Azure OpenAI
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_deployment_name: str | None = None
    azure_openai_api_version: str | None = None

    # Weather Tool
    weather_api_base_url: str | None = None
    weather_api_key: str | None = None

    # Supplier Tool
    supplier_data_path: Path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "supplier_tool_data.csv"
    )

    # Inventory Tool
    inventory_data_path: Path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "inventory_tool_data.csv"
    )

    # Read environment-variable overrides from the local .env file.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Create and cache one settings object per backend process."""
    return Settings()


settings = get_settings()