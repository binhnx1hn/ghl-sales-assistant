"""
Phase 2B: Lead Classifier Service.

Uses OpenAI GPT-4o-mini to classify a lead into hot/warm/cold tiers based on
business signals. After classification:
  1. Applies a GHL tag (tier:hot / tier:warm / tier:cold)
  2. Optionally triggers a configured GHL workflow for that tier
"""

import json
import logging
from typing import Optional, Dict, Any

from openai import AsyncOpenAI

from app.config import settings
from app.services.ghl_service import GHLService
from app.utils.exceptions import GHLAPIError

logger = logging.getLogger(__name__)

# ─── Prompts ──────────────────────────────────────────────────────────────────

CLASSIFIER_SYSTEM_PROMPT = """You are a lead scoring expert for a B2B sales team.
Given business signals, you score leads on a 0-100 scale and classify them as hot/warm/cold.

Scoring heuristics:
- LinkedIn URL present: +20 (contributes to hot); absence loses signal
- Website with HTTPS: +15 (hot) / +8 (warm, HTTP only)
- Lead source "google_maps" detail: +15; "google_search": +10; "directory": +5
- Industry exact match to target: +20; partial match: +10
- Employee count 50-200: +10; 10-50: +5
- Rating >= 4.0: +10; >= 3.0: +5
- Location in primary target market: +10; secondary market: +5

Thresholds:
- Hot: score >= 70
- Warm: 40 <= score < 70
- Cold: score < 40

Always respond with ONLY valid JSON. No markdown, no explanation.
JSON structure: {"tier": "hot"|"warm"|"cold", "score": <int 0-100>, "reasons": ["reason1", "reason2", ...]}"""

CLASSIFIER_USER_TEMPLATE = """Score this lead:

Business Name: {business_name}
Website: {website}
Industry: {industry}
City: {city}
State: {state}
Lead Source: {lead_source}
LinkedIn URL: {linkedin_url}
Employee Count Estimate: {employee_count}
Rating: {rating}

Return ONLY JSON: {{"tier": "hot"|"warm"|"cold", "score": <int>, "reasons": ["..."]}}"""


class LeadClassifierService:
    """
    Service that classifies leads into hot/warm/cold tiers using GPT-4o-mini,
    then applies GHL tags and optionally triggers GHL workflows.

    Workflow:
    1. Build scoring prompt with business signals
    2. Call OpenAI GPT-4o-mini → get tier, score, reasons
    3. Apply GHL tag: tier:hot / tier:warm / tier:cold
    4. If trigger_workflow=True and workflow ID configured → trigger GHL workflow
       (failures here are gracefully swallowed — do NOT raise 500)
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

    def _get_workflow_id(self, tier: str) -> Optional[str]:
        """Return the configured GHL workflow ID for a given tier, or None."""
        mapping = {
            "hot": settings.ghl_workflow_id_hot,
            "warm": settings.ghl_workflow_id_warm,
            "cold": settings.ghl_workflow_id_cold,
        }
        return mapping.get(tier)

    async def classify(
        self,
        contact_id: str,
        business_name: str,
        ghl_service: GHLService,
        website: Optional[str] = None,
        industry: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        lead_source: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        employee_count_estimate: Optional[str] = None,
        rating: Optional[str] = None,
        trigger_workflow: bool = False,
    ) -> Dict[str, Any]:
        """
        Classify a lead and apply GHL tags + optional workflow.

        Args:
            contact_id: GHL contact ID
            business_name: Target business name
            ghl_service: Authenticated GHL service instance
            website: Business website URL
            industry: Industry vertical
            city: City name
            state: State code
            lead_source: Source of the lead (google_maps, google_search, etc.)
            linkedin_url: LinkedIn URL if found
            employee_count_estimate: e.g. '50-200'
            rating: Business rating as string (e.g. '4.5')
            trigger_workflow: If True, attempt to trigger configured GHL workflow

        Returns:
            Dict with tier, score, reasons, workflow_triggered, workflow_id, tag_applied
        """
        # Step 1: Build prompt
        prompt = CLASSIFIER_USER_TEMPLATE.format(
            business_name=business_name,
            website=website or "Not provided",
            industry=industry or "Not provided",
            city=city or "Not provided",
            state=state or "Not provided",
            lead_source=lead_source or "Not provided",
            linkedin_url=linkedin_url or "Not found",
            employee_count=employee_count_estimate or "Unknown",
            rating=rating or "Unknown",
        )

        # Step 2: Call OpenAI
        classification = await self._call_openai(prompt)
        tier = classification["tier"]
        score = classification["score"]
        reasons = classification["reasons"]

        tag = f"tier:{tier}"

        # Step 3: Apply GHL tag (non-fatal if it fails)
        try:
            await ghl_service.add_tag(contact_id, tag)
            logger.info("Applied tag '%s' to contact %s", tag, contact_id)
        except (GHLAPIError, Exception) as exc:
            logger.warning(
                "Could not apply tag '%s' to contact %s: %s", tag, contact_id, exc
            )

        # Step 4: Optionally trigger GHL workflow (graceful fallback)
        workflow_triggered = False
        workflow_id: Optional[str] = None

        if trigger_workflow:
            workflow_id = self._get_workflow_id(tier)
            if workflow_id:
                try:
                    await ghl_service.trigger_workflow(contact_id, workflow_id)
                    workflow_triggered = True
                    logger.info(
                        "Triggered workflow %s for contact %s (tier: %s)",
                        workflow_id,
                        contact_id,
                        tier,
                    )
                except (GHLAPIError, Exception) as exc:
                    logger.warning(
                        "Could not trigger workflow %s for contact %s: %s",
                        workflow_id,
                        contact_id,
                        exc,
                    )
                    workflow_id = None  # Clear since it wasn't actually triggered
            else:
                logger.info(
                    "trigger_workflow=True but no workflow configured for tier '%s'", tier
                )

        # Step 5: Upsert GHL Opportunity (graceful fallback — never raises 500)
        TIER_TO_STAGE = {
            "hot": settings.ghl_stage_id_hot,
            "warm": settings.ghl_stage_id_warm,
            "cold": settings.ghl_stage_id_cold,
        }
        stage_id = TIER_TO_STAGE.get(tier)
        opportunity_action: Optional[str] = None
        opportunity_id: Optional[str] = None

        if settings.ghl_pipeline_id and stage_id:
            try:
                search_result = await ghl_service.search_opportunities(
                    contact_id, settings.ghl_pipeline_id
                )
                opportunities = search_result.get("opportunities", [])

                if opportunities:
                    opp_id = opportunities[0]["id"]
                    await ghl_service.update_opportunity_stage(opp_id, stage_id)
                    opportunity_action = "updated"
                    opportunity_id = opp_id
                    logger.info(
                        "Updated opportunity %s to stage %s for contact %s (tier: %s)",
                        opp_id,
                        stage_id,
                        contact_id,
                        tier,
                    )
                else:
                    result = await ghl_service.create_opportunity(
                        contact_id=contact_id,
                        pipeline_id=settings.ghl_pipeline_id,
                        stage_id=stage_id,
                        name=business_name,
                    )
                    opportunity_action = "created"
                    # GHL returns opportunity under "opportunity" key
                    opp = result.get("opportunity", result)
                    opportunity_id = opp.get("id")
                    logger.info(
                        "Created opportunity %s for contact %s (tier: %s)",
                        opportunity_id,
                        contact_id,
                        tier,
                    )
            except Exception as exc:
                logger.warning(
                    "Could not upsert opportunity for contact %s: %s", contact_id, exc
                )
                opportunity_action = "failed"
        else:
            opportunity_action = "skipped"
            logger.debug(
                "Opportunity upsert skipped for contact %s — pipeline not configured",
                contact_id,
            )

        return {
            "tier": tier,
            "score": score,
            "reasons": reasons,
            "workflow_triggered": workflow_triggered,
            "workflow_id": workflow_id,
            "tag_applied": tag,
            "opportunity_action": opportunity_action,
            "opportunity_id": opportunity_id,
        }

    async def _call_openai(self, user_prompt: str) -> Dict[str, Any]:
        """
        Call OpenAI with the classifier prompt and parse JSON response.

        Returns:
            Dict with 'tier', 'score', 'reasons'

        Raises:
            ValueError: If response cannot be parsed as valid JSON
        """
        client = self._get_client()

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,  # Low temperature for consistent scoring
                max_tokens=300,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)

            # Validate required fields
            tier = parsed.get("tier", "cold")
            if tier not in ("hot", "warm", "cold"):
                logger.warning("Unexpected tier '%s', defaulting to cold", tier)
                tier = "cold"

            score = int(parsed.get("score", 0))
            score = max(0, min(100, score))  # Clamp to 0-100

            reasons = parsed.get("reasons", [])
            if not isinstance(reasons, list):
                reasons = [str(reasons)]

            return {"tier": tier, "score": score, "reasons": reasons}

        except json.JSONDecodeError as exc:
            logger.error("Failed to parse OpenAI classification JSON: %s", exc)
            raise ValueError(f"AI returned invalid JSON: {exc}") from exc

        except Exception as exc:
            logger.error("OpenAI classification call failed: %s", exc)
            raise
