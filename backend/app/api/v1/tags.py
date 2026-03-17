"""
Tags API endpoints.

Provides tag management for the Chrome Extension.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.services.ghl_service import GHLService
from app.dependencies import get_ghl_service
from app.utils.exceptions import GHLAPIError

router = APIRouter()


@router.get(
    "",
    summary="Get available tags",
    description="Retrieve all available tags from the GoHighLevel location.",
)
async def get_tags(
    ghl_service: GHLService = Depends(get_ghl_service),
):
    """Get all tags available in the GHL location."""
    try:
        tags = await ghl_service.get_tags()
        return {"tags": tags}
    except GHLAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve tags: {str(e)}",
        )
