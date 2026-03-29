"""
Phase 2B: Outreach Queue Service.

Manages a per-contact outreach queue using GHL Notes as storage.
Each queue item is serialized into a GHL Note body with a [OUTREACH_QUEUE] prefix.

Note body format:
    [OUTREACH_QUEUE]
    item_id: oq_{contact_id}_{platform}_{unix_timestamp}
    platform: linkedin
    message_type: inmail
    status: pending
    profile_url: https://linkedin.com/company/...
    created_at: 2026-03-29T05:00:00Z
    sent_at:
    char_limit: 2000
    char_count: 487
    ---MESSAGE---
    Hi [Name], I came across Sunrise Senior Living...
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.services.ghl_service import GHLService
from app.services.outreach_drafter_service import OutreachDrafterService
from app.utils.exceptions import GHLAPIError

logger = logging.getLogger(__name__)

NOTE_PREFIX = "[OUTREACH_QUEUE]"
MESSAGE_SEPARATOR = "---MESSAGE---"

# Default message_type per platform
PLATFORM_DEFAULT_MESSAGE_TYPE = {
    "linkedin": "inmail",
    "facebook": "page_dm",
    "instagram": "dm",
    "tiktok": "dm",
}

# Profile URL context key per platform
PLATFORM_PROFILE_URL_KEY = {
    "linkedin": "linkedin_url",
    "facebook": "facebook_url",
    "instagram": "instagram_url",
    "tiktok": "tiktok_url",
}


def _build_item_id(contact_id: str, platform: str) -> str:
    """Generate a unique queue item ID."""
    ts = int(time.time())
    return f"oq_{contact_id}_{platform}_{ts}"


def _serialize_item(item: Dict[str, Any]) -> str:
    """Serialize a queue item dict into a GHL Note body string."""
    sent_at_str = ""
    if item.get("sent_at"):
        sent_at_val = item["sent_at"]
        if isinstance(sent_at_val, datetime):
            sent_at_str = sent_at_val.isoformat()
        else:
            sent_at_str = str(sent_at_val)

    created_at_val = item.get("created_at", datetime.now(timezone.utc))
    if isinstance(created_at_val, datetime):
        created_at_str = created_at_val.isoformat()
    else:
        created_at_str = str(created_at_val)

    lines = [
        NOTE_PREFIX,
        f"item_id: {item['item_id']}",
        f"contact_id: {item['contact_id']}",
        f"platform: {item['platform']}",
        f"message_type: {item['message_type']}",
        f"status: {item.get('status', 'pending')}",
        f"profile_url: {item.get('profile_url') or ''}",
        f"created_at: {created_at_str}",
        f"sent_at: {sent_at_str}",
        f"char_limit: {item.get('char_limit', 0)}",
        f"char_count: {item.get('char_count', 0)}",
        MESSAGE_SEPARATOR,
        item.get("drafted_message", ""),
    ]
    return "\n".join(lines)


def _parse_item(note: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse a GHL Note into a queue item dict. Returns None if not a queue note."""
    body = note.get("body", "")
    if not body.startswith(NOTE_PREFIX):
        return None

    try:
        # Split header from message
        if MESSAGE_SEPARATOR in body:
            header_part, message_part = body.split(MESSAGE_SEPARATOR, 1)
        else:
            header_part = body
            message_part = ""

        # Parse header lines into key-value pairs
        meta: Dict[str, str] = {}
        for line in header_part.strip().splitlines():
            if ": " in line and not line.startswith(NOTE_PREFIX):
                key, _, value = line.partition(": ")
                meta[key.strip()] = value.strip()

        drafted_message = message_part.strip()

        # Parse optional datetime fields
        created_at_str = meta.get("created_at", "")
        sent_at_str = meta.get("sent_at", "")

        created_at: datetime
        try:
            created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.now(timezone.utc)
        except ValueError:
            created_at = datetime.now(timezone.utc)

        sent_at: Optional[datetime] = None
        if sent_at_str:
            try:
                sent_at = datetime.fromisoformat(sent_at_str)
            except ValueError:
                sent_at = None

        return {
            "item_id": meta.get("item_id", ""),
            "contact_id": meta.get("contact_id", ""),
            "platform": meta.get("platform", ""),
            "message_type": meta.get("message_type", ""),
            "status": meta.get("status", "pending"),
            "profile_url": meta.get("profile_url") or None,
            "drafted_message": drafted_message,
            "char_limit": int(meta.get("char_limit", 0)),
            "char_count": int(meta.get("char_count", len(drafted_message))),
            "created_at": created_at,
            "sent_at": sent_at,
            "ghl_note_id": note.get("id"),
            "context_used": None,  # Not serialized to note for brevity
        }

    except Exception as exc:
        logger.warning("Failed to parse outreach queue note %s: %s", note.get("id"), exc)
        return None


class OutreachQueueService:
    """
    Service that manages per-contact outreach queues via GHL Notes.

    GHL Notes are used as a lightweight store — no new DB required.
    Each queue item note body starts with [OUTREACH_QUEUE] for easy filtering.
    """

    def __init__(self, drafter_service: Optional[OutreachDrafterService] = None):
        self.drafter_service = drafter_service or OutreachDrafterService()

    async def create_queue_items(
        self,
        contact_id: str,
        business_name: str,
        platforms: List[str],
        context: Dict[str, Any],
        draft_messages: bool,
        ghl_service: GHLService,
    ) -> List[Dict[str, Any]]:
        """
        Create outreach queue items for multiple platforms.

        For each platform:
          1. Optionally AI-draft a message via OutreachDrafterService
          2. Serialize item into GHL Note body with [OUTREACH_QUEUE] prefix
          3. Save via ghl_service.add_note()
          4. Return list of queue item dicts

        Args:
            contact_id: GHL contact ID
            business_name: Target business name
            platforms: List of platforms (linkedin, facebook, instagram, tiktok)
            context: OutreachQueueContext dict with URLs and sender info
            draft_messages: If True, call AI to draft each message
            ghl_service: Authenticated GHL service instance

        Returns:
            List of created OutreachQueueItem dicts
        """
        created_items: List[Dict[str, Any]] = []
        _t_start_total = time.monotonic()
        logger.info(
            "[TIMING] create_queue_items START — contact=%s platforms=%s draft=%s",
            contact_id, platforms, draft_messages,
        )

        async def _draft_and_save(platform: str) -> Dict[str, Any]:
            """Draft + save one platform item; returns the item dict."""
            _t0 = time.monotonic()
            message_type = PLATFORM_DEFAULT_MESSAGE_TYPE.get(platform, "dm")
            profile_url_key = PLATFORM_PROFILE_URL_KEY.get(platform)
            profile_url = context.get(profile_url_key) if profile_url_key else None

            item_id = _build_item_id(contact_id, platform)
            created_at = datetime.now(timezone.utc)

            drafted_message = ""
            char_count = 0
            char_limit = 0
            context_used: Optional[Dict[str, str]] = None

            if draft_messages:
                try:
                    _t_ai = time.monotonic()
                    draft_result = await self.drafter_service.draft_message(
                        contact_id=contact_id,
                        business_name=business_name,
                        platform=platform,
                        message_type=message_type,
                        profile_url=profile_url,
                        sender_name=context.get("sender_name"),
                        sender_company=context.get("sender_company"),
                        pitch=context.get("pitch"),
                        industry=context.get("industry"),
                    )
                    drafted_message = draft_result["drafted_message"]
                    char_count = draft_result["char_count"]
                    char_limit = draft_result["char_limit"]
                    if draft_result.get("profile_data_used"):
                        context_used = draft_result["profile_data_used"]
                    logger.info(
                        "[TIMING] %s AI draft done in %.2fs", platform, time.monotonic() - _t_ai
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to draft message for platform %s: %s", platform, exc
                    )
                    drafted_message = f"[Draft failed for {platform}. Please write manually.]"
                    char_count = len(drafted_message)
                    try:
                        cfg = self.drafter_service.get_platform_config(platform, message_type)
                        char_limit = cfg["char_limit"]
                    except ValueError:
                        char_limit = 1000

            item: Dict[str, Any] = {
                "item_id": item_id,
                "contact_id": contact_id,
                "platform": platform,
                "message_type": message_type,
                "status": "pending",
                "profile_url": profile_url,
                "drafted_message": drafted_message,
                "char_count": char_count,
                "char_limit": char_limit,
                "created_at": created_at,
                "sent_at": None,
                "ghl_note_id": None,
                "context_used": context_used,
            }

            note_body = _serialize_item(item)
            try:
                _t_note = time.monotonic()
                note_result = await ghl_service.add_note(contact_id, note_body)
                note_id = (
                    note_result.get("note", {}).get("id")
                    or note_result.get("id")
                )
                item["ghl_note_id"] = note_id
                logger.info(
                    "[TIMING] %s GHL note saved in %.2fs → note_id=%s",
                    platform, time.monotonic() - _t_note, note_id,
                )
            except (GHLAPIError, Exception) as exc:
                logger.warning(
                    "Failed to save outreach queue item %s to GHL: %s", item_id, exc
                )

            logger.info("[TIMING] %s total %.2fs", platform, time.monotonic() - _t0)
            return item

        # Run all platforms concurrently — reduces latency from O(N) sequential
        # OpenAI calls to O(1) (bounded by the slowest single call).
        results = await asyncio.gather(
            *[_draft_and_save(p) for p in platforms],
            return_exceptions=False,
        )
        created_items = list(results)
        logger.info(
            "[TIMING] create_queue_items DONE — %d items in %.2fs",
            len(created_items), time.monotonic() - _t_start_total,
        )
        return created_items

    async def get_queue(
        self,
        contact_id: str,
        status_filter: Optional[str],
        ghl_service: GHLService,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all outreach queue items for a contact from GHL Notes.

        Args:
            contact_id: GHL contact ID
            status_filter: Optional status to filter by (pending/sent/skipped)
            ghl_service: Authenticated GHL service instance

        Returns:
            List of OutreachQueueItem dicts matching the filter
        """
        try:
            notes = await ghl_service.get_notes(contact_id)
        except GHLAPIError as exc:
            if exc.status_code == 404:
                raise
            logger.warning("Failed to fetch notes for contact %s: %s", contact_id, exc)
            return []

        items: List[Dict[str, Any]] = []
        for note in notes:
            parsed = _parse_item(note)
            if parsed is None:
                continue

            # Apply status filter
            if status_filter and parsed.get("status") != status_filter:
                continue

            items.append(parsed)

        # Sort by created_at descending (newest first)
        items.sort(key=lambda x: x.get("created_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return items

    async def update_item_status(
        self,
        item_id: str,
        contact_id: str,
        status: str,
        ghl_service: GHLService,
        sent_at: Optional[datetime] = None,
        notes_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update the status of an outreach queue item.

        Finds the GHL Note containing item_id, updates the body with
        new status/sent_at, and returns the updated item.

        Args:
            item_id: The item_id string (oq_{contact_id}_{platform}_{ts})
            contact_id: GHL contact ID (needed to search notes)
            status: New status (sent | skipped)
            ghl_service: Authenticated GHL service instance
            sent_at: Timestamp when message was sent
            notes_text: Optional notes text to append

        Returns:
            Updated OutreachQueueItem dict

        Raises:
            ValueError: If item not found in GHL Notes
        """
        # Fetch all notes and find the matching queue item
        try:
            all_notes = await ghl_service.get_notes(contact_id)
        except GHLAPIError as exc:
            raise ValueError(
                f"Could not fetch notes for contact {contact_id}: {exc.message}"
            ) from exc

        target_note: Optional[Dict[str, Any]] = None
        target_item: Optional[Dict[str, Any]] = None

        for note in all_notes:
            parsed = _parse_item(note)
            if parsed and parsed.get("item_id") == item_id:
                target_note = note
                target_item = parsed
                break

        if target_note is None or target_item is None:
            raise ValueError(f"Outreach queue item '{item_id}' not found in GHL Notes")

        # Update the item fields
        target_item["status"] = status
        if sent_at:
            target_item["sent_at"] = sent_at
        elif status == "sent" and not target_item.get("sent_at"):
            target_item["sent_at"] = datetime.now(timezone.utc)

        # Re-serialize and update the GHL Note
        note_body = _serialize_item(target_item)
        if notes_text:
            note_body += f"\n\n[Notes]: {notes_text}"

        ghl_note_updated = False
        note_id = target_note.get("id")

        if note_id:
            try:
                await ghl_service.update_note(contact_id, note_id, note_body)
                ghl_note_updated = True
                logger.info(
                    "Updated outreach queue item %s → note %s status=%s",
                    item_id,
                    note_id,
                    status,
                )
            except (GHLAPIError, Exception) as exc:
                logger.warning(
                    "Failed to update GHL Note %s for item %s: %s",
                    note_id,
                    item_id,
                    exc,
                )

        target_item["ghl_note_updated"] = ghl_note_updated
        return target_item
