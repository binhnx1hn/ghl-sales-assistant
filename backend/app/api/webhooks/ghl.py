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

    # Debug log: print all received keys so client mis-config is easy to spot
    logger.info("Webhook received — keys=%s", list(payload.keys()))

    # ── Normalise payload ──────────────────────────────────────────────────────
    # GHL Workflow "Webhook" action sends data in several shapes depending on
    # how the client configured the action (custom data vs. auto-send contact).
    # We normalise everything into a single flat dict before validation.
    #
    # Shape A — client added custom key-value pairs (our preferred format):
    #   {"type": "OpportunityStageUpdate", "contactId": "...", "pipelineStageId": "..."}
    #
    # Shape B — GHL auto-send contact data (no custom keys):
    #   {"contact_id": "...", "company_name": "...", "triggerData": {...}, ...}
    #   In this case there is NO "type" or "pipelineStageId" at top level.
    #   We reconstruct them from triggerData / nested objects.
    #
    # Shape C — mixed / partial config (some custom keys + GHL auto fields)

    import json as _json

    # Resolve contact_id — camelCase OR snake_case
    contact_id: Optional[str] = (
        payload.get("contactId")
        or payload.get("contact_id")
        or None
    )

    # Resolve pipeline stage id — camelCase, snake_case, or typo variant
    pipeline_stage_id: str = (
        payload.get("pipelineStageId")
        or payload.get("pipelineStagelc")   # client typo: lc vs Id
        or payload.get("pipeline_stage_id")
        or ""
    )

    # Resolve type — if not set by client, treat any hit on this endpoint
    # as an OpportunityStageUpdate (client configured the trigger correctly,
    # just forgot to add the "type" custom key).
    event_type: str = payload.get("type", "") or "OpportunityStageUpdate"

    # Parse nested contact object (dict OR JSON string)
    raw_contact = payload.get("contact")
    contact_obj: Dict[str, Any] = {}
    if isinstance(raw_contact, dict):
        contact_obj = raw_contact
    elif isinstance(raw_contact, str):
        try:
            parsed = _json.loads(raw_contact)
            if isinstance(parsed, dict):
                contact_obj = parsed
        except Exception:
            pass

    # Extract triggerData sub-object (GHL auto-send mode)
    trigger_data: Dict[str, Any] = payload.get("triggerData") or {}
    if isinstance(trigger_data, str):
        try:
            trigger_data = _json.loads(trigger_data) or {}
        except Exception:
            trigger_data = {}

    # Resolve business name — try all known key variants
    business_name: Optional[str] = (
        payload.get("companyName")
        or payload.get("company_name")
        or contact_obj.get("companyName")
        or contact_obj.get("company_name")
        or trigger_data.get("companyName")
        or payload.get("name")
        or contact_obj.get("name")
        or None
    )

    # Resolve website
    website: Optional[str] = (
        payload.get("website")
        or contact_obj.get("website")
        or trigger_data.get("website")
        or None
    )

    # Resolve city / state
    city: Optional[str] = (
        payload.get("city")
        or contact_obj.get("city")
        or trigger_data.get("city")
        or None
    )
    state: Optional[str] = (
        payload.get("state")
        or contact_obj.get("state")
        or trigger_data.get("state")
        or None
    )

    logger.info(
        "Webhook normalised — event_type=%r contact_id=%s pipeline_stage_id=%r "
        "business_name=%s website=%s",
        event_type, contact_id, pipeline_stage_id, business_name, website,
    )

    # ── Validation ────────────────────────────────────────────────────────────

    # 2. Event type filter
    if event_type != "OpportunityStageUpdate":
        logger.warning(
            "Ignored webhook — type=%r (expected 'OpportunityStageUpdate')",
            event_type,
        )
        return {"received": True}

    # 3. Config guard
    pipeline_configs = settings.opportunity_pipeline_configs
    hot_stage_ids = {
        config["hot"] for config in pipeline_configs if config.get("hot")
    }
    if not hot_stage_ids:
        logger.warning("GHL_STAGE_ID_HOT not configured — webhook received but ignored")
        return {"received": True}

    # 4. Stage filter — skip only if a stage id WAS provided but doesn't match.
    # If no stage id at all (client didn't add the key), pass through and let
    # the contact_id drive the enrichment.
    if pipeline_stage_id and pipeline_stage_id not in hot_stage_ids:
        logger.warning(
            "Ignored stage transition — pipelineStageId=%r not in hot_stage_ids=%s",
            pipeline_stage_id,
            hot_stage_ids,
        )
        return {"received": True}

    # 5. ContactId presence check
    if not contact_id:
        logger.error(
            "Webhook missing contactId — all keys=%s",
            list(payload.keys()),
        )
        return {"received": True}

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
