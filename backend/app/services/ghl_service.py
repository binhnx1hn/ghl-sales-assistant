"""
GoHighLevel API Integration Service.

Handles all communication with the GoHighLevel CRM API including
contact management, tags, notes, and task creation.
"""

import httpx
from typing import Optional, Dict, Any, List
from datetime import date, datetime

from app.utils.exceptions import GHLAPIError


class GHLService:
    """Service class for GoHighLevel API interactions."""

    def __init__(self, api_key: str, location_id: str, base_url: str):
        self.api_key = api_key
        self.location_id = location_id
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Version": "2021-07-28",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated HTTP request to the GHL API.

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

        async with httpx.AsyncClient(timeout=30.0) as client:
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
                    raise GHLAPIError(
                        message=f"GHL API error: {response.status_code}",
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
        """Create a new contact or update existing one (deduplicate by phone).

        Args:
            contact_data: Contact fields

        Returns:
            Tuple of (contact_data, is_new) where is_new indicates if contact was created
        """
        phone = contact_data.get("phone")

        # Try to find existing contact by phone
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

        Returns:
            List of tag objects with id and name
        """
        params = {"locationId": self.location_id}
        result = await self._request("GET", "/tags/", params=params)
        return result.get("tags", [])

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
        payload = {
            "title": title,
            "dueDate": datetime.combine(due_date, datetime.min.time()).isoformat() + "Z",
            "completed": False,
        }
        if description:
            payload["description"] = description

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
