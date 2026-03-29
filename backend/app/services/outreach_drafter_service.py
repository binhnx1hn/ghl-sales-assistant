"""
Phase 2B: Outreach Drafter Service.

Uses OpenAI GPT-4o-mini to draft platform-specific outreach messages with
per-platform character limits enforced in the prompt.

Supported platforms and message types:
  - linkedin/inmail:              2000 chars, professional tone
  - linkedin/connection_request:   300 chars, personal, no hard pitch
  - facebook/page_dm:             1000 chars, conversational
  - instagram/dm:                 1000 chars, casual, emoji OK
  - tiktok/dm:                     500 chars, very brief
"""

import json
import logging
import time
from typing import Optional, Dict, Any, Tuple

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# ─── Platform Config ──────────────────────────────────────────────────────────

# (platform, message_type) → (char_limit, tone_instructions)
PLATFORM_CONFIG: Dict[Tuple[str, str], Dict[str, Any]] = {
    ("linkedin", "inmail"): {
        "char_limit": 2000,
        "tone": "professional, warm, consultative",
        "instructions": (
            "Write a professional LinkedIn InMail. "
            "Reference something specific from their business/industry. "
            "Keep it under 2000 characters. "
            "End with a low-friction question as CTA."
        ),
    },
    ("linkedin", "connection_request"): {
        "char_limit": 300,
        "tone": "personal, genuine, no hard pitch",
        "instructions": (
            "Write a LinkedIn connection request note. "
            "Be personal and genuine — no hard sales pitch. "
            "Mention a shared interest or genuine reason to connect. "
            "STRICTLY under 300 characters."
        ),
    },
    ("facebook", "page_dm"): {
        "char_limit": 1000,
        "tone": "conversational, friendly, approachable",
        "instructions": (
            "Write a Facebook Page DM. "
            "Be conversational and friendly. "
            "Keep under 1000 characters. "
            "Ask a simple question to start a dialogue."
        ),
    },
    ("instagram", "dm"): {
        "char_limit": 1000,
        "tone": "casual, authentic, emoji OK",
        "instructions": (
            "Write an Instagram DM. "
            "Be casual and authentic. You may use 1-2 relevant emojis. "
            "Keep under 1000 characters. "
            "Start a conversation, don't make it feel like an ad."
        ),
    },
    ("tiktok", "dm"): {
        "char_limit": 500,
        "tone": "brief, direct, energetic",
        "instructions": (
            "Write a TikTok DM. "
            "Be very brief and direct. "
            "STRICTLY under 500 characters. "
            "One sentence to introduce, one clear ask."
        ),
    },
}

DRAFTER_SYSTEM_PROMPT = """You are an expert social media outreach copywriter.
You write short, human-sounding messages that start genuine conversations.
You never sound like a template. You always respect platform character limits.
Always respond with ONLY valid JSON. No markdown, no explanation."""

DRAFTER_USER_TEMPLATE = """Write a {platform} {message_type} outreach message for this lead:

RECIPIENT:
- Business Name: {business_name}
- Industry: {industry}
- Profile URL: {profile_url}
- Profile Context: {profile_context}

SENDER:
- Name: {sender_name}
- Company: {sender_company}

VALUE PROPOSITION:
{pitch}

PLATFORM INSTRUCTIONS:
{instructions}
Tone: {tone}
Character Limit: {char_limit} characters (STRICTLY enforce)

Return ONLY this JSON: {{"message": "..."}}"""


class OutreachDrafterService:
    """
    Service that drafts platform-specific outreach messages using GPT-4o-mini.

    Character limits are enforced both in the prompt and validated post-generation.
    If LinkedIn URL is provided, optionally enriches with profile snippet via
    SocialResearchService (same pattern as AIEmailDrafterService).
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = openai_api_key or settings.openai_api_key
        self.model = model or settings.openai_model
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

    def get_platform_config(
        self, platform: str, message_type: str
    ) -> Dict[str, Any]:
        """Return config for a platform/message_type combo.

        Raises:
            ValueError: If the combo is not supported
        """
        key = (platform, message_type)
        config = PLATFORM_CONFIG.get(key)
        if config is None:
            supported = [f"{p}/{m}" for p, m in PLATFORM_CONFIG]
            raise ValueError(
                f"Unsupported platform/message_type combo: {platform}/{message_type}. "
                f"Supported: {', '.join(supported)}"
            )
        return config

    async def draft_message(
        self,
        contact_id: str,
        business_name: str,
        platform: str,
        message_type: str,
        profile_url: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_company: Optional[str] = None,
        pitch: Optional[str] = None,
        tone: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Draft a platform-specific outreach message.

        Args:
            contact_id: GHL contact ID (for context, not used in API call)
            business_name: Target business name
            platform: linkedin | facebook | instagram | tiktok
            message_type: inmail | connection_request | page_dm | dm
            profile_url: Target profile URL (optional; used for personalization)
            sender_name: Sender name (falls back to settings.default_sender_name)
            sender_company: Sender company (falls back to settings.default_sender_company)
            pitch: Value proposition (falls back to settings.default_pitch)
            tone: Desired tone override
            industry: Industry vertical for personalization

        Returns:
            Dict with drafted_message, char_count, char_limit, profile_data_used
        """
        # Validate platform/message_type combo
        config = self.get_platform_config(platform, message_type)
        char_limit = config["char_limit"]

        # Resolve sender defaults
        resolved_sender_name = sender_name or settings.default_sender_name or "Your Name"
        resolved_sender_company = (
            sender_company or settings.default_sender_company or "Your Company"
        )
        resolved_pitch = (
            pitch or settings.default_pitch or f"We help businesses like {business_name}"
        )

        # Optionally fetch LinkedIn profile snippet for personalization.
        # Disabled: the extra Serper round-trip (~1-2s) adds latency that
        # outweighs the marginal personalization gain when business_name +
        # industry are already provided. Re-enable if deeper personalization
        # is needed in the future.
        profile_data: Dict[str, str] = {}
        profile_context = "No profile data available"

        # Build prompt
        prompt = DRAFTER_USER_TEMPLATE.format(
            platform=platform,
            message_type=message_type,
            business_name=business_name,
            industry=industry or "Not specified",
            profile_url=profile_url or "Not provided",
            profile_context=profile_context,
            sender_name=resolved_sender_name,
            sender_company=resolved_sender_company,
            pitch=resolved_pitch,
            instructions=config["instructions"],
            tone=tone or config["tone"],
            char_limit=char_limit,
        )

        # Call OpenAI
        drafted_message = await self._call_openai(prompt, char_limit)

        return {
            "drafted_message": drafted_message,
            "char_count": len(drafted_message),
            "char_limit": char_limit,
            "profile_data_used": profile_data if profile_data else None,
        }

    async def _call_openai(self, user_prompt: str, char_limit: int) -> str:
        """
        Call OpenAI and return the drafted message string.

        Enforces the char_limit by truncating if the model exceeds it
        (safety net — prompt instructs compliance).
        """
        client = self._get_client()

        try:
            _t_openai = time.monotonic()
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": DRAFTER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=600,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            message = parsed.get("message", "")
            logger.info(
                "[TIMING] OpenAI chat.completions done in %.2fs (model=%s tokens=%s)",
                time.monotonic() - _t_openai,
                self.model,
                response.usage.total_tokens if response.usage else "?",
            )

            # Safety net: truncate if over limit
            if len(message) > char_limit:
                logger.warning(
                    "Drafted message exceeded char_limit (%d > %d), truncating",
                    len(message),
                    char_limit,
                )
                message = message[:char_limit]

            return message

        except json.JSONDecodeError as exc:
            logger.error("Failed to parse OpenAI outreach draft JSON: %s", exc)
            raise ValueError(f"AI returned invalid JSON: {exc}") from exc

        except Exception as exc:
            logger.error("OpenAI outreach draft call failed: %s", exc)
            raise
