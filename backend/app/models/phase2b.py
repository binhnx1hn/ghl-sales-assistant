"""
Phase 2B: Lead Classifier, Outreach Drafter, Outreach Queue — Request/Response Models.

Defines Pydantic schemas for:
- Lead classification (tier: hot/warm/cold) with GHL workflow triggers
- Outreach message drafting (per-platform character limits)
- Outreach queue management via GHL Notes
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal
from datetime import datetime


# ─── Lead Classifier ─────────────────────────────────────────────────────────

class ClassifyRequest(BaseModel):
    """Request model for AI-powered lead tier classification."""

    contact_id: str = Field(..., description="GHL contact ID")
    business_name: str = Field(..., description="Business name")
    website: Optional[str] = Field(None, description="Business website URL")
    industry: Optional[str] = Field(None, description="Industry vertical")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State code")
    lead_source: Optional[str] = Field(
        None,
        description="Lead source: google_maps | google_search | directory | etc.",
    )
    linkedin_url: Optional[str] = Field(None, description="LinkedIn company/person URL")
    employee_count_estimate: Optional[str] = Field(
        None, description="Employee count estimate (e.g. '10-50', '50-200')"
    )
    rating: Optional[str] = Field(
        None, description="Business rating (e.g. '4.2' from Google Maps)"
    )
    trigger_workflow: bool = Field(
        False,
        description="If true, trigger the configured GHL workflow for the tier",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "contact_id": "abc123xyz",
                "business_name": "Sunrise Senior Living",
                "website": "https://sunriseseniorliving.com",
                "industry": "Senior Care",
                "city": "Denver",
                "state": "CO",
                "lead_source": "google_maps",
                "linkedin_url": "https://linkedin.com/company/sunrise-senior-living",
                "employee_count_estimate": "50-200",
                "rating": "4.5",
                "trigger_workflow": False,
            }
        }
    }


class ClassifyResponse(BaseModel):
    """Response model after classifying a lead into hot/warm/cold tier."""

    success: bool = True
    contact_id: str
    business_name: str
    tier: Literal["hot", "warm", "cold"] = Field(
        ..., description="Lead tier determined by AI scoring"
    )
    score: int = Field(..., ge=0, le=100, description="Score 0-100")
    reasons: List[str] = Field(..., description="Scoring reasons from AI")
    workflow_triggered: bool = Field(
        False, description="Whether a GHL workflow was triggered"
    )
    workflow_id: Optional[str] = Field(
        None, description="ID of the workflow that was triggered (if any)"
    )
    tag_applied: str = Field(..., description="GHL tag applied (e.g. 'tier:hot')")
    opportunity_action: Optional[str] = Field(
        None,
        description="Opportunity upsert result: 'created' | 'updated' | 'skipped' | 'failed'",
    )
    opportunity_id: Optional[str] = Field(
        None, description="GHL Opportunity ID (if created or updated)"
    )


# ─── Outreach Queue Item ──────────────────────────────────────────────────────

class OutreachQueueItem(BaseModel):
    """A single outreach queue item stored as a GHL Note."""

    item_id: str = Field(
        ..., description="Unique ID: oq_{contact_id}_{platform}_{unix_ts}"
    )
    contact_id: str
    platform: Literal["linkedin", "facebook", "instagram", "tiktok"]
    message_type: Literal["inmail", "connection_request", "page_dm", "dm"]
    status: Literal["pending", "sent", "skipped"] = "pending"
    profile_url: Optional[str] = Field(None, description="Target profile URL")
    drafted_message: str = Field(..., description="AI-drafted outreach message")
    char_count: int = Field(..., description="Character count of drafted message")
    char_limit: int = Field(..., description="Platform character limit")
    created_at: datetime
    sent_at: Optional[datetime] = None
    ghl_note_id: Optional[str] = Field(
        None, description="GHL Note ID where item is stored"
    )
    context_used: Optional[Dict[str, str]] = Field(
        None, description="Context data used for drafting"
    )


# ─── Outreach Queue Context ───────────────────────────────────────────────────

class OutreachQueueContext(BaseModel):
    """Context used when drafting outreach messages for the queue."""

    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    industry: Optional[str] = None
    sender_name: Optional[str] = None
    sender_company: Optional[str] = None
    pitch: Optional[str] = None


# ─── Create Outreach Queue ────────────────────────────────────────────────────

class CreateOutreachQueueRequest(BaseModel):
    """Request model to create outreach queue items for multiple platforms."""

    contact_id: str = Field(..., description="GHL contact ID")
    business_name: str = Field(..., description="Target business name")
    platforms: List[Literal["linkedin", "facebook", "instagram", "tiktok"]] = Field(
        ..., description="Platforms to create queue items for"
    )
    context: OutreachQueueContext = Field(
        ..., description="Context for drafting messages"
    )
    draft_messages: bool = Field(
        True, description="If true, AI-draft a message for each platform"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "contact_id": "abc123xyz",
                "business_name": "Sunrise Senior Living",
                "platforms": ["linkedin", "facebook"],
                "context": {
                    "linkedin_url": "https://linkedin.com/company/sunrise-senior-living",
                    "sender_name": "Mai Bui",
                    "sender_company": "GHL Sales Assistant",
                    "pitch": "We help senior care facilities save time with visitor management",
                },
                "draft_messages": True,
            }
        }
    }


class CreateOutreachQueueResponse(BaseModel):
    """Response model after creating outreach queue items."""

    success: bool = True
    contact_id: str
    items_created: int
    items: List[OutreachQueueItem]


# ─── Get Outreach Queue ───────────────────────────────────────────────────────

class GetOutreachQueueResponse(BaseModel):
    """Response model listing outreach queue items for a contact."""

    success: bool = True
    contact_id: str
    total: int
    items: List[OutreachQueueItem]


# ─── Draft Outreach Message ───────────────────────────────────────────────────

class DraftOutreachRequest(BaseModel):
    """Request model for drafting a single platform outreach message."""

    contact_id: str = Field(..., description="GHL contact ID")
    business_name: str = Field(..., description="Target business name")
    platform: Literal["linkedin", "facebook", "instagram", "tiktok"] = Field(
        ..., description="Target social platform"
    )
    message_type: Literal["inmail", "connection_request", "page_dm", "dm"] = Field(
        ..., description="Message type for the platform"
    )
    profile_url: Optional[str] = Field(None, description="Target profile URL")
    sender_name: Optional[str] = Field(None, description="Sender name")
    sender_company: Optional[str] = Field(None, description="Sender company")
    pitch: Optional[str] = Field(None, description="Value proposition pitch")
    tone: Optional[str] = Field("professional", description="Desired tone")

    model_config = {
        "json_schema_extra": {
            "example": {
                "contact_id": "abc123xyz",
                "business_name": "Sunrise Senior Living",
                "platform": "linkedin",
                "message_type": "inmail",
                "profile_url": "https://linkedin.com/company/sunrise-senior-living",
                "sender_name": "Mai Bui",
                "sender_company": "GHL Sales Assistant",
                "pitch": "We help senior care facilities save time",
                "tone": "professional",
            }
        }
    }


class DraftOutreachResponse(BaseModel):
    """Response model for a drafted platform outreach message."""

    success: bool = True
    contact_id: str
    platform: str
    message_type: str
    drafted_message: str = Field(..., description="AI-drafted outreach message")
    char_count: int = Field(..., description="Character count of drafted message")
    char_limit: int = Field(..., description="Platform character limit enforced")
    profile_url: Optional[str] = None
    profile_data_used: Optional[Dict[str, str]] = Field(
        None, description="Profile data that was used to personalize the message"
    )


# ─── Update Queue Item ────────────────────────────────────────────────────────

class UpdateQueueItemRequest(BaseModel):
    """Request model for updating the status of an outreach queue item."""

    status: Literal["sent", "skipped"] = Field(
        ..., description="New status for the item"
    )
    sent_at: Optional[datetime] = Field(
        None, description="Timestamp when the message was sent"
    )
    notes: Optional[str] = Field(None, description="Optional notes about the update")


class UpdateQueueItemResponse(BaseModel):
    """Response model after updating an outreach queue item status."""

    success: bool = True
    item_id: str
    status: str
    ghl_note_updated: bool = Field(
        ..., description="Whether the GHL Note was successfully updated"
    )
