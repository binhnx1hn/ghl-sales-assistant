"""
GHL Sales Assistant - Backend Configuration

Loads environment variables and provides application settings.
"""

from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # GoHighLevel API
    ghl_api_key: str = ""
    ghl_location_id: str = ""
    ghl_base_url: str = "https://services.leadconnectorhq.com"

    # API Security
    api_secret_key: str = "change_this_to_a_random_secret_key"
    allowed_origins: str = "chrome-extension://your_extension_id,http://localhost:3000"

    # Phase 3 — Webhook security
    webhook_secret: Optional[str] = None

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Phase 2A — AI & Search APIs
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    serper_api_key: str = ""
    serper_base_url: str = "https://google.serper.dev"

    # Phase 2A — Email drafter defaults (client can override per request)
    default_sender_name: str = ""
    default_sender_company: str = ""
    default_pitch: str = ""

    # Phase 2B — GHL Workflow IDs for lead tier automation
    ghl_workflow_id_hot: Optional[str] = None
    ghl_workflow_id_warm: Optional[str] = None
    ghl_workflow_id_cold: Optional[str] = None

    # Phase 2B — GHL Pipeline & Stage IDs for Opportunities
    ghl_pipeline_id: Optional[str] = None
    ghl_stage_id_hot: Optional[str] = None
    ghl_stage_id_warm: Optional[str] = None
    ghl_stage_id_cold: Optional[str] = None

    @property
    def cors_origins(self) -> List[str]:
        """Parse allowed origins from comma-separated string."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
