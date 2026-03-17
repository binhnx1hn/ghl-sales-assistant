"""
Lead capture API endpoints.

Handles lead capture from the Chrome Extension and lead listing.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.models.lead import (
    LeadCaptureRequest,
    LeadCaptureResponse,
    LeadListResponse,
    ErrorResponse,
)
from app.services.ghl_service import GHLService
from app.services.lead_service import LeadService
from app.dependencies import get_ghl_service
from app.utils.exceptions import GHLAPIError

router = APIRouter()


@router.post(
    "/capture",
    response_model=LeadCaptureResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "GHL API error"},
    },
    summary="Capture a new lead",
    description="Receive lead data from the Chrome Extension, create or update the "
    "contact in GoHighLevel, apply tags, add notes, and create follow-up tasks.",
)
async def capture_lead(
    lead: LeadCaptureRequest,
    ghl_service: GHLService = Depends(get_ghl_service),
):
    """Capture a business lead from the Chrome Extension and save to GHL."""
    try:
        lead_service = LeadService(ghl_service)
        result = await lead_service.capture_lead(lead)
        return result
    except GHLAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to capture lead: {str(e)}",
        )


@router.get(
    "",
    response_model=LeadListResponse,
    summary="List recent leads",
    description="Retrieve recently captured leads from GoHighLevel.",
)
async def list_leads(
    limit: int = 20,
    query: Optional[str] = None,
    ghl_service: GHLService = Depends(get_ghl_service),
):
    """List recently captured leads from GHL."""
    try:
        if query:
            result = await ghl_service.search_contacts(query, limit=limit)
        else:
            result = await ghl_service.search_contacts("", limit=limit)

        contacts = result.get("contacts", [])
        leads = []
        for contact in contacts:
            leads.append(
                {
                    "contact_id": contact.get("id", ""),
                    "business_name": contact.get("companyName")
                    or contact.get("firstName", "Unknown"),
                    "phone": contact.get("phone"),
                    "city": contact.get("city"),
                    "tags": contact.get("tags", []),
                    "created_at": contact.get("dateAdded"),
                }
            )

        return LeadListResponse(leads=leads, total=len(leads))

    except GHLAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list leads: {str(e)}",
        )


@router.post(
    "/duplicate-check",
    summary="Check for duplicate contacts",
    description="Check if a contact with the given phone number already exists in GHL.",
)
async def check_duplicate(
    phone: str,
    ghl_service: GHLService = Depends(get_ghl_service),
):
    """Check if a lead already exists in GHL by phone number."""
    try:
        existing = await ghl_service.find_contact_by_phone(phone)
        if existing:
            return {
                "duplicate": True,
                "contact_id": existing.get("id"),
                "business_name": existing.get("companyName")
                or existing.get("firstName", "Unknown"),
            }
        return {"duplicate": False}

    except GHLAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
