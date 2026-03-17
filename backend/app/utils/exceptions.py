"""
Custom exception classes and exception handlers for the API.
"""

from fastapi import Request
from fastapi.responses import JSONResponse


class GHLAPIError(Exception):
    """Raised when GoHighLevel API returns an error."""

    def __init__(self, message: str, status_code: int = 500, detail: str = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


class LeadCaptureError(Exception):
    """Raised when lead capture process fails."""

    def __init__(self, message: str, detail: str = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


async def ghl_api_error_handler(request: Request, exc: GHLAPIError) -> JSONResponse:
    """Handle GHL API errors and return a structured response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.message,
            "detail": exc.detail,
        },
    )


async def lead_capture_error_handler(request: Request, exc: LeadCaptureError) -> JSONResponse:
    """Handle lead capture errors and return a structured response."""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": exc.message,
            "detail": exc.detail,
        },
    )
