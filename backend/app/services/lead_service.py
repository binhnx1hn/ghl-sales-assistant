"""
Lead processing business logic.

Orchestrates the lead capture workflow: deduplication, contact creation,
tagging, note creation, and follow-up task scheduling.
"""

import asyncio
from typing import Optional
from datetime import date, datetime, timezone

from app.models.lead import LeadCaptureRequest, LeadCaptureResponse
from app.services.ghl_service import GHLService


class LeadService:
    """Business logic service for processing captured leads."""

    def __init__(self, ghl_service: GHLService):
        self.ghl = ghl_service

    async def capture_lead(self, lead: LeadCaptureRequest) -> LeadCaptureResponse:
        """Process a captured lead from the Chrome Extension.

        This method orchestrates the entire lead capture workflow:
        1. Map lead data to GHL contact format
        2. Create or update the contact (with deduplication)
        3. Apply tags
        4. Add capture note
        5. Create follow-up task if date is provided

        Args:
            lead: Validated lead data from the extension

        Returns:
            LeadCaptureResponse with results of the capture operation
        """
        # Step 1: Map lead data to GHL contact format
        contact_data = self._map_to_ghl_contact(lead)

        # Step 2: Create or update contact (must complete first for contact_id)
        contact, is_new = await self.ghl.create_or_update_contact(contact_data)
        contact_id = contact.get("id")

        # Steps 3+4+5: Run tags, note, and task IN PARALLEL for speed
        # GHL API allows concurrent requests - reduces latency from ~900ms to ~300ms
        note_body = self._build_capture_note(lead)
        task_title = f"Follow up with {lead.business_name}" if lead.follow_up_date else None

        # Build coroutines to run concurrently
        coroutines = []
        if lead.tags:
            coroutines.append(self.ghl.add_tags(contact_id, lead.tags))
        if note_body:
            coroutines.append(self.ghl.add_note(contact_id, note_body))
        if lead.follow_up_date and task_title:
            coroutines.append(
                self.ghl.create_task(
                    contact_id=contact_id,
                    title=task_title,
                    due_date=lead.follow_up_date,
                )
            )

        # Execute all post-contact operations concurrently
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # Determine what succeeded (exceptions are captured, not raised)
        idx = 0
        tags_applied = []
        if lead.tags:
            if not isinstance(results[idx], Exception):
                tags_applied = lead.tags
            idx += 1

        note_created = False
        if note_body:
            note_created = not isinstance(results[idx], Exception)
            idx += 1

        task_created = False
        if lead.follow_up_date and task_title:
            task_created = not isinstance(results[idx], Exception)

        return LeadCaptureResponse(
            success=True,
            message="Lead captured successfully" if is_new else "Existing lead updated",
            contact_id=contact_id,
            is_new=is_new,
            business_name=lead.business_name,
            tags_applied=tags_applied,
            note_created=note_created,
            task_created=task_created,
        )

    def _clean_phone(self, phone: str) -> Optional[str]:
        """Clean and validate a phone number for GHL.

        GHL requires E.164 format or standard US format.
        Returns None if phone is invalid (too short, partial numbers, etc.)

        Args:
            phone: Raw phone string from browser extraction

        Returns:
            Cleaned phone string or None if invalid
        """
        if not phone:
            return None

        # Strip everything except digits and leading +
        import re
        digits_only = re.sub(r"[^\d+]", "", phone)

        # Remove leading + for digit count check
        digit_count = len(re.sub(r"\D", "", digits_only))

        # Must have at least 10 digits (US number without country code)
        if digit_count < 10:
            return None

        # If it looks like a US number (10 digits), add +1 country code
        if digit_count == 10:
            clean_digits = re.sub(r"\D", "", digits_only)
            return f"+1{clean_digits}"

        # If 11 digits starting with 1, add +
        if digit_count == 11 and digits_only.startswith("1"):
            clean_digits = re.sub(r"\D", "", digits_only)
            return f"+{clean_digits}"

        # Otherwise return as-is if starts with +, or add + prefix
        if digits_only.startswith("+"):
            return digits_only
        return f"+{digits_only}"

    def _map_to_ghl_contact(self, lead: LeadCaptureRequest) -> dict:
        """Map lead capture data to GoHighLevel contact format.

        Args:
            lead: Lead data from the extension

        Returns:
            Dictionary formatted for the GHL Contacts API
        """
        contact = {
            "firstName": lead.business_name,
            "companyName": lead.business_name,
            "source": f"Chrome Extension - {lead.source_type}",
        }

        # Clean phone before sending to GHL - invalid format causes 400 error
        cleaned_phone = self._clean_phone(lead.phone) if lead.phone else None
        if cleaned_phone:
            contact["phone"] = cleaned_phone
        if lead.website:
            contact["website"] = lead.website
        if lead.address:
            contact["address1"] = lead.address
        if lead.city:
            contact["city"] = lead.city
        if lead.state:
            contact["state"] = lead.state
        if lead.industry:
            contact["industry"] = lead.industry

        # Store additional data in custom fields
        custom_fields = []
        if lead.source_url:
            custom_fields.append({"key": "source_url", "value": lead.source_url})
        if lead.source_type:
            custom_fields.append({"key": "source_type", "value": lead.source_type})
        if lead.category:
            custom_fields.append({"key": "business_category", "value": lead.category})
        if lead.rating:
            custom_fields.append({"key": "business_rating", "value": lead.rating})

        if custom_fields:
            contact["customFields"] = custom_fields

        return contact

    def _build_capture_note(self, lead: LeadCaptureRequest) -> str:
        """Build a formatted note for the captured lead.

        Args:
            lead: Lead data from the extension

        Returns:
            Formatted note string
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            f"📋 Lead Captured - {timestamp}",
            f"Source: {lead.source_type} ({lead.source_url})",
        ]

        if lead.category:
            lines.append(f"Category: {lead.category}")
        if lead.rating:
            lines.append(f"Rating: {lead.rating}")
        if lead.follow_up_date:
            lines.append(f"Follow-up scheduled: {lead.follow_up_date.isoformat()}")

        # Add user note if provided
        if lead.note:
            lines.append(f"\n📝 Note: {lead.note}")

        return "\n".join(lines)
