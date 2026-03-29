"""
Lead capture API endpoints.

Handles lead capture from the Chrome Extension and lead listing.
Phase 2A adds: /enrich (social profile finder) and /draft-email (AI email drafter).
Phase 2B adds: /classify, /draft-outreach, /outreach-queue (create/get/update).
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
from app.models.phase2b import (
    ClassifyRequest,
    ClassifyResponse,
    DraftOutreachRequest,
    DraftOutreachResponse,
    CreateOutreachQueueRequest,
    CreateOutreachQueueResponse,
    GetOutreachQueueResponse,
    UpdateQueueItemRequest,
    UpdateQueueItemResponse,
    OutreachQueueItem,
)
from app.services.ghl_service import GHLService
from app.services.lead_service import LeadService
from app.services.social_research_service import SocialResearchService
from app.services.ai_email_drafter_service import AIEmailDrafterService
from app.services.lead_classifier_service import LeadClassifierService
from app.services.outreach_drafter_service import OutreachDrafterService
from app.services.outreach_queue_service import OutreachQueueService
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
        # Search for all social profiles with candidates for user selection
        search_result = await social_service.search_social_profiles_with_candidates(
            business_name=request.business_name,
            website=request.website,
            city=request.city,
            state=request.state,
        )
        profiles = search_result["profiles"]
        candidates = search_result["candidates"]

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
            candidates=candidates,
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


# ─── Phase 2B Endpoints ────────────────────────────────────────────────────────


@router.post(
    "/classify",
    response_model=ClassifyResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Missing required fields"},
        500: {"model": ErrorResponse, "description": "AI or GHL API error"},
    },
    summary="Classify a lead into hot/warm/cold tier",
    description=(
        "Phase 2B: Uses OpenAI GPT-4o-mini to score a lead (0-100) and classify "
        "it as hot (≥70), warm (40-69), or cold (<40) based on business signals. "
        "Applies a GHL tag (tier:hot / tier:warm / tier:cold) to the contact. "
        "If trigger_workflow=true and the corresponding GHL workflow ID is configured, "
        "triggers the workflow — failure is graceful (returns workflow_triggered: false)."
    ),
)
async def classify_lead(
    request: ClassifyRequest,
    ghl_service: GHLService = Depends(get_ghl_service),
):
    """Classify a lead into hot/warm/cold and apply GHL tag."""
    if not request.contact_id or not request.business_name:
        raise HTTPException(
            status_code=400,
            detail="contact_id and business_name are required",
        )

    classifier = LeadClassifierService()

    try:
        result = await classifier.classify(
            contact_id=request.contact_id,
            business_name=request.business_name,
            ghl_service=ghl_service,
            website=request.website,
            industry=request.industry,
            city=request.city,
            state=request.state,
            lead_source=request.lead_source,
            linkedin_url=request.linkedin_url,
            employee_count_estimate=request.employee_count_estimate,
            rating=request.rating,
            trigger_workflow=request.trigger_workflow,
        )

        return ClassifyResponse(
            success=True,
            contact_id=request.contact_id,
            business_name=request.business_name,
            tier=result["tier"],
            score=result["score"],
            reasons=result["reasons"],
            workflow_triggered=result["workflow_triggered"],
            workflow_id=result["workflow_id"],
            tag_applied=result["tag_applied"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to classify lead: {str(e)}",
        )


@router.post(
    "/draft-outreach",
    response_model=DraftOutreachResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Unsupported platform/message_type combo"},
        500: {"model": ErrorResponse, "description": "AI API error"},
    },
    summary="Draft a platform-specific outreach message",
    description=(
        "Phase 2B: Uses OpenAI GPT-4o-mini to draft a social media outreach message "
        "with per-platform character limits enforced. "
        "Supported combos: linkedin/inmail (2000), linkedin/connection_request (300), "
        "facebook/page_dm (1000), instagram/dm (1000), tiktok/dm (500)."
    ),
)
async def draft_outreach(
    request: DraftOutreachRequest,
    ghl_service: GHLService = Depends(get_ghl_service),
):
    """Draft a personalized social media outreach message for a given platform."""
    drafter = OutreachDrafterService()

    try:
        result = await drafter.draft_message(
            contact_id=request.contact_id,
            business_name=request.business_name,
            platform=request.platform,
            message_type=request.message_type,
            profile_url=request.profile_url,
            sender_name=request.sender_name,
            sender_company=request.sender_company,
            pitch=request.pitch,
            tone=request.tone,
        )

        return DraftOutreachResponse(
            success=True,
            contact_id=request.contact_id,
            platform=request.platform,
            message_type=request.message_type,
            drafted_message=result["drafted_message"],
            char_count=result["char_count"],
            char_limit=result["char_limit"],
            profile_url=request.profile_url,
            profile_data_used=result.get("profile_data_used"),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to draft outreach message: {str(e)}",
        )


@router.post(
    "/outreach-queue",
    response_model=CreateOutreachQueueResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid platforms"},
        500: {"model": ErrorResponse, "description": "Service error"},
    },
    summary="Create outreach queue items for a contact",
    description=(
        "Phase 2B: Creates outreach queue items for one or more platforms. "
        "If draft_messages=true (default), AI-drafts a message for each platform. "
        "Each item is stored as a GHL Note with [OUTREACH_QUEUE] prefix for retrieval."
    ),
)
async def create_outreach_queue(
    request: CreateOutreachQueueRequest,
    ghl_service: GHLService = Depends(get_ghl_service),
):
    """Create per-platform outreach queue items stored as GHL Notes."""
    valid_platforms = {"linkedin", "facebook", "instagram", "tiktok"}
    invalid = [p for p in request.platforms if p not in valid_platforms]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platforms: {invalid}. Must be one of {sorted(valid_platforms)}",
        )

    queue_service = OutreachQueueService()
    context_dict = request.context.model_dump()

    try:
        items = await queue_service.create_queue_items(
            contact_id=request.contact_id,
            business_name=request.business_name,
            platforms=request.platforms,
            context=context_dict,
            draft_messages=request.draft_messages,
            ghl_service=ghl_service,
        )

        queue_items = [OutreachQueueItem(**item) for item in items]

        return CreateOutreachQueueResponse(
            success=True,
            contact_id=request.contact_id,
            items_created=len(queue_items),
            items=queue_items,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create outreach queue: {str(e)}",
        )


@router.get(
    "/outreach-queue/{contact_id}",
    response_model=GetOutreachQueueResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Contact not found"},
        500: {"model": ErrorResponse, "description": "Service error"},
    },
    summary="Get outreach queue items for a contact",
    description=(
        "Phase 2B: Fetches all outreach queue items for a contact by reading GHL Notes "
        "with the [OUTREACH_QUEUE] prefix and parsing them back into structured items. "
        "Optionally filter by status: pending | sent | skipped."
    ),
)
async def get_outreach_queue(
    contact_id: str,
    status: Optional[str] = Query(
        None,
        description="Filter by status: pending | sent | skipped",
    ),
    ghl_service: GHLService = Depends(get_ghl_service),
):
    """Fetch and parse outreach queue items for a contact from GHL Notes."""
    queue_service = OutreachQueueService()

    try:
        items = await queue_service.get_queue(
            contact_id=contact_id,
            status_filter=status,
            ghl_service=ghl_service,
        )

        queue_items = [OutreachQueueItem(**item) for item in items]

        return GetOutreachQueueResponse(
            success=True,
            contact_id=contact_id,
            total=len(queue_items),
            items=queue_items,
        )

    except GHLAPIError as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Contact {contact_id} not found")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch outreach queue: {str(e)}",
        )


@router.patch(
    "/outreach-queue/{item_id}",
    response_model=UpdateQueueItemResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Queue item not found"},
        500: {"model": ErrorResponse, "description": "Service error"},
    },
    summary="Update outreach queue item status",
    description=(
        "Phase 2B: Updates the status of an outreach queue item (sent | skipped). "
        "Finds the GHL Note by item_id embedded in the note body, "
        "updates the note body with new status and sent_at timestamp."
    ),
)
async def update_outreach_queue_item(
    item_id: str,
    request: UpdateQueueItemRequest,
    contact_id: str = Query(..., description="GHL contact ID the item belongs to"),
    ghl_service: GHLService = Depends(get_ghl_service),
):
    """Update status of an outreach queue item and sync the GHL Note."""
    queue_service = OutreachQueueService()

    try:
        updated = await queue_service.update_item_status(
            item_id=item_id,
            contact_id=contact_id,
            status=request.status,
            ghl_service=ghl_service,
            sent_at=request.sent_at,
            notes_text=request.notes,
        )

        return UpdateQueueItemResponse(
            success=True,
            item_id=item_id,
            status=updated["status"],
            ghl_note_updated=updated.get("ghl_note_updated", False),
        )

    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except GHLAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update outreach queue item: {str(e)}",
        )
