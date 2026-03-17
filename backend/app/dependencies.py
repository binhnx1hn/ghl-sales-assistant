"""
Dependency injection for FastAPI endpoints.

Provides shared dependencies like GHL service instances.
"""

from app.services.ghl_service import GHLService
from app.config import settings


def get_ghl_service() -> GHLService:
    """Provide a GHL service instance for API endpoints."""
    return GHLService(
        api_key=settings.ghl_api_key,
        location_id=settings.ghl_location_id,
        base_url=settings.ghl_base_url,
    )
