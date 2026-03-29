"""
Phase 2A: Social Research Service.

Uses Serper.dev (Google Search API) to find public social media profiles
(LinkedIn, Facebook, Instagram, TikTok) for a business by name and location.
All data used is publicly available — no platform login required.
"""

import logging
import re
from typing import Optional, Dict, Any, List
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Mapping of platform name -> list of accepted domain patterns
PLATFORM_DOMAINS: Dict[str, List[str]] = {
    "linkedin": ["linkedin.com/company/", "linkedin.com/in/"],
    "facebook": ["facebook.com/", "fb.com/"],
    "instagram": ["instagram.com/"],
    "tiktok": ["tiktok.com/@"],
}

# Search query templates per platform — name-based fallback
SEARCH_QUERIES: Dict[str, str] = {
    "linkedin": 'site:linkedin.com/company "{name}" {location}',
    "facebook": 'site:facebook.com "{name}" {location}',
    "instagram": 'site:instagram.com "{name}" {location}',
    "tiktok": 'site:tiktok.com "{name}" {location}',
}

# Search query templates when website domain is available — much more accurate
SEARCH_QUERIES_DOMAIN: Dict[str, str] = {
    "linkedin": 'site:linkedin.com/company "{domain}"',
    "facebook": 'site:facebook.com "{domain}"',
    "instagram": 'site:instagram.com "{domain}"',
    "tiktok": 'site:tiktok.com "{domain}"',
}


class SocialResearchService:
    """
    Service to find social media profiles for a business using Google Search (Serper.dev).

    Strategy:
    1. For each platform, build a targeted Google search query
    2. Call Serper.dev API to get top results
    3. Extract and validate the first matching URL
    4. Return a dict of platform -> URL (None if not found)
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.serper_api_key
        self.base_url = (base_url or settings.serper_base_url).rstrip("/")

    async def search_social_profiles(
        self,
        business_name: str,
        website: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Dict[str, Optional[str]]:
        """
        Search for all social media profiles of a business.

        Args:
            business_name: Name of the business to search for
            website: Business website (improves search accuracy)
            city: City name (improves geographic disambiguation)
            state: State code (improves geographic disambiguation)

        Returns:
            Dict mapping platform name to URL (None if not found):
            {"linkedin": "...", "facebook": "...", "instagram": None, "tiktok": None}
        """
        if not self.api_key:
            logger.warning("SERPER_API_KEY not configured — skipping social research")
            return {platform: None for platform in PLATFORM_DOMAINS}

        # Build location string for search context
        location_parts = [p for p in [city, state] if p]
        location = " ".join(location_parts)

        # Extract bare domain and brand slug from website URL
        domain: Optional[str] = None
        brand_slug: Optional[str] = None  # domain without TLD, e.g. "buffetposeidon"
        if website:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(website if website.startswith("http") else f"https://{website}")
                domain = parsed.netloc.lstrip("www.") or parsed.path.lstrip("www.").split("/")[0]
                # Brand slug: first part of domain before the TLD
                # e.g. "buffetposeidon.com" -> "buffetposeidon"
                brand_slug = domain.split(".")[0] if domain else None
            except Exception:
                domain = None
                brand_slug = None

        # Run searches for each platform
        results: Dict[str, Optional[str]] = {}
        for platform in PLATFORM_DOMAINS:
            try:
                url = await self._find_profile(
                    business_name, platform, location,
                    domain=domain, brand_slug=brand_slug
                )
                results[platform] = url
                logger.info("Found %s profile for '%s': %s", platform, business_name, url)
            except Exception as exc:
                logger.warning(
                    "Failed to search %s for '%s': %s", platform, business_name, exc
                )
                results[platform] = None

        return results

    async def _find_profile(
        self,
        business_name: str,
        platform: str,
        location: str = "",
        domain: Optional[str] = None,
        brand_slug: Optional[str] = None,
    ) -> Optional[str]:
        """
        Search Google for a specific platform profile of a business.

        Args:
            business_name: Business name
            platform: Platform key (linkedin, facebook, instagram, tiktok)
            location: Optional location string for disambiguation
            domain: Bare domain from website (e.g. "buffetposeidon.com") — preferred over name
            brand_slug: unused, kept for signature compatibility

        Returns:
            Profile URL string or None if not found
        """
        valid_domains = PLATFORM_DOMAINS[platform]

        if domain:
            # Primary: domain-based query is more precise
            query = SEARCH_QUERIES_DOMAIN[platform].format(domain=domain).strip()
        else:
            # Fallback: name + location query
            query = SEARCH_QUERIES[platform].format(
                name=business_name,
                location=location,
            ).strip()

        search_results = await self._serper_search(query, num=5)
        organic = search_results.get("organic", [])

        # If domain query returned nothing, retry with name-based query
        if not organic and domain:
            fallback_query = SEARCH_QUERIES[platform].format(
                name=business_name,
                location=location,
            ).strip()
            search_results = await self._serper_search(fallback_query, num=5)
            organic = search_results.get("organic", [])

        # Find the first result that matches expected domain pattern
        for result in organic:
            link = result.get("link", "")
            if self._is_valid_profile_url(link, valid_domains, business_name):
                return self._clean_url(link)

        return None

    async def _serper_search(self, query: str, num: int = 5) -> Dict[str, Any]:
        """
        Call Serper.dev Google Search API.

        Args:
            query: Search query string
            num: Number of results to return

        Returns:
            Raw Serper API response dict
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/search",
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                },
                json={"q": query, "num": num},
            )
            response.raise_for_status()
            return response.json()

    def _is_valid_profile_url(
        self, url: str, valid_domains: List[str], business_name: str
    ) -> bool:
        """
        Validate that a URL looks like a real profile page (not a search page, post, etc.)

        Args:
            url: URL to validate
            valid_domains: List of domain patterns that are acceptable
            business_name: Used for basic name matching

        Returns:
            True if URL looks like a valid profile
        """
        if not url:
            return False

        url_lower = url.lower()

        # Must match one of the valid domain patterns
        if not any(domain in url_lower for domain in valid_domains):
            return False

        # Reject known non-profile URL patterns
        reject_patterns = [
            "/posts/", "/photo", "/photos/", "/videos/", "/video/",
            "/events/", "/jobs/", "/search/", "?q=", "&q=",
            "linkedin.com/in/search", "linkedin.com/company/search",
            "/explore/", "/reel/", "/stories/", "/tv/",
            "/permalink/", "/media/", "/groups/", "/pages/",
        ]
        if any(pattern in url_lower for pattern in reject_patterns):
            return False

        # URL must have at least one path segment after the domain prefix
        # e.g. linkedin.com/company/sunrise-senior-living (not just linkedin.com/company/)
        for domain in valid_domains:
            idx = url_lower.find(domain)
            if idx != -1:
                slug = url[idx + len(domain):].strip("/").split("?")[0]
                if len(slug) >= 2:  # Slug must be at least 2 chars
                    return True

        return False

    def _clean_url(self, url: str) -> str:
        """Remove tracking parameters and normalize a profile URL."""
        # Remove query string (e.g. ?trk=..., ?utm_source=...)
        clean = url.split("?")[0].rstrip("/")
        return clean

    async def fetch_linkedin_snippet(self, linkedin_url: str) -> Dict[str, str]:
        """
        Fetch a LinkedIn profile's public snippet via Google Search.
        Used to get profile text (name, title, company, bio) without LinkedIn API.

        Args:
            linkedin_url: LinkedIn company or person profile URL

        Returns:
            Dict with keys: name, title, company, industry, bio, url
        """
        if not self.api_key:
            return {"url": linkedin_url}

        # Search for the exact LinkedIn URL to get its Google snippet
        query = f'site:linkedin.com "{linkedin_url.split("linkedin.com/")[-1].strip("/")}"'

        try:
            search_results = await self._serper_search(query, num=3)
            organic = search_results.get("organic", [])

            # Also check knowledge graph
            knowledge_graph = search_results.get("knowledgeGraph", {})

            profile_data: Dict[str, str] = {"url": linkedin_url}

            if organic:
                top = organic[0]
                profile_data["name"] = top.get("title", "").split(" - ")[0].strip()
                profile_data["bio"] = top.get("snippet", "")

                # Try to extract title/company from the title field
                # LinkedIn titles often look like: "John Doe - CEO at Acme Corp | LinkedIn"
                title_raw = top.get("title", "")
                if " - " in title_raw:
                    parts = title_raw.split(" - ")
                    if len(parts) >= 2:
                        profile_data["name"] = parts[0].strip()
                        role_company = parts[1].replace("| LinkedIn", "").strip()
                        if " at " in role_company:
                            role_parts = role_company.split(" at ")
                            profile_data["title"] = role_parts[0].strip()
                            profile_data["company"] = role_parts[1].strip()
                        else:
                            profile_data["title"] = role_company

            if knowledge_graph:
                profile_data["name"] = knowledge_graph.get("title", profile_data.get("name", ""))
                profile_data["industry"] = knowledge_graph.get("type", "")
                profile_data["bio"] = knowledge_graph.get("description", profile_data.get("bio", ""))

            return profile_data

        except Exception as exc:
            logger.warning("Failed to fetch LinkedIn snippet for %s: %s", linkedin_url, exc)
            return {"url": linkedin_url}
