"""
Lead processing business logic.

Orchestrates the lead capture workflow: deduplication, contact creation,
tagging, note creation, and follow-up task scheduling.
"""

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

        # Step 2: Create or update contact (deduplicate by phone)
        contact, is_new = await self.ghl.create_or_update_contact(contact_data)
        contact_id = contact.get("id")

        # Step 3: Apply tags
        tags_applied = []
        if lead.tags:
            await self.ghl.add_tags(contact_id, lead.tags)
            tags_applied = lead.tags

        # Step 4: Add capture note
        note_created = False
        note_body = self._build_capture_note(lead)
        if note_body:
            await self.ghl.add_note(contact_id, note_body)
            note_created = True

        # Step 5: Create follow-up task if date provided
        task_created = False
        if lead.follow_up_date:
            task_title = f"Follow up with {lead.business_name}"
            task_description = (
                f"Follow-up task for lead captured from {lead.source_type}.\n"
                f"Source: {lead.source_url}"
            )
            await self.ghl.create_task(
                contact_id=contact_id,
                title=task_title,
                due_date=lead.follow_up_date,
                description=task_description,
            )
            task_created = True

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

        if lead.phone:
            contact["phone"] = lead.phone
        if lead.website:
            contact["website"] = lead.website
        if lead.address:
            contact["address1"] = lead.address
        if lead.city:
            contact["city"] = lead.city
        if lead.state:
            contact["state"] = lead.state

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
