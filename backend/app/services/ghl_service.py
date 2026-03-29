"""
GoHighLevel API Integration Service.

Handles all communication with the GoHighLevel CRM API including
contact management, tags, notes, and task creation.
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from datetime import date, datetime, time, timezone

logger = logging.getLogger(__name__)

from app.utils.exceptions import GHLAPIError


class GHLService:
    """Service class for GoHighLevel API interactions.

    Uses a shared persistent httpx.AsyncClient (connection pool) to avoid
    TCP handshake overhead on every request. This is the primary performance
    optimization — reusing connections cuts ~100-200ms per API call.
    """

    # Shared client pool per (api_key, base_url) combination
    _client: Optional[httpx.AsyncClient] = None

    def __init__(self, api_key: str, location_id: str, base_url: str):
        self.api_key = api_key
        self.location_id = location_id
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Version": "2021-07-28",
        }
        # Create persistent async client with connection pooling
        if GHLService._client is None or GHLService._client.is_closed:
            GHLService._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=25.0, write=10.0, pool=5.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated HTTP request using the shared connection pool.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g. /contacts/)
            json_data: Request body as dictionary
            params: Query parameters

        Returns:
            Parsed JSON response as dictionary

        Raises:
            GHLAPIError: If the API returns a non-2xx status code
        """
        url = f"{self.base_url}{endpoint}"
        client = GHLService._client

        try:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=json_data,
                params=params,
            )

            if response.status_code >= 400:
                error_detail = response.text
                logger.error(
                    "GHL API error %s on %s %s: %s",
                    response.status_code,
                    method,
                    endpoint,
                    error_detail,
                )
                raise GHLAPIError(
                    message=f"GHL API error: {response.status_code} - {error_detail[:200]}",
                    status_code=response.status_code,
                    detail=error_detail,
                )

            return response.json()

        except httpx.RequestError as exc:
            raise GHLAPIError(
                message=f"Failed to connect to GHL API: {str(exc)}",
                status_code=503,
                detail=str(exc),
            )

    # ─── Contact Operations ──────────────────────────────────────────

    async def search_contacts(
        self, query: str, limit: int = 20
    ) -> Dict[str, Any]:
        """Search for existing contacts by name or phone number.

        Args:
            query: Search term (business name or phone)
            limit: Maximum number of results

        Returns:
            Dictionary with 'contacts' list
        """
        params = {
            "locationId": self.location_id,
            "query": query,
            "limit": limit,
        }
        return await self._request("GET", "/contacts/", params=params)

    async def find_contact_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Find a contact by phone number for deduplication.

        Args:
            phone: Phone number to search for

        Returns:
            Contact dictionary if found, None otherwise
        """
        if not phone:
            return None

        result = await self.search_contacts(phone, limit=5)
        contacts = result.get("contacts", [])

        # Match by phone number
        for contact in contacts:
            contact_phone = contact.get("phone", "")
            # Normalize phone numbers for comparison (strip non-digits)
            normalized_query = "".join(filter(str.isdigit, phone))
            normalized_contact = "".join(filter(str.isdigit, contact_phone))
            if normalized_query and normalized_contact and normalized_query in normalized_contact:
                return contact

        return None

    async def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new contact in GoHighLevel.

        Args:
            contact_data: Contact fields (firstName, phone, email, etc.)

        Returns:
            Created contact data including the new contact ID
        """
        payload = {
            "locationId": self.location_id,
            **contact_data,
        }
        return await self._request("POST", "/contacts/", json_data=payload)

    async def update_contact(
        self, contact_id: str, contact_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing contact in GoHighLevel.

        Args:
            contact_id: GHL contact ID
            contact_data: Fields to update

        Returns:
            Updated contact data
        """
        return await self._request(
            "PUT", f"/contacts/{contact_id}", json_data=contact_data
        )

    async def create_or_update_contact(
        self, contact_data: Dict[str, Any]
    ) -> tuple[Dict[str, Any], bool]:
        """Create or update a contact using GHL upsert endpoint (single API call).

        Uses POST /contacts/upsert which GHL handles atomically — no need for a
        separate search call first. This saves ~400-600ms vs search → create/update.

        Args:
            contact_data: Contact fields including phone/email for matching

        Returns:
            Tuple of (contact_data, is_new) where is_new indicates if contact was created
        """
        payload = {
            "locationId": self.location_id,
            **contact_data,
        }

        try:
            result = await self._request("POST", "/contacts/upsert", json_data=payload)
            contact = result.get("contact", result)
            is_new = result.get("traceId") is None  # upsert returns traceId only on create
            # More reliable: check if contact existed before
            is_new = not result.get("existed", False)
            if "id" not in contact and "contact" in result:
                contact = result["contact"]
            return contact, is_new

        except GHLAPIError as e:
            # Fallback: upsert not available, use search + create/update
            logger.warning("Upsert endpoint failed (%s), falling back to search+create", e.status_code)
            phone = contact_data.get("phone")
            existing = await self.find_contact_by_phone(phone)
            if existing:
                contact_id = existing.get("id")
                result = await self.update_contact(contact_id, contact_data)
                contact = result.get("contact", result)
                contact["id"] = contact_id
                return contact, False
            else:
                result = await self.create_contact(contact_data)
                contact = result.get("contact", result)
                return contact, True

    # ─── Tag Operations ──────────────────────────────────────────────

    async def add_tags(self, contact_id: str, tags: List[str]) -> Dict[str, Any]:
        """Add tags to a contact.

        Args:
            contact_id: GHL contact ID
            tags: List of tag names to add

        Returns:
            Updated tags data
        """
        if not tags:
            return {"tags": []}

        payload = {"tags": tags}
        return await self._request(
            "POST", f"/contacts/{contact_id}/tags", json_data=payload
        )

    async def get_tags(self) -> List[Dict[str, Any]]:
        """Get all available tags for the location.

        Uses GET /locations/{locationId}/tags (GHL API v2 2021-07-28).
        Requires scope: locations/tags.readonly or locations/tags.write.

        Returns:
            List of tag objects with id and name
        """
        result = await self._request(
            "GET", f"/locations/{self.location_id}/tags"
        )
        return result.get("tags", [])

    # ─── Tag Operations (single tag helper) ──────────────────────────

    async def add_tag(self, contact_id: str, tag: str) -> Dict[str, Any]:
        """Add a single tag to a contact (convenience wrapper around add_tags).

        Args:
            contact_id: GHL contact ID
            tag: Single tag name to add

        Returns:
            Updated tags data
        """
        return await self.add_tags(contact_id, [tag])

    # ─── Workflow Operations ──────────────────────────────────────────

    async def trigger_workflow(
        self, contact_id: str, workflow_id: str
    ) -> Dict[str, Any]:
        """Trigger a GHL workflow for a contact.

        Args:
            contact_id: GHL contact ID
            workflow_id: GHL workflow ID to trigger

        Returns:
            API response data

        Raises:
            GHLAPIError: If the workflow trigger fails (e.g. not configured, missing scope)
        """
        payload = {"event": "contact_workflow_fired"}
        return await self._request(
            "POST",
            f"/contacts/{contact_id}/workflow/{workflow_id}",
            json_data=payload,
        )

    # ─── Note Operations ─────────────────────────────────────────────

    async def add_note(
        self, contact_id: str, body: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a note to a contact.

        Args:
            contact_id: GHL contact ID
            body: Note text content
            user_id: Optional user ID who created the note

        Returns:
            Created note data
        """
        payload = {"body": body}
        if user_id:
            payload["userId"] = user_id

        return await self._request(
            "POST", f"/contacts/{contact_id}/notes", json_data=payload
        )

    async def get_notes(self, contact_id: str) -> List[Dict[str, Any]]:
        """Get all notes for a contact.

        Args:
            contact_id: GHL contact ID

        Returns:
            List of note objects with id, body, dateAdded, etc.
        """
        result = await self._request("GET", f"/contacts/{contact_id}/notes")
        return result.get("notes", [])

    async def update_note(
        self, contact_id: str, note_id: str, body: str
    ) -> Dict[str, Any]:
        """Update the body of an existing note on a contact.

        Args:
            contact_id: GHL contact ID
            note_id: GHL Note ID to update
            body: New note body text

        Returns:
            Updated note data
        """
        payload = {"body": body}
        return await self._request(
            "PUT",
            f"/contacts/{contact_id}/notes/{note_id}",
            json_data=payload,
        )

    # ─── Task Operations ─────────────────────────────────────────────

    async def create_task(
        self,
        contact_id: str,
        title: str,
        due_date: date,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a follow-up task for a contact.

        Args:
            contact_id: GHL contact ID
            title: Task title
            due_date: Task due date
            description: Optional task description

        Returns:
            Created task data
        """
        # Use noon UTC for the chosen calendar day so GHL/local UI does not show
        # the previous calendar day when midnight UTC is converted to US timezones.
        due_dt = datetime.combine(due_date, time(12, 0, 0), tzinfo=timezone.utc)
        payload = {
            "title": title,
            "dueDate": due_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "completed": False,
            # NOTE: GHL Tasks API does NOT accept "description" field - omit it
        }

        return await self._request(
            "POST", f"/contacts/{contact_id}/tasks", json_data=payload
        )

    # ─── Custom Fields ───────────────────────────────────────────────

    async def get_custom_fields(self) -> List[Dict[str, Any]]:
        """Get all custom fields for the location.

        Returns:
            List of custom field objects
        """
        params = {"locationId": self.location_id}
        result = await self._request(
            "GET", f"/locations/{self.location_id}/customFields", params=params
        )
        return result.get("customFields", [])

    async def update_custom_fields(
        self, contact_id: str, custom_fields: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Update custom field values on a contact.

        Each entry in custom_fields should be:
            {"id": "<field_key_or_id>", "value": "<value>"}

        GHL accepts both the field's key (e.g. "linkedin_url") and its UUID
        as the "id" property. Using key names is preferred for readability.

        Args:
            contact_id: GHL contact ID
            custom_fields: List of {"id": field_key, "value": field_value} dicts

        Returns:
            Updated contact data
        """
        if not custom_fields:
            return {}

        payload = {"customFields": custom_fields}
        return await self._request(
            "PUT", f"/contacts/{contact_id}", json_data=payload
        )

    async def update_social_profiles(
        self,
        contact_id: str,
        linkedin: Optional[str] = None,
        facebook: Optional[str] = None,
        instagram: Optional[str] = None,
        tiktok: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convenience method: update social profile custom fields on a contact.

        Only sends fields that have a non-None value, so partial updates are safe.

        Args:
            contact_id: GHL contact ID
            linkedin: LinkedIn URL
            facebook: Facebook URL
            instagram: Instagram URL
            tiktok: TikTok URL

        Returns:
            Updated contact data or empty dict if nothing to update
        """
        fields_map = {
            "linkedin_url": linkedin,
            "facebook_url": facebook,
            "instagram_url": instagram,
            "tiktok_url": tiktok,
        }

        # Only include fields that have a value
        custom_fields = [
            {"id": key, "value": value}
            for key, value in fields_map.items()
            if value
        ]

        if not custom_fields:
            logger.debug("No social profiles to save for contact %s", contact_id)
            return {}

        return await self.update_custom_fields(contact_id, custom_fields)

    # ─── Opportunity Operations ───────────────────────────────────────

    async def search_opportunities(
        self, contact_id: str, pipeline_id: str
    ) -> Dict[str, Any]:
        """Search for existing opportunities for a contact within a pipeline.

        Args:
            contact_id: GHL contact ID
            pipeline_id: GHL pipeline ID to filter by

        Returns:
            Dictionary with 'opportunities' list
        """
        params = {
            "location_id": self.location_id,
            "contact_id": contact_id,
            "pipeline_id": pipeline_id,
        }
        return await self._request("GET", "/opportunities/search", params=params)

    async def create_opportunity(
        self,
        contact_id: str,
        pipeline_id: str,
        stage_id: str,
        name: str,
    ) -> Dict[str, Any]:
        """Create a new opportunity in a GHL pipeline.

        Args:
            contact_id: GHL contact ID
            pipeline_id: GHL pipeline ID
            stage_id: GHL pipeline stage ID
            name: Opportunity name (typically the business name)

        Returns:
            Created opportunity data including the new opportunity ID
        """
        payload = {
            "pipelineId": pipeline_id,
            "locationId": self.location_id,
            "name": name,
            "pipelineStageId": stage_id,
            "contactId": contact_id,
            "status": "open",
        }
        return await self._request("POST", "/opportunities/", json_data=payload)

    async def update_opportunity_stage(
        self, opportunity_id: str, stage_id: str
    ) -> Dict[str, Any]:
        """Move an existing opportunity to a new pipeline stage.

        Args:
            opportunity_id: GHL opportunity ID
            stage_id: Target pipeline stage ID

        Returns:
            Updated opportunity data
        """
        payload = {"pipelineStageId": stage_id}
        return await self._request(
            "PUT", f"/opportunities/{opportunity_id}", json_data=payload
        )
