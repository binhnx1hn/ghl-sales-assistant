# Phase 3 — GHL Hot Lead Webhook Receiver: BA Spec

**Classification**: FEATURE  
**Version**: 1.0  
**Date**: 2026-04-01  
**Author**: BA Agent  
**Status**: spec-ready → BE Dev

---

## 1. Goal

Build a GHL Webhook Receiver endpoint (`POST /webhooks/ghl/hot-lead`) that receives outbound HTTP POST events fired by GoHighLevel's Workflow automation when a contact moves to the Hot Lead pipeline stage. The endpoint must immediately acknowledge GHL with HTTP 200 (`{"received": true}`) and then — in a background task — extract the contact metadata from the webhook payload, construct a `HotLeadWorkflowRequest`, and execute the existing hot-lead enrichment logic directly via the service layer (fetch contact notes → find social profiles → save profiles to GHL contact fields → draft personalized email → save email draft as GHL note). This closes the automation loop: no manual trigger, no extension interaction, no self-HTTP call — the CRM event drives the enrichment end-to-end.

---

## 2. Constraints

- **No new database** — no persistence layer introduced; all state lives in GHL.
- **No new infrastructure** — no message queue, no Celery, no Redis; use FastAPI `BackgroundTasks` only.
- **No self-HTTP call** — background task calls service functions directly, never `httpx`-calls its own `/api/v1/leads/hot-lead-workflow` endpoint.
- **No FE changes** — this is a pure backend feature; extension is unaffected.
- **Reuse existing services** — `GHLService`, `SocialResearchService`, `AIEmailDrafterService` from `backend/app/services/` must be called as-is; no forking.
- **Separate router mount** — webhook router mounts at `/webhooks/` in `main.py`, not under `/api/v1/`; webhooks are a distinct concern from the REST API.
- **GHL ToS compliance** — endpoint must not store raw webhook payloads; log only the `contactId` and event type for audit; no PII written to disk.
- **Fast ACK** — GHL requires a response in < 5 seconds; enrichment MUST run in background, not blocking the HTTP response.
- **Optional security** — `WEBHOOK_SECRET` is optional; if unset, skip header validation (dev-friendly). Do not hard-fail on missing secret config.

---

## 3. API Contract

### 3.1 Inbound — Webhook Receiver

| Field | Value |
|---|---|
| **Method** | `POST` |
| **Path** | `/webhooks/ghl/hot-lead` |
| **Auth** | Optional `X-Webhook-Secret` header checked against `settings.webhook_secret` |
| **Content-Type** | `application/json` |
| **Caller** | GHL Workflow automation (external) |

**Request body** (GHL sends this on `OpportunityStageUpdate`):

```json
{
  "type": "OpportunityStageUpdate",
  "locationId": "abc123",
  "id": "opp_id_here",
  "contactId": "contact_id_here",
  "name": "Business Name",
  "pipelineId": "pipeline_id_here",
  "pipelineStageId": "stage_id_here",
  "status": "open",
  "contact": {
    "id": "contact_id_here",
    "name": "John Doe",
    "companyName": "Business Name",
    "website": "https://example.com",
    "city": "Denver",
    "state": "CO"
  }
}
```

**Immediate response** (always, if security check passes):

```json
HTTP 200
{"received": true}
```

**Response on secret mismatch** (only when `WEBHOOK_SECRET` is configured):

```json
HTTP 401
{"detail": "Invalid webhook secret"}
```

### 3.2 Background Job Output

After ACK, the background task produces these side effects in GHL (same as existing `/api/v1/leads/hot-lead-workflow`):

| Output | Location in GHL |
|---|---|
| LinkedIn URL | Contact custom field `linkedin_url` |
| Facebook URL | Contact custom field `facebook_url` |
| Instagram URL | Contact custom field `instagram_url` |
| TikTok URL | Contact custom field `tiktok_url` |
| Email draft + subject | GHL Note on the contact (body prefixed `📧 HOT LEAD EMAIL SUGGESTION`) |

---

## 4. Validation Rules

### 4.1 Security Header Check (evaluated first)

```
IF settings.webhook_secret is set (non-empty):
    IF request header "X-Webhook-Secret" != settings.webhook_secret:
        → return HTTP 401 {"detail": "Invalid webhook secret"}
        → do NOT enqueue background task
ELSE:
    → skip validation (no secret configured)
```

### 4.2 Event Type Filter

```
IF payload["type"] != "OpportunityStageUpdate":
    → return HTTP 200 {"received": true}
    → do NOT enqueue background task
    → log: INFO "Ignored webhook event type: {payload.type}"
```

### 4.3 Hot Lead Stage Filter

```
IF payload["pipelineStageId"] != settings.ghl_stage_id_hot:
    → return HTTP 200 {"received": true}
    → do NOT enqueue background task
    → log: INFO "Ignored stage transition: pipelineStageId={payload.pipelineStageId}"
```

### 4.4 Config Guard

```
IF settings.ghl_stage_id_hot is None or empty:
    → return HTTP 200 {"received": true}
    → do NOT enqueue background task
    → log: WARNING "GHL_STAGE_ID_HOT not configured — webhook received but ignored"
```

### 4.5 Required Fields in Payload

These fields must be present for enrichment to proceed. If any are missing, log error and skip background task (still return 200):

| Field | Path in payload | Required |
|---|---|---|
| Contact ID | `payload.contactId` | YES — abort if absent |
| Event type | `payload.type` | YES — abort if absent |
| Stage ID | `payload.pipelineStageId` | YES — abort if absent |

Optional metadata (extracted if present, ignored if absent):

| Field | Path in payload | Maps to |
|---|---|---|
| Business name | `payload.contact.companyName` or `payload.name` | `HotLeadWorkflowRequest.business_name` |
| Website | `payload.contact.website` | `HotLeadWorkflowRequest.website` |
| City | `payload.contact.city` | `HotLeadWorkflowRequest.city` |
| State | `payload.contact.state` | `HotLeadWorkflowRequest.state` |

---

## 5. Security

### 5.1 Webhook Secret Validation

```
Header name:  X-Webhook-Secret
Config key:   WEBHOOK_SECRET (settings.webhook_secret)
Comparison:   constant-time string equality (use hmac.compare_digest)
Behaviour:
  - WEBHOOK_SECRET set + header matches   → proceed
  - WEBHOOK_SECRET set + header missing   → HTTP 401
  - WEBHOOK_SECRET set + header wrong     → HTTP 401
  - WEBHOOK_SECRET not set                → proceed (dev mode)
```

Use `hmac.compare_digest(provided_secret, settings.webhook_secret)` to prevent timing attacks.

### 5.2 No Signature Verification (GHL limitation)

GHL does not support HMAC-signed payloads for webhook actions (as of 2026). The `X-Webhook-Secret` header is a shared static secret configured in the GHL Webhook action as a custom header. This is the recommended GHL webhook security pattern.

### 5.3 CORS

Webhook endpoint is NOT a browser-facing endpoint. CORS middleware already applied globally in `main.py` — no special handling needed. GHL server-to-server calls are not CORS-constrained.

---

## 6. Config Changes

### 6.1 New `.env` Variable

| Variable | Type | Default | Purpose |
|---|---|---|---|
| `WEBHOOK_SECRET` | `Optional[str]` | `None` | Shared secret validated against `X-Webhook-Secret` header; if unset, validation skipped |

### 6.2 Change to `backend/app/config.py`

Add to the `Settings` class, under `# API Security` section (after `api_secret_key`):

```python
# Phase 3 — Webhook security
webhook_secret: Optional[str] = None
```

No other config changes. `ghl_stage_id_hot` and `ghl_pipeline_id` already exist at lines 46–47.

### 6.3 `.env.example` Addition

```dotenv
# Phase 3 — Webhook Security
WEBHOOK_SECRET=               # Set to a random string to secure the GHL webhook endpoint
```

---

## 7. File Changes

### 7.1 Files to CREATE

| File | Purpose |
|---|---|
| `backend/app/api/webhooks/__init__.py` | Empty init — makes `webhooks` a package |
| `backend/app/api/webhooks/ghl.py` | Webhook router: `POST /ghl/hot-lead` handler + background task function |

### 7.2 Files to MODIFY

| File | Change |
|---|---|
| `backend/app/main.py` | Import `webhook_router` from `app.api.webhooks.ghl`; mount with `app.include_router(webhook_router, prefix="/webhooks")` |
| `backend/app/config.py` | Add `webhook_secret: Optional[str] = None` field to `Settings` class |
| `backend/backend/.env.example` | Add `WEBHOOK_SECRET=` entry |

### 7.3 Files to NOT TOUCH

| File | Reason |
|---|---|
| `backend/app/api/v1/leads.py` | Existing endpoint untouched; service logic is called directly from background task |
| `backend/app/api/v1/router.py` | v1 API router unchanged |
| `backend/app/services/*.py` | All services reused as-is |
| `backend/app/models/enrich.py` | Models reused as-is |

---

## 8. Background Task Flow

The background task function `_run_hot_lead_enrichment(contact_id, business_name, website, city, state)` executes these steps in order. It is **async** and called via `background_tasks.add_task(...)`.

```
Step 1 — Instantiate services
    ghl_service = GHLService(api_key=settings.ghl_api_key,
                             location_id=settings.ghl_location_id,
                             base_url=settings.ghl_base_url)
    social_service = SocialResearchService()
    drafter = AIEmailDrafterService()

Step 2 — Fetch full contact record (for fallback metadata)
    contact = await ghl_service.get_contact(contact_id)
    contact_data = contact.get("contact", contact)
    Resolve business_name: webhook value → contact_data["companyName"] → contact_data["firstName"] → "Unknown Business"
    Resolve website:       webhook value → contact_data["website"]
    Resolve city:          webhook value → contact_data["city"]
    Resolve state:         webhook value → contact_data["state"]

Step 3 — Fetch recent notes
    notes = await ghl_service.get_notes(contact_id)
    sorted_notes = sorted(notes, key=lambda n: n.get("dateAdded") or "", reverse=True)
    selected_notes = sorted_notes[:5]   ← default notes_limit=5
    notes_context = "\n".join(["- " + n["body"].strip() for n in selected_notes if n.get("body")])

Step 4 — Find social profiles
    search_result = await social_service.search_social_profiles_with_candidates(
        business_name=business_name, website=website, city=city, state=state
    )
    profiles = search_result["profiles"]

Step 5 — Save profiles to GHL contact (if any found)
    IF any(profiles.values()):
        await ghl_service.update_social_profiles(
            contact_id=contact_id,
            linkedin=profiles.get("linkedin"),
            facebook=profiles.get("facebook"),
            instagram=profiles.get("instagram"),
            tiktok=profiles.get("tiktok"),
        )

Step 6 — Draft personalized email
    draft_result = await drafter.draft_email(
        business_name=business_name,
        linkedin_url=profiles.get("linkedin"),
        sender_name=settings.default_sender_name or None,
        sender_company=settings.default_sender_company or None,
        pitch=settings.default_pitch or None,
        notes_context=notes_context or None,
    )
    draft_subject = draft_result.get("subject", f"Quick question about {business_name}")
    draft_body    = draft_result.get("body", "")

Step 7 — Save email draft as GHL note
    note_body = (
        "📧 HOT LEAD EMAIL SUGGESTION\n"
        "────────────────────────────────────────\n"
        f"Subject: {draft_subject}\n\n"
        f"{draft_body}\n"
        "────────────────────────────────────────\n"
        f"LinkedIn: {profiles.get('linkedin') or 'N/A'}\n"
        f"Recent notes used: {len(selected_notes)}\n"
        "(Review before sending)"
    )
    note_result = await ghl_service.add_note(contact_id=contact_id, body=note_body)

Step 8 — Log success
    logger.info(f"Hot lead enrichment complete: contact_id={contact_id}, note_id={note_id}")
```

**Sender defaults**: Use `settings.default_sender_name`, `settings.default_sender_company`, `settings.default_pitch` (already in config). Pass as `None` if empty string — the `AIEmailDrafterService` handles None gracefully.

---

## 9. Error Handling

### 9.1 HTTP Handler (before ACK)

| Condition | Response | Log |
|---|---|---|
| Secret mismatch | HTTP 401 | `WARNING "Webhook secret mismatch from {request.client.host}"` |
| Malformed JSON body | HTTP 422 (FastAPI default) | FastAPI handles automatically |
| Missing `contactId` in payload | HTTP 200 + skip task | `ERROR "Webhook missing contactId — payload: {payload}"` |
| `ghl_stage_id_hot` not configured | HTTP 200 + skip task | `WARNING "GHL_STAGE_ID_HOT not configured"` |
| Wrong event type | HTTP 200 + skip task | `INFO "Ignored event type: {type}"` |
| Wrong stage | HTTP 200 + skip task | `INFO "Ignored stage: {stageId}"` |

### 9.2 Background Task (after ACK — errors must NOT crash the worker)

All background task code must be wrapped in a top-level `try/except Exception`:

| Error source | Action |
|---|---|
| `GHLAPIError` on `get_contact` | `logger.error(...)` + return (abort enrichment) |
| `GHLAPIError` on `get_notes` | `logger.warning(...)` + continue with empty notes_context |
| `Exception` from `SocialResearchService` | `logger.error(...)` + continue (skip profiles step) |
| `Exception` from `AIEmailDrafterService` | `logger.error(...)` + continue (skip email draft step) |
| `GHLAPIError` on `add_note` | `logger.error(...)` + continue (enrichment still partially succeeded) |
| Any unhandled `Exception` | `logger.exception(f"Hot lead enrichment failed for contact_id={contact_id}")` |

**Key principle**: background task MUST NOT raise exceptions that would surface to the ASGI server or produce a 500 error after the 200 ACK has already been sent. Log and swallow.

### 9.3 GHL Timeout Constraint

GHL webhooks time out if no response in **5 seconds**. The endpoint handler must complete in < 1 second:
- No service calls in the handler itself
- No `await` on enrichment logic
- Only: security check + payload parse + stage filter + `background_tasks.add_task(...)` + return JSON

---

## 10. GHL Client Setup Guide

### Setting Up the GHL Webhook Automation

This guide explains how to configure GoHighLevel to automatically trigger the hot lead enrichment when a contact is moved to the Hot Lead pipeline stage.

---

#### Prerequisites

- GHL sub-account with Workflow access
- Backend deployed and accessible at a public URL (e.g., `https://your-backend.com`)
- `GHL_STAGE_ID_HOT` configured in your backend `.env`

---

#### Step 1 — Find Your Hot Lead Stage ID

1. In GHL, go to **CRM → Pipelines**
2. Find your pipeline and identify the **Hot Lead** stage
3. Click the stage name → the URL will contain the stage ID (e.g., `...stageId=abc123def`)
4. Copy this ID — you'll need it for your backend `.env` as `GHL_STAGE_ID_HOT`

---

#### Step 2 — Create a New Workflow

1. Go to **Automation → Workflows**
2. Click **+ New Workflow** → **Start from Scratch**
3. Name it: `Hot Lead Webhook Trigger`

---

#### Step 3 — Set the Trigger

1. Click **Add Trigger**
2. Choose: **Opportunity Stage Changed**
3. Configure filters:
   - **Pipeline**: Select your sales pipeline
   - **Stage**: Select **Hot Lead** (your target stage)
4. Click **Save Trigger**

---

#### Step 4 — Add the Webhook Action

1. Click **+ Add Action** (the `+` button after the trigger)
2. Search for and select: **Webhook**
3. Configure the webhook:
   - **Method**: `POST`
   - **URL**: `https://YOUR_BACKEND_DOMAIN/webhooks/ghl/hot-lead`
   - **Headers**:
     - Key: `Content-Type` → Value: `application/json`
     - Key: `X-Webhook-Secret` → Value: *(your `WEBHOOK_SECRET` value from `.env`)*
   - **Body**: Leave as **Default** (GHL sends its standard payload automatically)
4. Click **Save Action**

> **Note**: If `WEBHOOK_SECRET` is not set in your backend `.env`, you can omit the `X-Webhook-Secret` header.

---

#### Step 5 — Publish the Workflow

1. Toggle the workflow to **Published** (top-right switch)
2. Click **Save**

---

#### Step 6 — Test the Automation

1. In GHL CRM, find any test contact
2. Create an Opportunity for them (or find an existing one)
3. Move the opportunity stage to **Hot Lead**
4. Wait 10–30 seconds
5. Check the contact's **Notes** — you should see a note beginning with `📧 HOT LEAD EMAIL SUGGESTION`
6. Check the contact's **Custom Fields** — LinkedIn, Facebook, Instagram, TikTok URLs should be populated (if found)

---

#### What Gets Created Automatically

When a contact moves to Hot Lead, the backend will:

| Action | Where to Find in GHL |
|---|---|
| Find social media profiles (LinkedIn, Facebook, Instagram, TikTok) | Contact → **Custom Fields** |
| Save profile URLs to contact | Contact → **Custom Fields** |
| Draft a personalized outreach email using GPT-4o-mini | Contact → **Notes** |
| Save the email draft as a note | Contact → **Notes** → `📧 HOT LEAD EMAIL SUGGESTION` |

---

#### Sample Webhook Payload Shape (for reference)

GHL sends this structure when an opportunity stage changes:

```json
{
  "type": "OpportunityStageUpdate",
  "locationId": "your_location_id",
  "id": "opportunity_id",
  "contactId": "contact_id",
  "name": "Business Name",
  "pipelineId": "pipeline_id",
  "pipelineStageId": "hot_lead_stage_id",
  "status": "open",
  "contact": {
    "id": "contact_id",
    "name": "John Doe",
    "companyName": "Business Name",
    "website": "https://example.com",
    "city": "Denver",
    "state": "CO"
  }
}
```

---

#### Troubleshooting

| Symptom | Check |
|---|---|
| No note created after moving to Hot Lead | Check backend logs for `WARNING "GHL_STAGE_ID_HOT not configured"` |
| HTTP 401 in GHL workflow history | `X-Webhook-Secret` header value doesn't match `WEBHOOK_SECRET` in `.env` |
| Note created but no social profiles | Business name or website may be missing from contact; add them manually and re-trigger |
| Workflow not firing at all | Ensure workflow is **Published** and trigger filter matches correct pipeline + stage |

---

## 11. Failure Modes

| Failure | Trigger Condition | Behaviour | Recovery |
|---|---|---|---|
| `GHL_STAGE_ID_HOT` not configured | `settings.ghl_stage_id_hot` is `None` | 200 ACK, no enrichment, log WARNING | Set `GHL_STAGE_ID_HOT` in `.env` and restart |
| Wrong webhook secret | `X-Webhook-Secret` != `settings.webhook_secret` | 401, no enrichment | Match secret in GHL Webhook action to `.env` value |
| `contactId` missing from payload | GHL sends non-standard payload | 200 ACK, no enrichment, log ERROR | Inspect GHL workflow payload; ensure trigger is `OpportunityStageUpdate` |
| Enrichment crashes (GHL API down) | `GHLAPIError` in background task | Error logged, partial results possible | Retry by manually moving contact back to Hot Lead and then to Hot Lead again |
| OpenAI API error | `Exception` from `AIEmailDrafterService` | Error logged, no email note created, profiles still saved | Retry manually via `/api/v1/leads/hot-lead-workflow` |
| Serper API error | `Exception` from `SocialResearchService` | Error logged, no profiles saved, email draft still attempted | Retry manually via `/api/v1/leads/hot-lead-workflow` |
| GHL note save fails | `GHLAPIError` on `add_note` | Error logged, profiles may still be saved | Retry manually via `/api/v1/leads/hot-lead-workflow` |
| GHL webhook fires twice (duplicate) | GHL retries on 200 (GHL does NOT retry on 200) | N/A — GHL only retries on non-200; 200 = success, no retry | Not a concern |

---

## 12. Open Questions

| # | Question | Impact | Suggested Default |
|---|---|---|---|
| OQ-1 | Should `notes_limit` be configurable via a new `WEBHOOK_NOTES_LIMIT` env var, or always use `5`? | Low — `5` is already the default in `HotLeadWorkflowRequest` | Default `5`; add `WEBHOOK_NOTES_LIMIT: int = 5` to config only if client requests control |
| OQ-2 | GHL may also send `ContactTagUpdate` and other event types to the same URL if the client configures multiple triggers. The spec handles this via `type` filter. Confirm: should any other `type` values be **actively rejected** (401) vs silently ignored (200)? | Low | Silently ignore all unknown types (200) — never reject; GHL re-attempts on non-200 |
| OQ-3 | `locationId` in payload — should the endpoint validate it matches `settings.ghl_location_id` to prevent cross-tenant spoofing? | Medium (security) | Validate if `WEBHOOK_SECRET` is NOT set; skip if secret is set (secret provides sufficient auth) |
| OQ-4 | Should a duplicate-prevention mechanism (e.g., cache `opportunity_id` for 60s) be added to avoid re-processing if GHL fires the same event twice? | Low | GHL does not retry on HTTP 200; skip for Phase 3, revisit if observed in production |
| OQ-5 | The background task uses `settings.default_sender_name/company/pitch` as sender defaults. Should the client be able to override these per-pipeline (e.g., different pitch for Hot Lead vs Warm Lead)? | Low | Use global defaults for Phase 3; per-pipeline overrides deferred to Phase 4 |

---

## 13. Acceptance Criteria

| ID | Criterion | Verified By |
|---|---|---|
| AC-1 | `POST /webhooks/ghl/hot-lead` returns `{"received": true}` with HTTP 200 within 1 second | Integration test / manual timing |
| AC-2 | Enrichment runs in background after 200 ACK; GHL webhook history shows 200 success | GHL workflow execution log |
| AC-3 | Non-`OpportunityStageUpdate` events return 200 silently without triggering enrichment | Unit test with `type: "ContactTagUpdate"` payload |
| AC-4 | Stage filter: payload with wrong `pipelineStageId` returns 200 silently without enrichment | Unit test |
| AC-5 | When `WEBHOOK_SECRET` is set and header is wrong, returns HTTP 401 | Unit test |
| AC-6 | When `WEBHOOK_SECRET` is not set, any header value is accepted | Unit test |
| AC-7 | Contact notes fetched (up to 5), social profiles searched and saved to GHL contact custom fields | End-to-end: move contact to Hot Lead, check GHL custom fields |
| AC-8 | Email draft saved as GHL note with `📧 HOT LEAD EMAIL SUGGESTION` prefix | End-to-end: check contact Notes in GHL |
| AC-9 | `GHL_STAGE_ID_HOT` not configured → 200 + WARNING log, no crash | Unit test + log assertion |
| AC-10 | Background task exception does not produce a 500 response or crash the worker | Unit test: mock `ghl_service.get_contact` to raise; verify 200 still returned |

---

*End of Phase 3 Spec — spec-ready → BE Dev*
