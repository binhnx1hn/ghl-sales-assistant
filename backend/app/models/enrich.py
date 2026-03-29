"""
Phase 2A: Enrich & Email Drafter — Request/Response Models.

Defines Pydantic schemas for the social profile enrichment and
AI-powered email drafting endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List


class EnrichRequest(BaseModel):
    """Request model for enriching a GHL contact with social profile links."""

    contact_id: str = Field(..., description="GHL contact ID to update")
    business_name: str = Field(..., description="Business name to search for")
    website: Optional[str] = Field(None, description="Business website URL (improves accuracy)")
    city: Optional[str] = Field(None, description="City name (improves accuracy)")
    state: Optional[str] = Field(None, description="State code (improves accuracy)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "contact_id": "abc123xyz",
                "business_name": "Sunrise Senior Living",
                "website": "https://sunriseseniorliving.com",
                "city": "Denver",
                "state": "CO",
            }
        }
    }


class SocialProfiles(BaseModel):
    """Social media profile URLs found for a business."""

    linkedin: Optional[str] = Field(None, description="LinkedIn company page URL")
    facebook: Optional[str] = Field(None, description="Facebook page URL")
    instagram: Optional[str] = Field(None, description="Instagram profile URL")
    tiktok: Optional[str] = Field(None, description="TikTok profile URL")


class SaveProfilesRequest(BaseModel):
    """Request model to save user-confirmed social profiles to a GHL contact."""

    contact_id: str = Field(..., description="GHL contact ID to update")
    linkedin: Optional[str] = Field(None, description="LinkedIn URL (empty string = clear)")
    facebook: Optional[str] = Field(None, description="Facebook URL")
    instagram: Optional[str] = Field(None, description="Instagram URL")
    tiktok: Optional[str] = Field(None, description="TikTok URL")


class EnrichResponse(BaseModel):
    """Response model after enriching a contact with social profile links."""

    success: bool = True
    contact_id: str
    business_name: str
    profiles_found: SocialProfiles
    saved_to_ghl: bool = False
    profiles_count: int = Field(0, description="Number of profiles found")
    candidates: Optional[Dict[str, List[str]]] = Field(
        None,
        description="Top candidate URLs per platform for user selection. "
        "e.g. {'instagram': ['https://instagram.com/a', 'https://instagram.com/b']}",
    )


class DraftEmailRequest(BaseModel):
    """Request model for drafting a personalized email from LinkedIn profile."""

    contact_id: str = Field(..., description="GHL contact ID")
    business_name: str = Field(..., description="Business name")
    linkedin_url: Optional[str] = Field(
        None, description="LinkedIn company/person URL. If not provided, AI will search for it."
    )
    sender_name: Optional[str] = Field(None, description="Sender name (overrides default)")
    sender_company: Optional[str] = Field(None, description="Sender company (overrides default)")
    pitch: Optional[str] = Field(
        None,
        description="Value proposition pitch (overrides default). "
        "Example: 'We help senior care facilities save time with visitor management'",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "contact_id": "abc123xyz",
                "business_name": "Sunrise Senior Living",
                "linkedin_url": "https://linkedin.com/company/sunrise-senior-living",
                "sender_name": "Mai Bui",
                "sender_company": "GHL Sales Assistant",
                "pitch": "We help senior care facilities streamline their CRM and save 5 hours/week",
            }
        }
    }


class EmailDraft(BaseModel):
    """Drafted email subject and body."""

    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body text")


class DraftEmailResponse(BaseModel):
    """Response model after drafting a personalized email."""

    success: bool = True
    contact_id: str
    business_name: str
    linkedin_url: Optional[str] = None
    draft_email: EmailDraft
    saved_as_note: bool = False
    note_id: Optional[str] = None
    profile_data_used: Optional[Dict[str, str]] = Field(
        None,
        description="LinkedIn profile data that was used to generate the email",
    )
