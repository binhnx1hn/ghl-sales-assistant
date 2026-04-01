"""
Phase 2A: AI Email Drafter Service.

Uses OpenAI GPT-4o-mini to draft personalized cold outreach emails
based on LinkedIn profile data fetched via Serper.dev Google Search.
"""

import json
import logging
from typing import Optional, Dict, Any

from openai import AsyncOpenAI

from app.config import settings
from app.services.social_research_service import SocialResearchService

logger = logging.getLogger(__name__)

# System prompt for email drafting
SYSTEM_PROMPT = """You are an expert sales copywriter who writes short, personalized cold outreach emails.
Your emails are:
- Conversational and human-sounding (never robotic or template-like)
- Under 150 words in the body
- Specific to the recipient's business/profile
- Have a clear, low-friction call to action
- Never use buzzwords like "synergy", "leverage", "game-changer"

Always respond with valid JSON only. No markdown, no explanation."""

# User prompt template
USER_PROMPT_TEMPLATE = """Write a personalized cold outreach email based on this information:

RECIPIENT INFO:
- Business Name: {business_name}
- Contact Name: {name}
- Title: {title}
- Company: {company}
- Industry: {industry}
- Bio/Description: {bio}
- LinkedIn: {linkedin_url}

SENDER INFO:
- Name: {sender_name}
- Company: {sender_company}

VALUE PROPOSITION:
{pitch}

RECENT NOTES CONTEXT:
{notes_context}

INSTRUCTIONS:
- Reference something specific from their profile or industry
- Keep it personal and brief (under 150 words in body)
- End with a simple question as CTA (e.g. "Would a quick 15-min call make sense?")
- If contact name is unknown, use "Hi there" or address by company name

Return ONLY this JSON structure (no markdown):
{{"subject": "...", "body": "..."}}"""


class AIEmailDrafterService:
    """
    Service that drafts personalized cold outreach emails using OpenAI GPT-4o-mini.

    Workflow:
    1. Accept LinkedIn URL + business info
    2. Use SocialResearchService to fetch LinkedIn profile snippet from Google
    3. Build a structured prompt with profile data + sender info
    4. Call OpenAI GPT-4o-mini to generate subject + body
    5. Return the draft email
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        model: Optional[str] = None,
        social_service: Optional[SocialResearchService] = None,
    ):
        self.api_key = openai_api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.social_service = social_service or SocialResearchService()
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        """Lazily initialize the OpenAI async client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "OPENAI_API_KEY is not configured. "
                    "Please set it in your .env file."
                )
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def draft_email(
        self,
        business_name: str,
        linkedin_url: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_company: Optional[str] = None,
        pitch: Optional[str] = None,
        notes_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Draft a personalized cold outreach email.

        Args:
            business_name: Target business name
            linkedin_url: LinkedIn profile/company URL (optional — will search if not provided)
            sender_name: Sender's name (falls back to settings.default_sender_name)
            sender_company: Sender's company (falls back to settings.default_sender_company)
            pitch: Value proposition (falls back to settings.default_pitch)
            notes_context: Optional notes from CRM to personalize better

        Returns:
            Dict with keys:
              - subject: Email subject line
              - body: Email body text
              - profile_data: LinkedIn profile data used (for transparency)
              - linkedin_url: Resolved LinkedIn URL
        """
        # Resolve sender defaults from settings
        resolved_sender_name = sender_name or settings.default_sender_name or "Your Name"
        resolved_sender_company = sender_company or settings.default_sender_company or "Your Company"
        resolved_pitch = pitch or settings.default_pitch or f"We help businesses like {business_name}"
        resolved_notes_context = (
            notes_context.strip()
            if notes_context and notes_context.strip()
            else "No recent notes available."
        )

        # Step 1: Fetch LinkedIn profile data if URL provided
        profile_data: Dict[str, str] = {"business_name": business_name}
        resolved_linkedin_url = linkedin_url

        if linkedin_url:
            try:
                fetched = await self.social_service.fetch_linkedin_snippet(linkedin_url)
                profile_data.update(fetched)
                logger.info("Fetched LinkedIn profile for %s: %s", business_name, profile_data)
            except Exception as exc:
                logger.warning("Could not fetch LinkedIn profile: %s", exc)

        # If no LinkedIn URL was provided, try to search for one
        if not linkedin_url:
            try:
                profiles = await self.social_service.search_social_profiles(business_name)
                resolved_linkedin_url = profiles.get("linkedin")
                if resolved_linkedin_url:
                    fetched = await self.social_service.fetch_linkedin_snippet(resolved_linkedin_url)
                    profile_data.update(fetched)
            except Exception as exc:
                logger.warning("Could not auto-find LinkedIn profile: %s", exc)

        # Step 2: Build the prompt with all available profile data
        prompt = USER_PROMPT_TEMPLATE.format(
            business_name=business_name,
            name=profile_data.get("name", ""),
            title=profile_data.get("title", ""),
            company=profile_data.get("company", business_name),
            industry=profile_data.get("industry", ""),
            bio=profile_data.get("bio", ""),
            linkedin_url=resolved_linkedin_url or "Not found",
            sender_name=resolved_sender_name,
            sender_company=resolved_sender_company,
            pitch=resolved_pitch,
            notes_context=resolved_notes_context,
        )

        # Step 3: Call OpenAI GPT-4o-mini
        draft = await self._call_openai(prompt)

        return {
            "subject": draft.get("subject", f"Quick question about {business_name}"),
            "body": draft.get("body", ""),
            "profile_data": profile_data,
            "linkedin_url": resolved_linkedin_url,
        }

    async def _call_openai(self, user_prompt: str) -> Dict[str, str]:
        """
        Call OpenAI API with the given prompt and parse the JSON response.

        Args:
            user_prompt: The user-level prompt with all profile data

        Returns:
            Parsed dict with 'subject' and 'body' keys
        """
        client = self._get_client()

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,  # Some creativity but still focused
                max_tokens=400,   # Enough for subject + body under 150 words
                response_format={"type": "json_object"},  # Force JSON output
            )

            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)

            if "subject" not in parsed or "body" not in parsed:
                logger.warning("OpenAI response missing subject/body: %s", content)
                return {
                    "subject": "Following up",
                    "body": content,  # Fallback: use raw content as body
                }

            return parsed

        except json.JSONDecodeError as exc:
            logger.error("Failed to parse OpenAI JSON response: %s", exc)
            raise ValueError(f"AI returned invalid JSON: {exc}") from exc

        except Exception as exc:
            logger.error("OpenAI API call failed: %s", exc)
            raise
