# Phase 2B Spec — Outreach Queue + Lead Classifier + Warm/Hot Sequence Agent

**Date**: 2026-03-29  
**Author**: BA  
**Status**: 📋 Spec Ready → signal `spec-ready` → pm  
**Depends on**: Phase 2A complete (enrich, save-profiles, draft-email, checkbox-list UI)

---

## 1. Feature List — Prioritized

### P1 — Must Have (MVP for client value)

| ID | Feature | Feasibility | Risk |
|----|---------|-------------|------|
| F-01 | Lead Classifier: score Cold/Warm/Hot from contact data | ✅ High — GPT-4o-mini + existing GHL contact fields | 🟡 Medium — scoring quality depends on data richness |
| F-02 | `POST /leads/classify` endpoint | ✅ High — standard FastAPI async pattern | 🟢 Low |
| F-03 | GHL Workflow trigger on classify: assign workflow by tier via GHL API `POST /contacts/{id}/workflow` | 🟡 Medium — GHL API v2 supports workflow assignment | 🔴 High — requires new GHL scope `workflows.write`; workflow IDs must be pre-configured by client |
| F-04 | `POST /leads/draft-outreach` — draft per-platform outreach message (LinkedIn InMail, Facebook DM, Instagram DM, connection request) | ✅ High — extends existing `ai_email_drafter_service.py` pattern | 🟡 Medium — tone/character limits vary per platform |
| F-05 | `POST /leads/outreach-queue` — create queue items in memory/GHL Notes | ✅ High — GHL Notes already integrated | 🟢 Low |
| F-06 | `GET /leads/outreach-queue/{contact_id}` — fetch pending queue items | ✅ High | 🟢 Low |
| F-07 | Extension outreach queue panel — shows drafted messages per platform with "Open & Copy" button | ✅ High — extends existing review-popup pattern | 🟡 Medium — UI state management across platforms |

### P2 — Should Have (full workflow value)

| ID | Feature | Feasibility | Risk |
|----|---------|-------------|------|
| F-08 | Queue item status update: `PATCH /leads/outreach-queue/{item_id}` — mark sent/skipped | ✅ High | 🟢 Low |
| F-09 | Classifier auto-trigger on lead capture (option in `POST /leads/capture`) | 🟡 Medium — adds latency to capture flow | 🟡 Medium — must be opt-in flag |
| F-10 | LinkedIn connection request message draft (separate from InMail — 300 char limit) | ✅ High | 🟢 Low — character limit is fixed |
| F-11 | Multi-step warm sequence content drafting — draft 3 email touchpoints for Warm tier | ✅ High | 🟡 Medium — GPT context window, tone consistency |
| F-12 | Extension "Classify" button on review-popup — one-click classify after capture | ✅ High | 🟢 Low |

### P3 — Nice to Have (future)

| ID | Feature | Feasibility | Risk |
|----|---------|-------------|------|
| F-13 | Persistent outreach queue in dedicated DB (SQLite/Postgres) vs GHL Notes | 🟡 Medium — requires new infra | 🟡 Medium — adds complexity |
| F-14 | Batch classify: classify all unclassified contacts in GHL | 🟡 Medium — GHL rate limits | 🟡 Medium |
| F-15 | Scheduler: auto-draft outreach messages when new contact enters GHL (webhook) | 🟡 Medium — requires GHL webhook setup | 🔴 High — scope creep, new infra |
| F-16 | TikTok DM message draft | 🔴 Low — TikTok DM is app-only, no web paste flow | 🔴 High — UX mismatch |

---

## 2. API Contracts

### 2.1 `POST /api/v1/leads/classify`

**Goal**: Classify a GHL contact as Cold/Warm/Hot using AI scoring on available data signals, then optionally trigger the matching GHL Workflow.

**Constraints**:
- Must read existing GHL contact custom fields (website, social profiles, industry, city/state) — no new search API calls required
- GPT-4o-mini prompt must produce a deterministic JSON output: `{tier, score, reasons[]}`
- GHL Workflow trigger is optional; skipped gracefully if `workflow_ids` not configured
- Response ≤ 3s (no external search; AI inference only)

**Request**:
```json
POST /api/v1/leads/classify
{
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
  "trigger_workflow": true
}
```

**Response** (200):
```json
{
  "success": true,
  "contact_id": "abc123xyz",
  "business_name": "Sunrise Senior Living",
  "tier": "warm",
  "score": 72,
  "reasons": [
    "Active LinkedIn presence found",
    "Professional website with HTTPS",
    "Senior care industry — high fit",
    "Rating 4.5+ suggests established business"
  ],
  "workflow_triggered": true,
  "workflow_id": "wf_warm_sequence_001",
  "tag_applied": "tier:warm"
}
```

**Failure Cases**:
- `400` — `contact_id` missing or `business_name` missing
- `422` — `tier` not in `[cold, warm, hot]` (internal logic error — should never reach client)
- `500` — GPT API failure or GHL API failure on workflow trigger
- `503` — GHL API unreachable

**Scoring Logic** (classifier heuristics for GPT prompt):

| Signal | Hot | Warm | Cold |
|--------|-----|------|------|
| LinkedIn URL found | ✅ +20 | ✅ +10 | — |
| Website quality (HTTPS + loads) | +15 | +8 | no website: 0 |
| Lead source | `google_maps` detail page: +15 | `google_search`: +10 | `directory`: +5 |
| Industry fit (configurable) | Exact match: +20 | Partial: +10 | No match: 0 |
| Business size estimate | 50-200: +10 | 10-50: +5 | <10: 0 |
| Rating ≥ 4.0 | +10 | +5 | — |
| Location (local/target market) | +10 | +5 | Out of region: 0 |

Thresholds: **Hot ≥ 70**, **Warm 40–69**, **Cold < 40**

---

### 2.2 `POST /api/v1/leads/outreach-queue`

**Goal**: Create one or more `OutreachQueueItem` entries for a contact — one per platform with AI-drafted message — and persist them as GHL Notes (Phase 1 storage) or in-memory cache (Phase 2).

**Constraints**:
- Accepts array of platforms; drafts all in single request
- Each item must be independently retrievable and status-updatable
- Storage backend: GHL Notes (no new DB required for MVP). Item serialized as JSON in note body with `[OUTREACH_QUEUE]` prefix for filtering.
- Max 4 items per call (one per platform)

**Request**:
```json
POST /api/v1/leads/outreach-queue
{
  "contact_id": "abc123xyz",
  "business_name": "Sunrise Senior Living",
  "platforms": ["linkedin", "facebook"],
  "context": {
    "linkedin_url": "https://linkedin.com/company/sunrise-senior-living",
    "facebook_url": "https://facebook.com/sunriseseniorliving",
    "industry": "Senior Care",
    "sender_name": "Mai Bui",
    "sender_company": "GHL Sales Assistant",
    "pitch": "We help senior care facilities streamline their CRM"
  },
  "draft_messages": true
}
```

**Response** (201):
```json
{
  "success": true,
  "contact_id": "abc123xyz",
  "items_created": 2,
  "queue": [
    {
      "item_id": "oq_abc123_linkedin_1711684800",
      "contact_id": "abc123xyz",
      "platform": "linkedin",
      "message_type": "inmail",
      "status": "pending",
      "profile_url": "https://linkedin.com/company/sunrise-senior-living",
      "drafted_message": "Hi [Name], I came across Sunrise Senior Living...",
      "char_count": 287,
      "char_limit": 2000,
      "created_at": "2026-03-29T05:00:00Z",
      "ghl_note_id": "note_abc"
    },
    {
      "item_id": "oq_abc123_facebook_1711684800",
      "contact_id": "abc123xyz",
      "platform": "facebook",
      "message_type": "page_dm",
      "status": "pending",
      "profile_url": "https://facebook.com/sunriseseniorliving",
      "drafted_message": "Hello! I noticed Sunrise Senior Living...",
      "char_count": 210,
      "char_limit": 1000,
      "created_at": "2026-03-29T05:00:00Z",
      "ghl_note_id": "note_xyz"
    }
  ]
}
```

**Failure Cases**:
- `400` — `contact_id` or `platforms` missing; unsupported platform value
- `422` — `platforms` contains invalid value (not in `[linkedin, facebook, instagram, tiktok]`)
- `500` — GPT draft failure or GHL note save failure

---

### 2.3 `GET /api/v1/leads/outreach-queue/{contact_id}`

**Goal**: Retrieve all pending/sent/skipped outreach queue items for a contact by reading GHL Notes with `[OUTREACH_QUEUE]` prefix.

**Constraints**:
- Must filter GHL notes by prefix — cannot rely on separate DB
- Returns items sorted by `created_at` descending
- `status` filter is optional query param

**Request**:
```
GET /api/v1/leads/outreach-queue/abc123xyz?status=pending
```

**Response** (200):
```json
{
  "success": true,
  "contact_id": "abc123xyz",
  "total": 2,
  "items": [
    {
      "item_id": "oq_abc123_linkedin_1711684800",
      "contact_id": "abc123xyz",
      "platform": "linkedin",
      "message_type": "inmail",
      "status": "pending",
      "profile_url": "https://linkedin.com/company/sunrise-senior-living",
      "drafted_message": "Hi [Name], I came across Sunrise Senior Living...",
      "char_count": 287,
      "char_limit": 2000,
      "created_at": "2026-03-29T05:00:00Z",
      "sent_at": null,
      "ghl_note_id": "note_abc"
    }
  ]
}
```

**Failure Cases**:
- `404` — contact not found in GHL
- `500` — GHL Notes API failure

---

### 2.4 `POST /api/v1/leads/draft-outreach`

**Goal**: Draft a single platform-specific outreach message using GPT-4o-mini. Respects per-platform character limits and message conventions. Does NOT create a queue item — caller decides whether to save.

**Constraints**:
- Must enforce platform character limits in prompt and response
- Must include `char_count` in response so FE can show progress bar
- No external search needed if `profile_url` and `business_name` provided
- If LinkedIn URL given, re-use `social_research_service.py` scrape logic for profile context

**Platform Message Types & Limits**:

| Platform | Message Type | Char Limit | Notes |
|----------|-------------|------------|-------|
| `linkedin` | `inmail` | 2000 | Subject + body; professional tone |
| `linkedin` | `connection_request` | 300 | Very brief; personal, no hard pitch |
| `facebook` | `page_dm` | 1000 | Conversational, friendly |
| `instagram` | `dm` | 1000 | Casual, emoji OK |
| `tiktok` | `dm` | 500 | Very brief, informal |

**Request**:
```json
POST /api/v1/leads/draft-outreach
{
  "contact_id": "abc123xyz",
  "business_name": "Sunrise Senior Living",
  "platform": "linkedin",
  "message_type": "connection_request",
  "profile_url": "https://linkedin.com/company/sunrise-senior-living",
  "sender_name": "Mai Bui",
  "sender_company": "GHL Sales Assistant",
  "pitch": "We help senior care facilities streamline their CRM",
  "tone": "professional"
}
```

**Response** (200):
```json
{
  "success": true,
  "contact_id": "abc123xyz",
  "platform": "linkedin",
  "message_type": "connection_request",
  "drafted_message": "Hi! I help senior care facilities like Sunrise streamline CRM and save 5hrs/week. Would love to connect!",
  "char_count": 102,
  "char_limit": 300,
  "profile_url": "https://linkedin.com/company/sunrise-senior-living",
  "profile_data_used": {
    "company_name": "Sunrise Senior Living",
    "tagline": "Caring for seniors with dignity"
  }
}
```

**Failure Cases**:
- `400` — unsupported `platform` or `message_type` combination
- `422` — drafted message exceeds `char_limit` (should not happen — prompt enforces it; retry once)
- `500` — GPT API failure

---

### 2.5 `PATCH /api/v1/leads/outreach-queue/{item_id}` (P2)

**Goal**: Update the status of a queue item (pending → sent, pending → skipped).

**Request**:
```json
PATCH /api/v1/leads/outreach-queue/oq_abc123_linkedin_1711684800
{
  "status": "sent",
  "sent_at": "2026-03-29T05:30:00Z",
  "notes": "Sent via LinkedIn InMail"
}
```

**Response** (200):
```json
{
  "success": true,
  "item_id": "oq_abc123_linkedin_1711684800",
  "status": "sent",
  "ghl_note_updated": true
}
```

---

## 3. Data Model — `OutreachQueueItem`

```python
class OutreachQueueItem(BaseModel):
    item_id: str           # Format: "oq_{contact_id}_{platform}_{unix_timestamp}"
    contact_id: str        # GHL contact ID
    platform: Literal["linkedin", "facebook", "instagram", "tiktok"]
    message_type: Literal["inmail", "connection_request", "page_dm", "dm"]
    status: Literal["pending", "sent", "skipped"] = "pending"
    profile_url: Optional[str]          # Platform profile URL to open
    drafted_message: str                # AI-generated message text
    char_count: int                     # len(drafted_message)
    char_limit: int                     # Platform max chars
    created_at: datetime
    sent_at: Optional[datetime] = None
    ghl_note_id: Optional[str] = None   # GHL Note ID where item is persisted
    context_used: Optional[Dict[str, str]] = None  # Profile data used for drafting
```

**GHL Note Storage Format** (prefix-based, filtereable):
```
[OUTREACH_QUEUE]
item_id: oq_abc123_linkedin_1711684800
platform: linkedin
message_type: inmail
status: pending
profile_url: https://linkedin.com/company/sunrise-senior-living
created_at: 2026-03-29T05:00:00Z
---MESSAGE---
Hi [Name], I came across Sunrise Senior Living on LinkedIn...
```

---

## 4. GHL Workflow Integration Spec

### Overview

The classifier triggers a GHL Workflow by adding the contact to a pre-existing named workflow via GHL API. **The workflows must be created manually by the client in GHL first.**

### GHL API Endpoint

```
POST /contacts/{contactId}/workflow/{workflowId}
Version: 2021-07-28
Scope required: workflows.readonly, workflows.write (new — client must add)
```

### Configuration (`.env` additions)

```env
GHL_WORKFLOW_ID_HOT=wf_hot_immediate_001
GHL_WORKFLOW_ID_WARM=wf_warm_3day_001
GHL_WORKFLOW_ID_COLD=wf_cold_nurture_001
```

### Trigger Flow

```
POST /leads/classify
  → GPT scores contact → tier = "hot" | "warm" | "cold"
  → LeadClassifierService.classify()
    → apply GHL tag: "tier:hot" | "tier:warm" | "tier:cold"   (contacts.write ✅ already granted)
    → if trigger_workflow=true AND GHL_WORKFLOW_ID_{TIER} configured:
        POST /contacts/{contact_id}/workflow/{workflow_id}
    → return ClassifyResponse
```

### Workflow Templates (client must create in GHL)

| Tier | Workflow Name (suggested) | Contents |
|------|--------------------------|----------|
| Hot | `AI - Hot Lead Sequence` | Immediate email send + "Call in 2 hours" task + SMS alert to sales rep |
| Warm | `AI - Warm Lead Sequence` | Day 0: email; Day 3: follow-up email; Day 7: reminder task |
| Cold | `AI - Cold Nurture Sequence` | Day 0: email; Day 30: check-in; Day 90: re-engage |

### Content Injection

- AI-drafted email content (from `draft-email` endpoint) is saved as GHL Note **before** workflow trigger
- GHL Workflow can reference custom field `contact.ai_drafted_email` if BE stores it there
- For MVP: workflow uses its own template emails; AI draft is a separate Note for sales rep reference

### Fallback if workflows not configured

```python
if not workflow_id:
    logger.warning("No workflow configured for tier %s — tag applied only", tier)
    # Still returns success with workflow_triggered=False
```

---

## 5. Extension UI Spec — Outreach Queue Panel

### 5.1 Trigger Point

The outreach queue panel is accessible from the existing **ReviewPopup** after Phase 2A social profiles are saved. A new **"📤 Outreach Queue"** button appears in the popup footer.

### 5.2 New UI State: `outreach-queue-panel`

Rendered inside the existing `review-popup.js` shadow DOM. Replaces the profiles section when active.

### 5.3 Queue Panel Layout

```
┌─────────────────────────────────────────────┐
│ 📤 Outreach Queue — Sunrise Senior Living    │
│                                             │
│ [🔵 Classify Lead]  tier: WARM ✓            │
│                                             │
│ ─────────────────────────────────────────── │
│ ☑ LinkedIn  [InMail ▾]                     │
│   "Hi! I came across Sunrise Senior Living  │
│    on LinkedIn and wanted to reach out..."  │
│   102/2000 chars  [✏ Edit]  [📋 Copy]      │
│   [↗ Open LinkedIn Profile]                 │
│                                             │
│ ☑ LinkedIn  [Connection Request ▾]          │
│   "Hi! I help senior care facilities like  │
│    Sunrise streamline CRM..."               │
│   102/300 chars  [✏ Edit]  [📋 Copy]       │
│   [↗ Open LinkedIn Profile]                 │
│                                             │
│ ☑ Facebook  [Page DM ▾]                    │
│   "Hello! I noticed Sunrise Senior Living  │
│    has a great Facebook presence..."        │
│   210/1000 chars  [✏ Edit]  [📋 Copy]      │
│   [↗ Open Facebook Page]                    │
│                                             │
│ ─────────────────────────────────────────── │
│ [← Back]          [✅ Mark All Sent]        │
└─────────────────────────────────────────────┘
```

### 5.4 UI Components

| Component | Behavior |
|-----------|----------|
| **[🔵 Classify Lead]** button | Calls `POST /leads/classify`. Shows tier badge (🔴 HOT / 🟡 WARM / 🔵 COLD) after response |
| **Platform row** | Checkbox (include/exclude), platform icon, message type dropdown (`InMail` / `Connection Request`), message preview (3 lines truncated) |
| **Char counter** | `102/300 chars` — turns red when > 90% of limit |
| **[✏ Edit]** | Expands to `<textarea>` for inline editing; live char counter updates |
| **[📋 Copy]** | Copies drafted message to clipboard; button text changes to "✓ Copied!" for 2s |
| **[↗ Open Profile]** | Opens platform profile URL in new tab via `chrome.tabs.create` |
| **[← Back]** | Returns to profiles checkbox panel |
| **[✅ Mark All Sent]** | Calls `PATCH /outreach-queue/{item_id}` for all checked items; shows success toast |

### 5.5 New API Client Methods (extension/utils/api.js additions)

```js
ApiClient.classifyLead({ contact_id, business_name, website, industry, ... })
  → POST /api/v1/leads/classify

ApiClient.createOutreachQueue({ contact_id, business_name, platforms, context })
  → POST /api/v1/leads/outreach-queue

ApiClient.getOutreachQueue(contact_id, status = "pending")
  → GET /api/v1/leads/outreach-queue/{contact_id}

ApiClient.draftOutreach({ contact_id, platform, message_type, ... })
  → POST /api/v1/leads/draft-outreach

ApiClient.updateQueueItem(item_id, { status, sent_at })
  → PATCH /api/v1/leads/outreach-queue/{item_id}
```

### 5.6 Extension State Flow

```
ReviewPopup.showLinks()          ← existing Phase 2A (social profiles checkbox panel)
  → [📤 Outreach Queue] click
    → ReviewPopup.showOutreachQueue()
      → if no tier: show [🔵 Classify Lead] button
      → if no queue items: auto-call createOutreachQueue() for platforms with URLs
      → render queue items from API response
      → [📋 Copy] → navigator.clipboard.writeText(message)
      → [↗ Open] → chrome.tabs.create({ url: profile_url })
      → [✅ Mark All Sent] → PATCH each item → show toast "✓ Sent to 2 platforms"
```

---

## 6. New Backend Services Required

| Service | File | Responsibility |
|---------|------|---------------|
| `LeadClassifierService` | `backend/app/services/lead_classifier_service.py` | GPT-based scoring, tier assignment, GHL tag + workflow trigger |
| `OutreachQueueService` | `backend/app/services/outreach_queue_service.py` | Create/read/update queue items, serialize/parse GHL Notes |
| `OutreachDrafterService` | `backend/app/services/outreach_drafter_service.py` | Platform-specific message drafting (extends `AIEmailDrafterService`) |

### New Models

| File | New Models |
|------|-----------|
| `backend/app/models/classify.py` | `ClassifyRequest`, `ClassifyResponse` |
| `backend/app/models/outreach.py` | `OutreachQueueItem`, `CreateQueueRequest`, `CreateQueueResponse`, `QueueListResponse`, `DraftOutreachRequest`, `DraftOutreachResponse`, `UpdateQueueItemRequest` |

### GHL Service Extensions

New methods on [`GHLService`](../backend/app/services/ghl_service.py):

```python
async def trigger_workflow(self, contact_id: str, workflow_id: str) -> Dict[str, Any]
    # POST /contacts/{contact_id}/workflow/{workflow_id}

async def get_notes(self, contact_id: str) -> Dict[str, Any]
    # GET /contacts/{contact_id}/notes

async def update_note(self, contact_id: str, note_id: str, body: str) -> Dict[str, Any]
    # PUT /contacts/{contact_id}/notes/{note_id}
```

### New `.env` Variables

```env
# Phase 2B — Lead Classifier
GHL_WORKFLOW_ID_HOT=           # GHL Workflow ID for Hot tier
GHL_WORKFLOW_ID_WARM=          # GHL Workflow ID for Warm tier
GHL_WORKFLOW_ID_COLD=          # GHL Workflow ID for Cold tier

# Classifier tuning
CLASSIFIER_HOT_THRESHOLD=70    # Default 70
CLASSIFIER_WARM_THRESHOLD=40   # Default 40

# Target market for scoring bonus
TARGET_INDUSTRIES=Senior Care,Medical,Healthcare
TARGET_STATES=CO,TX,CA
```

---

## 7. Tech Constraints

| Constraint | Detail |
|-----------|--------|
| **No browser automation** | All message send actions are 100% manual human clicks. Extension only provides: drafted text (copyable), profile URL (opens in new tab). Zero bot actions, zero simulated clicks, zero DOM injection into external sites. |
| **Read-only public data** | Profile research uses Serper.dev Google Search results only. No scraping of LinkedIn/Facebook/Instagram internal data. No authenticated API calls to social platforms. |
| **Human sends all messages** | User copies drafted message → opens profile tab → pastes manually → clicks Send. Extension facilitates but never automates sending. |
| **GHL Notes as queue storage (MVP)** | No new database required. Queue items stored as structured text in GHL contact Notes. Prefix `[OUTREACH_QUEUE]` used for filtering. Limitation: no complex queries; linear scan of notes. |
| **GPT-4o-mini only** | Consistent with Phase 2A. No GPT-4 upgrade needed for classification or short message drafting. |
| **Character limits are hard constraints** | Prompt instructs GPT to stay within limit. If response exceeds limit, service retries once with stricter prompt before returning 422. |
| **Workflow IDs are external config** | GHL Workflow IDs are not auto-created by this system. Client must create workflows in GHL UI and provide IDs via `.env`. Missing IDs = graceful skip (tag-only fallback). |
| **New GHL scopes required** | `workflows.readonly` (list workflows), `workflows.write` (trigger workflow), `contacts/notes.readonly` (read notes for queue). Client must add these to API token. |

---

## 8. Acceptance Criteria

### AC-01: Lead Classification
- GIVEN a contact with `business_name`, `website`, `industry`, `linkedin_url`
- WHEN `POST /leads/classify` is called
- THEN response contains `tier` ∈ `{cold, warm, hot}`, `score` (0-100), `reasons` array (≥1 item)
- AND GHL tag `tier:{tier}` is applied to contact
- AND if `trigger_workflow=true` and env var set, GHL workflow is triggered
- AND response time < 3s

### AC-02: Outreach Queue Creation
- GIVEN a contact with LinkedIn and Facebook URLs
- WHEN `POST /leads/outreach-queue` with `platforms: ["linkedin", "facebook"]`
- THEN 2 queue items created, each with `drafted_message` within platform char limit
- AND each item persisted as GHL Note with `[OUTREACH_QUEUE]` prefix
- AND `GET /outreach-queue/{contact_id}` returns same 2 items

### AC-03: Platform Message Drafting
- GIVEN platform=`linkedin`, message_type=`connection_request`
- WHEN `POST /leads/draft-outreach`
- THEN `char_count ≤ 300`
- GIVEN platform=`linkedin`, message_type=`inmail`
- THEN `char_count ≤ 2000`

### AC-04: Extension Queue Panel
- GIVEN ReviewPopup is open with social profiles saved
- WHEN user clicks "📤 Outreach Queue"
- THEN panel shows queue items (or auto-drafts them if none exist)
- AND "📋 Copy" copies message to clipboard
- AND "↗ Open Profile" opens profile in new tab (no auto-send)
- AND "✅ Mark All Sent" updates item status in GHL

### AC-05: Tech Constraint Compliance
- Extension MUST NOT inject any content into LinkedIn, Facebook, Instagram, or TikTok pages
- Extension MUST NOT simulate clicks or form fills on external sites
- All send actions require explicit human interaction

---

## 9. Open Questions (Client Input Required)

| # | Question | Impact | Default if Not Answered |
|---|---------|--------|------------------------|
| OQ-1 | What are the GHL Workflow IDs for Hot/Warm/Cold sequences? (Client creates in GHL UI first) | Required for workflow trigger (F-03). Blocking for full F-03. | Skip workflow trigger; apply tier tag only |
| OQ-2 | What is the target industry list for Hot scoring bonus? (e.g. "Senior Care, Medical, Dental") | Affects classifier scoring accuracy | Use generic: any established business scores mid-range |
| OQ-3 | What target states/regions? (for location scoring bonus) | Affects classifier scoring | No location bonus applied |
| OQ-4 | For LinkedIn InMail — should the draft include a subject line + body, or body only? | Affects `DraftOutreachRequest` schema and prompt | Include subject + body (more useful) |
| OQ-5 | For Warm sequence (F-11 P2): should 3 email drafts be generated at once, or one-at-a-time on demand? | Affects `CreateQueueRequest` schema and GPT token usage | On-demand: one draft per call |
| OQ-6 | Does client want the tier tag format as `tier:hot` (with colon) or separate tag names like `Hot Lead`, `Warm Lead`? | Tag naming convention in GHL | Use `tier:hot` / `tier:warm` / `tier:cold` |
| OQ-7 | Should `classify` be called automatically on every new lead capture, or only manually? | If auto: adds ~1.5s to capture flow | Manual only (opt-in `trigger_workflow` flag) |
| OQ-8 | New GHL scopes needed: `workflows.readonly`, `workflows.write`, `contacts/notes.readonly`. Can client add these to API token? | Required for workflow trigger and queue read | Without `workflows.write`: tag-only fallback. Without `contacts/notes.readonly`: queue read disabled |

---

## 10. New GHL Scopes Required

| Scope | Purpose | Impact if Missing |
|-------|---------|-------------------|
| `workflows.write` | Trigger workflow on classify | F-03 blocked — tier tag applied only |
| `workflows.readonly` | List available workflows (optional — for validation) | Non-blocking |
| `contacts/notes.readonly` | Read notes for queue fetch (`GET /outreach-queue/{id}`) | Queue read (`GET`) blocked |

Existing scopes already granted: `contacts.write`, `contacts.readonly`, `locations/customFields.readonly`, `locations/customFields.write`, `locations/tags.readonly`, `locations/tags.write`

---

## 11. File Change Summary

### New Files

| File | Type | Owner |
|------|------|-------|
| `backend/app/models/classify.py` | New | BE Dev |
| `backend/app/models/outreach.py` | New | BE Dev |
| `backend/app/services/lead_classifier_service.py` | New | BE Dev |
| `backend/app/services/outreach_queue_service.py` | New | BE Dev |
| `backend/app/services/outreach_drafter_service.py` | New | BE Dev |

### Modified Files

| File | Change | Owner |
|------|--------|-------|
| `backend/app/api/v1/leads.py` | Add 4 new endpoints: classify, outreach-queue (POST/GET/PATCH), draft-outreach | BE Dev |
| `backend/app/services/ghl_service.py` | Add `trigger_workflow()`, `get_notes()`, `update_note()` | BE Dev |
| `backend/app/config.py` | Add workflow IDs + classifier threshold env vars | BE Dev |
| `extension/utils/api.js` | Add 5 new `ApiClient` methods | FE Dev |
| `extension/content/components/review-popup.js` | Add `showOutreachQueue()` panel state, classify button, queue item rows, copy/open/mark-sent actions | FE Dev |
| `extension/manifest.json` | Add `clipboardWrite` permission for copy-to-clipboard | FE Dev |
| `backend/.env.example` | Add new env vars | BE Dev |

---

*Signal: `spec-ready` → pm*
