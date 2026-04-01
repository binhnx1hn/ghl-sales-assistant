"""
Phase 3 — GHL Webhook Receiver

POST /webhooks/ghl/hot-lead

Receives OpportunityStageUpdate events from GHL Workflow automation when a
contact moves to the Hot Lead pipeline stage.  Immediately ACKs GHL with
HTTP 200 {"received": true} and runs enrichment (social profiles + email
draft) in a FastAPI BackgroundTask — no blocking, no self-HTTP call.
"""

import hmac
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from app.config import settings
from app.services.ai_email_drafter_service import AIEmailDrafterService
from app.services.ghl_service import GHLService
from app.services.social_research_service import SocialResearchService

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

async def _run_hot_lead_enrichment(
    contact_id: str,
    business_name: Optional[str],
    website: Optional[str],
    city: Optional[str],
    state: Optional[str],
) -> None:
    """
    8-step hot-lead enrichment executed asynchronously after the HTTP ACK.
    All exceptions are caught and logged — never raised to the ASGI server.
    """
    try:
        # Step 1 — Instantiate services
        ghl_service = GHLService(
            api_key=settings.ghl_api_key,
            location_id=settings.ghl_location_id,
            base_url=settings.ghl_base_url,
        )
        social_service = SocialResearchService()
        drafter = AIEmailDrafterService()

        # Step 2 — Fetch full contact record (fallback metadata resolution)
        try:
            contact = await ghl_service.get_contact(contact_id)
        except Exception as exc:
            logger.error(
                "Hot lead enrichment aborted — could not fetch contact "
                "contact_id=%s error=%s",
                contact_id,
                exc,
            )
            return

        contact_data = contact.get("contact", contact)
        resolved_name = (
            business_name
            or contact_data.get("companyName")
            or contact_data.get("firstName")
            or "Unknown Business"
        )
        resolved_website = website or contact_data.get("website")
        resolved_city = city or contact_data.get("city")
        resolved_state = state or contact_data.get("state")

        # Step 3 — Fetch recent notes
        try:
            notes = await ghl_service.get_notes(contact_id)
        except Exception as exc:
            logger.warning(
                "Could not fetch notes for contact_id=%s — continuing without notes context. error=%s",
                contact_id,
                exc,
            )
            notes = []

        sorted_notes = sorted(
            notes,
            key=lambda n: n.get("dateAdded") or "",
            reverse=True,
        )
        selected_notes = sorted_notes[:5]
        notes_context = "\n".join(
            [
                f"- {note.get('body', '').strip()}"
                for note in selected_notes
                if note.get("body")
            ]
        ).strip()

        # Step 4 — Find social profiles
        profiles: Dict[str, Any] = {}
        try:
            search_result = await social_service.search_social_profiles_with_candidates(
                business_name=resolved_name,
                website=resolved_website,
                city=resolved_city,
                state=resolved_state,
            )
            profiles = search_result.get("profiles", {})
        except Exception as exc:
            logger.error(
                "Social profile search failed for contact_id=%s — skipping profiles step. error=%s",
                contact_id,
                exc,
            )

        # Step 5 — Save profiles to GHL contact (if any found)
        if any(profiles.values()):
            try:
                await ghl_service.update_social_profiles(
                    contact_id=contact_id,
                    linkedin=profiles.get("linkedin"),
                    facebook=profiles.get("facebook"),
                    instagram=profiles.get("instagram"),
                    tiktok=profiles.get("tiktok"),
                )
            except Exception as exc:
                logger.error(
                    "Failed to save social profiles for contact_id=%s error=%s",
                    contact_id,
                    exc,
                )

        # Step 6 — Draft personalized email
        draft_subject = f"Quick question about {resolved_name}"
        draft_body = ""
        try:
            draft_result = await drafter.draft_email(
                business_name=resolved_name,
                linkedin_url=profiles.get("linkedin"),
                sender_name=settings.default_sender_name or None,
                sender_company=settings.default_sender_company or None,
                pitch=settings.default_pitch or None,
                notes_context=notes_context or None,
            )
            draft_subject = draft_result.get("subject", draft_subject)
            draft_body = draft_result.get("body", "")
        except Exception as exc:
            logger.error(
                "Email drafting failed for contact_id=%s — skipping email draft step. error=%s",
                contact_id,
                exc,
            )

        # Step 7 — Save email draft as GHL note
        note_body = (
            "📧 HOT LEAD EMAIL SUGGESTION\n"
            "────────────────────────────────────────\n"
            f"Subject: {draft_subject}\n\n"
            f"{draft_body}\n"
            "────────────────────────────────────────\n"
            f"LinkedIn: {profiles.get('linkedin') or 'N/A'}\n"
            f"Recent notes used: {len(selected_notes)}\n"
            "(Review before sending)"
        )
        note_id: Optional[str] = None
        try:
            note_result = await ghl_service.add_note(
                contact_id=contact_id, body=note_body
            )
            note_id = note_result.get("note", {}).get("id") or note_result.get("id")
        except Exception as exc:
            logger.error(
                "Failed to save email draft note for contact_id=%s error=%s",
                contact_id,
                exc,
            )

        # Step 8 — Log success
        logger.info(
            "Hot lead enrichment complete: contact_id=%s note_id=%s",
            contact_id,
            note_id,
        )

    except Exception:
        logger.exception(
            "Hot lead enrichment failed for contact_id=%s", contact_id
        )


# ---------------------------------------------------------------------------
# Webhook handler
# ---------------------------------------------------------------------------

@router.post("/ghl/hot-lead")
async def receive_hot_lead_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_webhook_secret: Optional[str] = Header(default=None, alias="X-Webhook-Secret"),
) -> Dict[str, Any]:
    """
    Receive GHL OpportunityStageUpdate webhook for Hot Lead stage transitions.

    Validation chain (in order):
    1. Optional HMAC-safe secret check → 401 on mismatch
    2. Event type filter → 200 skip if not OpportunityStageUpdate
    3. Config guard — ghl_stage_id_hot must be set → 200 skip if missing
    4. Stage filter → 200 skip if pipelineStageId != ghl_stage_id_hot
    5. contactId presence → 200 skip if absent
    6. Enqueue background task → return {"received": true}
    """
    # 1. Secret check (optional — skip if WEBHOOK_SECRET not configured)
    if settings.webhook_secret:
        provided = x_webhook_secret or ""
        if not hmac.compare_digest(provided, settings.webhook_secret):
            logger.warning(
                "Webhook secret mismatch from %s",
                request.client.host if request.client else "unknown",
            )
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    # Parse body — FastAPI will return 422 automatically for invalid JSON;
    # we handle missing-key scenarios below.
    payload: Dict[str, Any] = await request.json()

    # 2. Event type filter
    event_type = payload.get("type", "")
    if event_type != "OpportunityStageUpdate":
        logger.info("Ignored webhook event type: %s", event_type)
        return {"received": True}

    # 3. Config guard
    if not settings.ghl_stage_id_hot:
        logger.warning("GHL_STAGE_ID_HOT not configured — webhook received but ignored")
        return {"received": True}

    # 4. Stage filter
    pipeline_stage_id = payload.get("pipelineStageId", "")
    if pipeline_stage_id != settings.ghl_stage_id_hot:
        logger.info("Ignored stage transition: pipelineStageId=%s", pipeline_stage_id)
        return {"received": True}

    # 5. ContactId presence check
    contact_id = payload.get("contactId")
    if not contact_id:
        logger.error(
            "Webhook missing contactId — type=%s locationId=%s",
            payload.get("type"),
            payload.get("locationId"),
        )
        return {"received": True}

    # Extract optional metadata (webhook contact sub-object takes precedence)
    contact_obj: Dict[str, Any] = payload.get("contact") or {}
    business_name: Optional[str] = (
        contact_obj.get("companyName") or payload.get("name") or None
    )
    website: Optional[str] = contact_obj.get("website") or None
    city: Optional[str] = contact_obj.get("city") or None
    state: Optional[str] = contact_obj.get("state") or None

    # 6. Enqueue background enrichment (non-blocking)
    background_tasks.add_task(
        _run_hot_lead_enrichment,
        contact_id,
        business_name,
        website,
        city,
        state,
    )

    logger.info(
        "Hot lead webhook enqueued: contact_id=%s business_name=%s",
        contact_id,
        business_name,
    )

    # 7. Immediate ACK to GHL
    return {"received": True}
