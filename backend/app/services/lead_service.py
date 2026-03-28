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
        # Step 1: Merge industry into tags (GHL has no native "industry" field)
        if lead.industry and lead.industry not in lead.tags:
            lead.tags = [lead.industry] + lead.tags

        # Step 2 (was 1): Map lead data to GHL contact format
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

        # Save social links if provided by user in popup
        has_social = bool(
            lead.social_links and any(lead.social_links.get(p) for p in ("linkedin", "facebook", "instagram", "tiktok"))
        )
        if has_social:
            coroutines.append(
                self.ghl.update_social_profiles(
                    contact_id=contact_id,
                    linkedin=lead.social_links.get("linkedin") or None,
                    facebook=lead.social_links.get("facebook") or None,
                    instagram=lead.social_links.get("instagram") or None,
                    tiktok=lead.social_links.get("tiktok") or None,
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
            idx += 1

        if has_social:
            social_saved = not isinstance(results[idx], Exception)  # noqa: F841

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
        """Clean and validate a phone number for GHL (E.164 format).

        Handles Vietnamese numbers (0xxxxxxxxx → +84xxxxxxxxx),
        US numbers (10 digits → +1xxxxxxxxxx), and international numbers.
        Returns None if phone is invalid (too short, etc.)

        Args:
            phone: Raw phone string from browser extraction

        Returns:
            E.164 formatted phone string or None if invalid
        """
        if not phone:
            return None

        import re

        # Strip everything except digits and leading +
        digits_only = re.sub(r"[^\d+]", "", phone)
        clean_digits = re.sub(r"\D", "", digits_only)
        digit_count = len(clean_digits)

        # Must have at least 8 digits to be a valid phone number
        if digit_count < 8:
            return None

        # Already has country code prefix (e.g. +84..., +1...)
        if digits_only.startswith("+"):
            return digits_only

        # Vietnamese local number: starts with 0, 10 digits (e.g. 0976635533)
        # → strip leading 0 and prepend +84
        if digit_count == 10 and clean_digits.startswith("0"):
            return f"+84{clean_digits[1:]}"

        # Vietnamese number without leading 0, 9 digits (e.g. 976635533)
        if digit_count == 9 and not clean_digits.startswith("1"):
            return f"+84{clean_digits}"

        # US/Canada number: exactly 10 digits not starting with 0
        if digit_count == 10:
            return f"+1{clean_digits}"

        # 11-digit number starting with 1 (US with country code, no +)
        if digit_count == 11 and clean_digits.startswith("1"):
            return f"+{clean_digits}"

        # Vietnamese 11-digit with country code 84 (e.g. 84976635533)
        if digit_count == 11 and clean_digits.startswith("84"):
            return f"+{clean_digits}"

        # Fallback: prepend + for other international formats
        return f"+{clean_digits}"

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

        # Store additional data in custom fields (use "key" for field lookup by key name)
        custom_fields = []
        if lead.industry:
            custom_fields.append({"key": "industry", "value": lead.industry})
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
