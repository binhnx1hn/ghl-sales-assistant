"""
Tests for the Lead Capture API endpoints and GHL service.
"""

import pytest # type: ignore
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date

from app.models.lead import LeadCaptureRequest
from app.services.lead_service import LeadService
from app.services.ghl_service import GHLService


class TestLeadCaptureRequest:
    """Test lead capture request model validation."""

    def test_valid_full_lead(self):
        """Test creating a lead with all fields."""
        lead = LeadCaptureRequest(
            business_name="Sunrise Senior Living",
            phone="+1-555-123-4567",
            website="https://sunriseseniorliving.com",
            address="123 Care Lane",
            city="Denver",
            state="CO",
            source_url="https://www.google.com/maps/place/test",
            source_type="google_maps",
            rating="4.5",
            category="Nursing Home",
            note="Large facility, ask about visitor log management",
            follow_up_date=date(2026, 3, 20),
            tags=["Nursing Home", "Denver", "New Lead"],
        )
        assert lead.business_name == "Sunrise Senior Living"
        assert lead.phone == "+1-555-123-4567"
        assert len(lead.tags) == 3

    def test_minimal_lead(self):
        """Test creating a lead with only required fields."""
        lead = LeadCaptureRequest(
            business_name="Test Business",
            source_url="https://google.com/search?q=test",
        )
        assert lead.business_name == "Test Business"
        assert lead.phone is None
        assert lead.tags == []

    def test_missing_business_name_raises(self):
        """Test that missing business name raises validation error."""
        with pytest.raises(Exception):
            LeadCaptureRequest(
                source_url="https://google.com/search?q=test",
            )


class TestLeadService:
    """Test lead service business logic."""

    @pytest.fixture
    def mock_ghl_service(self):
        """Create a mock GHL service."""
        service = AsyncMock(spec=GHLService)
        service.create_or_update_contact = AsyncMock(
            return_value=({"id": "contact_123"}, True)
        )
        service.add_tags = AsyncMock(return_value={"tags": ["New Lead"]})
        service.add_note = AsyncMock(return_value={"id": "note_123"})
        service.create_task = AsyncMock(return_value={"id": "task_123"})
        return service

    @pytest.mark.asyncio
    async def test_capture_new_lead(self, mock_ghl_service):
        """Test capturing a new lead creates contact, tags, note, and task."""
        lead_service = LeadService(mock_ghl_service)

        lead = LeadCaptureRequest(
            business_name="Test Nursing Home",
            phone="555-123-4567",
            source_url="https://google.com/maps",
            source_type="google_maps",
            note="Test note",
            follow_up_date=date(2026, 3, 20),
            tags=["Nursing Home", "New Lead"],
        )

        result = await lead_service.capture_lead(lead)

        assert result.success is True
        assert result.is_new is True
        assert result.contact_id == "contact_123"
        assert result.note_created is True
        assert result.task_created is True
        assert len(result.tags_applied) == 2

        # Verify GHL service was called correctly
        mock_ghl_service.create_or_update_contact.assert_called_once()
        mock_ghl_service.add_tags.assert_called_once()
        mock_ghl_service.add_note.assert_called_once()
        mock_ghl_service.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_capture_lead_without_followup(self, mock_ghl_service):
        """Test capturing a lead without follow-up date skips task creation."""
        lead_service = LeadService(mock_ghl_service)

        lead = LeadCaptureRequest(
            business_name="Test Business",
            source_url="https://google.com/search",
            source_type="google_search",
        )

        result = await lead_service.capture_lead(lead)

        assert result.success is True
        assert result.task_created is False
        mock_ghl_service.create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_capture_existing_lead_updates(self, mock_ghl_service):
        """Test that existing contacts get updated instead of created."""
        mock_ghl_service.create_or_update_contact = AsyncMock(
            return_value=({"id": "existing_contact"}, False)
        )

        lead_service = LeadService(mock_ghl_service)

        lead = LeadCaptureRequest(
            business_name="Existing Business",
            phone="555-999-8888",
            source_url="https://yelp.com/biz/test",
            source_type="yelp",
        )

        result = await lead_service.capture_lead(lead)

        assert result.success is True
        assert result.is_new is False
        assert result.message == "Existing lead updated"


class TestGHLContactMapping:
    """Test GHL contact data mapping."""

    def test_map_full_lead_to_contact(self):
        """Test mapping a complete lead to GHL contact format."""
        from app.services.lead_service import LeadService

        ghl_mock = MagicMock()
        service = LeadService(ghl_mock)

        lead = LeadCaptureRequest(
            business_name="Sunrise Senior Living",
            phone="+1-555-123-4567",
            website="https://sunriseseniorliving.com",
            address="123 Care Lane",
            city="Denver",
            state="CO",
            source_url="https://google.com/maps",
            source_type="google_maps",
            category="Nursing Home",
            rating="4.5",
        )

        contact = service._map_to_ghl_contact(lead)

        assert contact["firstName"] == "Sunrise Senior Living"
        assert contact["companyName"] == "Sunrise Senior Living"
        assert contact["phone"] == "+1-555-123-4567"
        assert contact["website"] == "https://sunriseseniorliving.com"
        assert contact["city"] == "Denver"
        assert contact["state"] == "CO"
        assert len(contact["customFields"]) == 4  # source_url, source_type, category, rating
