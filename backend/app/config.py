"""
GHL Sales Assistant - Backend Configuration

Loads environment variables and provides application settings.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # GoHighLevel API
    ghl_api_key: str = ""
    ghl_location_id: str = ""
    ghl_base_url: str = "https://services.leadconnectorhq.com"

    # API Security
    api_secret_key: str = "change_this_to_a_random_secret_key"
    allowed_origins: str = "chrome-extension://your_extension_id,http://localhost:3000"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    @property
    def cors_origins(self) -> List[str]:
        """Parse allowed origins from comma-separated string."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
