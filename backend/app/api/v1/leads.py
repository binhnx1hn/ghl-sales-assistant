"""
Lead capture API endpoints.

Handles lead capture from the Chrome Extension and lead listing.
Phase 2A adds: /enrich (social profile finder) and /draft-email (AI email drafter).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.models.lead import (
    LeadCaptureRequest,
    LeadCaptureResponse,
    LeadListResponse,
    ErrorResponse,
)
from app.models.enrich import (
    EnrichRequest,
    EnrichResponse,
    SocialProfiles,
    SaveProfilesRequest,
    DraftEmailRequest,
    DraftEmailResponse,
    EmailDraft,
)
from app.services.ghl_service import GHLService
from app.services.lead_service import LeadService
from app.services.social_research_service import SocialResearchService
from app.services.ai_email_drafter_service import AIEmailDrafterService
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


@router.post(
    "/enrich",
    response_model=EnrichResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Search or GHL API error"},
    },
    summary="Find social profiles for a contact",
    description=(
        "Phase 2A: Uses Serper.dev Google Search to find LinkedIn, Facebook, Instagram, "
        "and TikTok profiles for a business. Found URLs are saved as GHL custom fields."
    ),
)
async def enrich_lead(
    request: EnrichRequest,
    save: bool = Query(False, description="If true, immediately save found profiles to GHL. If false (default), return results for user review."),
    ghl_service: GHLService = Depends(get_ghl_service),
):
    """Find social media profiles for an existing GHL contact.

    By default (save=false) returns found profiles without saving — caller must
    confirm and call /save-profiles to persist. Pass save=true for legacy behaviour.
    """
    social_service = SocialResearchService()

    try:
        # Search for all social profiles
        profiles = await social_service.search_social_profiles(
            business_name=request.business_name,
            website=request.website,
            city=request.city,
            state=request.state,
        )

        # Save found profiles as GHL contact custom fields only if requested
        saved = False
        if save:
            try:
                await ghl_service.update_social_profiles(
                    contact_id=request.contact_id,
                    linkedin=profiles.get("linkedin"),
                    facebook=profiles.get("facebook"),
                    instagram=profiles.get("instagram"),
                    tiktok=profiles.get("tiktok"),
                )
                saved = True
            except GHLAPIError as ghl_err:
                import logging
                logging.getLogger(__name__).warning(
                    "Could not save social profiles to GHL contact %s: %s",
                    request.contact_id,
                    ghl_err.message,
                )

        profiles_count = sum(1 for v in profiles.values() if v)

        return EnrichResponse(
            success=True,
            contact_id=request.contact_id,
            business_name=request.business_name,
            profiles_found=SocialProfiles(**profiles),
            saved_to_ghl=saved,
            profiles_count=profiles_count,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enrich lead: {str(e)}",
        )


@router.post(
    "/save-profiles",
    summary="Save confirmed social profiles to a GHL contact",
    description="Phase 2A: Saves user-reviewed social profile URLs to GHL contact custom fields.",
)
async def save_profiles(
    request: SaveProfilesRequest,
    ghl_service: GHLService = Depends(get_ghl_service),
):
    """Save user-confirmed social profiles to a GHL contact."""
    try:
        await ghl_service.update_social_profiles(
            contact_id=request.contact_id,
            linkedin=request.linkedin or None,
            facebook=request.facebook or None,
            instagram=request.instagram or None,
            tiktok=request.tiktok or None,
        )
        return {"success": True, "contact_id": request.contact_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save profiles: {str(e)}")


@router.post(
    "/draft-email",
    response_model=DraftEmailResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "AI or GHL API error"},
    },
    summary="Draft a personalized email from LinkedIn profile",
    description=(
        "Phase 2A: Uses OpenAI GPT-4o-mini to draft a personalized cold outreach email "
        "based on a LinkedIn profile fetched via Google Search (Serper.dev). "
        "The draft is saved as a GHL note on the contact record."
    ),
)
async def draft_email(
    request: DraftEmailRequest,
    ghl_service: GHLService = Depends(get_ghl_service),
):
    """Draft a personalized outreach email using AI and save it as a GHL note."""
    drafter = AIEmailDrafterService()

    try:
        # Generate email draft using AI
        result = await drafter.draft_email(
            business_name=request.business_name,
            linkedin_url=request.linkedin_url,
            sender_name=request.sender_name,
            sender_company=request.sender_company,
            pitch=request.pitch,
        )

        draft_subject = result["subject"]
        draft_body = result["body"]
        resolved_linkedin_url = result.get("linkedin_url")
        profile_data = result.get("profile_data", {})

        # Save the draft as a GHL note on the contact
        note_id = None
        saved_as_note = False
        note_body = (
            f"📧 AI DRAFTED EMAIL\n"
            f"{'─' * 40}\n"
            f"Subject: {draft_subject}\n\n"
            f"{draft_body}\n"
            f"{'─' * 40}\n"
            f"Generated from LinkedIn: {resolved_linkedin_url or 'N/A'}\n"
            f"(Review and personalize before sending)"
        )

        try:
            note_result = await ghl_service.add_note(
                contact_id=request.contact_id,
                body=note_body,
            )
            note_id = note_result.get("note", {}).get("id") or note_result.get("id")
            saved_as_note = True
        except GHLAPIError as ghl_err:
            import logging
            logging.getLogger(__name__).warning(
                "Could not save email draft note to GHL contact %s: %s",
                request.contact_id,
                ghl_err.message,
            )

        return DraftEmailResponse(
            success=True,
            contact_id=request.contact_id,
            business_name=request.business_name,
            linkedin_url=resolved_linkedin_url,
            draft_email=EmailDraft(subject=draft_subject, body=draft_body),
            saved_as_note=saved_as_note,
            note_id=note_id,
            profile_data_used=profile_data if profile_data else None,
        )

    except ValueError as e:
        # Config errors (missing API keys etc.)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to draft email: {str(e)}",
        )
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
