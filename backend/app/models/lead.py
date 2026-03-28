"""
Lead data models for request/response validation.

Defines the Pydantic schemas used for lead capture from the Chrome Extension.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


class LeadCaptureRequest(BaseModel):
    """Request model for capturing a new lead from the Chrome Extension."""

    business_name: str = Field(..., description="Name of the business")
    phone: Optional[str] = Field(None, description="Business phone number")
    website: Optional[str] = Field(None, description="Business website URL")
    address: Optional[str] = Field(None, description="Full street address")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State code (e.g. CO, TX)")
    source_url: str = Field(..., description="URL of the page where lead was captured")
    source_type: str = Field(
        "unknown",
        description="Source type: google_search, google_maps, directory, other",
    )
    rating: Optional[str] = Field(None, description="Business rating if available")
    category: Optional[str] = Field(None, description="Business category (e.g. Nursing Home)")
    note: Optional[str] = Field(None, description="Quick note added by user")
    follow_up_date: Optional[date] = Field(None, description="Follow-up date for the task")
    industry: Optional[str] = Field(None, description="Industry type selected by user (e.g. Restaurants, Medical Offices)")
    tags: List[str] = Field(default_factory=list, description="Tags to apply to the contact")
    social_links: Optional[dict] = Field(None, description="Social profile URLs reviewed by user: {linkedin, facebook, instagram, tiktok}")

    model_config = {
        "json_schema_extra": {
            "example": {
                "business_name": "Sunrise Senior Living",
                "phone": "+1-555-123-4567",
                "website": "https://sunriseseniorliving.com",
                "address": "123 Care Lane",
                "city": "Denver",
                "state": "CO",
                "source_url": "https://www.google.com/maps/place/...",
                "source_type": "google_maps",
                "rating": "4.5",
                "category": "Nursing Home",
                "note": "Large facility, ask about visitor log management",
                "follow_up_date": "2026-03-20",
                "tags": ["Nursing Home", "Denver", "New Lead"],
            }
        }
    }


class LeadCaptureResponse(BaseModel):
    """Response model after successfully capturing a lead."""

    success: bool = True
    message: str = "Lead captured successfully"
    contact_id: str = Field(..., description="GHL contact ID")
    is_new: bool = Field(..., description="True if new contact was created, False if updated")
    business_name: str
    tags_applied: List[str] = Field(default_factory=list)
    note_created: bool = False
    task_created: bool = False


class LeadListItem(BaseModel):
    """Simplified lead item for list responses."""

    contact_id: str
    business_name: str
    phone: Optional[str] = None
    city: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class LeadListResponse(BaseModel):
    """Response model for listing recent leads."""

    leads: List[LeadListItem] = Field(default_factory=list)
    total: int = 0


class ErrorResponse(BaseModel):
    """Standard error response model."""

    success: bool = False
    error: str
    detail: Optional[str] = None
