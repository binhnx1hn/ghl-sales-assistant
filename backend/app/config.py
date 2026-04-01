"""
GHL Sales Assistant - Backend Configuration

Loads environment variables and provides application settings.
"""

from pydantic_settings import BaseSettings
from typing import List, Optional, Dict


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
    ghl_pipeline_ids: Optional[str] = None
    ghl_stage_ids_hot: Optional[str] = None
    ghl_stage_ids_warm: Optional[str] = None
    ghl_stage_ids_cold: Optional[str] = None

    @property
    def cors_origins(self) -> List[str]:
        """Parse allowed origins from comma-separated string."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @staticmethod
    def _parse_csv(value: Optional[str]) -> List[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def opportunity_pipeline_configs(self) -> List[Dict[str, str]]:
        """Return normalized pipeline-stage configs for opportunity upsert."""
        pipeline_ids = self._parse_csv(self.ghl_pipeline_ids)
        hot_ids = self._parse_csv(self.ghl_stage_ids_hot)
        warm_ids = self._parse_csv(self.ghl_stage_ids_warm)
        cold_ids = self._parse_csv(self.ghl_stage_ids_cold)

        if pipeline_ids:
            # Only keep complete configs to avoid partial misrouting.
            count = min(len(pipeline_ids), len(hot_ids), len(warm_ids), len(cold_ids))
            return [
                {
                    "pipeline_id": pipeline_ids[i],
                    "hot": hot_ids[i],
                    "warm": warm_ids[i],
                    "cold": cold_ids[i],
                }
                for i in range(count)
            ]

        if (
            self.ghl_pipeline_id
            and self.ghl_stage_id_hot
            and self.ghl_stage_id_warm
            and self.ghl_stage_id_cold
        ):
            return [
                {
                    "pipeline_id": self.ghl_pipeline_id,
                    "hot": self.ghl_stage_id_hot,
                    "warm": self.ghl_stage_id_warm,
                    "cold": self.ghl_stage_id_cold,
                }
            ]

        return []

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
