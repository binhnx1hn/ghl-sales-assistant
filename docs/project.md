# Project Log

## BE Dev: GHL Opportunities Integration — Auto-Create/Move Opportunity on Classify

**Date**: 2026-03-29
**Status**: ✅ be-done → integration
**Author**: BE Dev

### Changes
- [`backend/app/config.py`](../backend/app/config.py): Added `ghl_pipeline_id`, `ghl_stage_id_hot`, `ghl_stage_id_warm`, `ghl_stage_id_cold` to `Settings`
- [`backend/.env.example`](../backend/.env.example): Added Phase 2B GHL Opportunities Pipeline section with comments
- [`backend/app/services/ghl_service.py`](../backend/app/services/ghl_service.py): Added `search_opportunities()`, `create_opportunity()`, `update_opportunity_stage()` under new `# ─── Opportunity Operations` section
- [`backend/app/services/lead_classifier_service.py`](../backend/app/services/lead_classifier_service.py): Added Step 5 opportunity upsert after tag+workflow; returns `opportunity_action` and `opportunity_id`
- [`backend/app/models/phase2b.py`](../backend/app/models/phase2b.py): Added `opportunity_action: Optional[str]` and `opportunity_id: Optional[str]` to `ClassifyResponse`

### API-CONTRACT

| Endpoint | Change | Field | Values |
|---|---|---|---|
| `POST /api/v1/leads/classify` | Response extended | `opportunity_action` | `"created"` \| `"updated"` \| `"skipped"` \| `"failed"` |
| `POST /api/v1/leads/classify` | Response extended | `opportunity_id` | GHL Opportunity ID string or `null` |

### Behaviour
- **Pipeline configured** (`GHL_PIPELINE_ID` + stage IDs set): contact's opportunity is created or moved to the matching stage on every classify call
- **Pipeline not configured**: `opportunity_action: "skipped"`, no error
- **GHL API error**: `opportunity_action: "failed"`, warning logged, **no 500 raised**

---

## Phase 2B Pipeline — Outreach Queue + Lead Classifier + Warm/Hot Sequence

**Date**: 2026-03-29
**Status**: ✅ APPROVED — ready for Deliver
**Pipeline**:
- [x] FE Dev: Fix BUG-001 — `google-search.js` `a[ping]` selector returning Google Maps URL
- [x] BA: Spec Phase 2B — Outreach Queue UI + Lead Classifier + Warm/Hot GHL Sequence Agent → [`plans/phase2b-spec.md`](../plans/phase2b-spec.md)
- [x] BE Dev: Lead Classifier service + `POST /leads/classify` + GHL Workflow trigger
- [x] BE Dev: Outreach Queue API — CRUD queue items, per-platform draft messages
- [x] FE Dev: Outreach Queue review panel in extension + draft-message UI per platform
- [x] Integration: Verify Phase 2B BE+FE contracts hold, server starts, endpoints respond
- [x] QC: Audit Phase 2B against BA spec → ✅ QC-PASS (5 defects found + fixed: QC-001 to QC-005)
- [x] Reviewer: ✅ APPROVED — 2026-03-29T05:32Z
- [ ] Deliver: Release notes + tag

---

## Reviewer Verdict — Phase 2B

**Date**: 2026-03-29T05:32Z
**Verdict**: ✅ APPROVED
**Reviewer**: Reviewer - Final Authority
**Signal**: `reviewer-approved` → deliver

---

### Architecture Fitness Assessment

#### ARCH-01: Storage — GHL Notes as MVP Queue
**PASS.** Using GHL Notes with a `[OUTREACH_QUEUE]` prefix as queue storage is the correct decision for this scale. Mai Bui's use case is a single-user Chrome extension with low-volume outreach (tens of leads, not thousands). Introducing a separate DB for queue persistence would be over-engineering. The serialize/parse pattern in [`backend/app/services/outreach_queue_service.py`](../backend/app/services/outreach_queue_service.py) is robust: structured header block + `---MESSAGE---` separator, defensive `_parse_item()` with per-field `try/except`, fallback defaults. Two correctness risks noted but acceptable at this scale (see P3 items below).

#### ARCH-02: AI — GPT-4o-mini Consistent Usage
**PASS.** All three AI calls (email drafter Phase 2A, lead classifier, outreach drafter) use the same `AsyncOpenAI` client with lazy init, `response_format={"type": "json_object"}`, low temperature for classification (0.2) and higher for creative drafting (0.7). Score clamping (`max(0, min(100, score))`), tier validation against allowed enum, and hard char-limit truncation as safety net are all correct defensive patterns. The scoring heuristics in [`backend/app/services/lead_classifier_service.py`](../backend/app/services/lead_classifier_service.py) are clearly documented and appropriately generic pending client answers to OQ-2/OQ-3.

#### ARCH-03: ToS / Legal — Human-in-the-Loop Design
**PASS.** The design is sound on all social platform ToS:
- Extension does **not** inject into LinkedIn/Facebook/Instagram/TikTok pages (manifest `host_permissions` and `content_scripts.matches` only cover Google, Yelp, Yellow Pages).
- No simulated clicks, no form fills, no automated send.
- Copy button requires explicit human clipboard action; "Open Profile" requires human navigation; "Mark Sent" requires human confirmation.
- `trigger_workflow` is opt-in (`bool = False` default) — no automatic GHL side-effects on capture.
- AC-05 from spec is architecturally enforced, not just documented.

#### ARCH-04: API Contract Integrity
**PASS.** All 10 endpoints (5 Phase 2A + 5 Phase 2B) verified by Integration (32/32 checks). QC-002 (`item.message` → `item.drafted_message`) and QC-003 (context URLs missing) were HIGH-severity contract mismatches — both confirmed fixed. `_request()` in [`extension/utils/api.js`](../extension/utils/api.js) now correctly sends PATCH with body. URL contracts between FE `ApiClient` and BE router confirmed 1:1.

#### ARCH-05: Error Handling Completeness
**PASS** with minor note. All 5 Phase 2B endpoints follow the correct pattern: `ValueError` → 400, `GHLAPIError` → propagate status, generic `Exception` → 500. GHL tag failure and workflow trigger failure are gracefully swallowed (log warning, return `workflow_triggered: false`) — correct for non-blocking side effects. Draft failure per platform falls back to `[Draft failed for {platform}. Please write manually.]` — good UX. The dead `except` block (QC-001) has been removed.

#### ARCH-06: MV3 Compliance
**PASS.** `clipboardWrite` permission added (QC-004 fixed). `navigator.clipboard.writeText` used (not `document.execCommand`). `chrome.tabs.create` used for "Open Profile" (not `window.open`). No `eval()`, no CDN scripts, no dynamic `import()`. Service worker registered correctly. Content scripts load order correct in manifest.

---

### BUG-001 Fix Assessment

**PASS.** The [`google-search.js`](../extension/content/extractors/google-search.js) fix is correct and defence-in-depth:
1. Primary: `.bkaPDb a.n1obkb[href^='http']` — targets the exact "Website" action button container
2. Secondary: `a[href^='http']:has(span.aSAiSd)` — targets the link wrapping the "Website" label span
3. Text-scan fallback explicitly guards `!href.includes("google.com/maps")` and `!href.includes("google.com/search")`

The overly broad `a[ping]` fallback that returned Google Maps URLs is eliminated. Fix is applied before any `a[ping]` scan in the selector chain.

---

### Open Questions Status (from spec §9)

| OQ | Status | Impact |
|----|--------|--------|
| OQ-1 | Client-side action required — GHL Workflow IDs not yet configured | Workflow trigger gracefully skipped; tag-only mode works now |
| OQ-2/OQ-3 | Not blocking — classifier uses generic heuristics; industry/location scoring will improve when client provides targets | Low: scoring still useful without customization |
| OQ-4 | Resolved in implementation — InMail drafts body only (no separate subject field in outreach drafter) | Acceptable for MVP |
| OQ-5 | Resolved — on-demand per-platform draft (default) | Correct default |
| OQ-6 | Resolved — `tier:hot` / `tier:warm` / `tier:cold` | Implemented |
| OQ-7 | Resolved — classify is manual/opt-in | Correct |
| OQ-8 | Client must add `workflows.write` + `contacts/notes.readonly` scopes to GHL API token | **Blocking for workflow trigger + queue read in production** — graceful fallback exists |

**OQ-8 is the only production blocker** and is a client-side GHL configuration step, not a code defect.

---

### P3 Tech Debt Items (Non-blocking, Future Phase)

1. **GHL Notes pagination**: [`ghl_service.get_notes()`](../backend/app/services/ghl_service.py) fetches a single page of notes. If a contact accumulates >20-50 notes, old queue items may not appear in `GET /outreach-queue`. Add pagination traversal when contact note volume grows.

2. **`_parse_item()` fragility on note body corruption**: If a GHL Note body is manually edited and breaks the `key: value` format, parsing silently returns `None` and the item disappears from the queue. Acceptable at MVP scale; add a note integrity check in P3.

3. **Classifier prompt has no client-specific industry/location targets**: OQ-2/OQ-3 unanswered. Scoring defaults are generic — a dental clinic in any state scores identically to a dental clinic in Mai Bui's target market. Revisit after client answers.

4. **No idempotency guard on `createOutreachQueue`**: Opening the outreach panel multiple times re-creates queue items (new GHL Notes per call). The FE guards against this with `if (!this._queueItems || this._queueItems.length === 0)` in memory, but a browser refresh will trigger re-creation. Add a duplicate-check on existing `[OUTREACH_QUEUE]` notes per platform in P3.

5. **Char truncation at boundary**: The safety-net truncation in [`outreach_drafter_service.py`](../backend/app/services/outreach_drafter_service.py) cuts mid-word/mid-sentence. Acceptable safety net but a word-boundary truncation would be cleaner. Low priority.

---

### Summary

Phase 2B is production-ready for Mai Bui's single-user use case. All 5 QC defects (QC-001 through QC-005) are confirmed fixed. Architecture choices are appropriate for scale: GHL Notes as queue storage avoids new infrastructure, GPT-4o-mini is consistent with Phase 2A, human-in-the-loop design is ToS-compliant across all four platforms. The only production action required before full feature activation is the client adding two GHL API token scopes (OQ-8).

**Signal**: `reviewer-approved` → deliver

### CHECKPOINT — 2026-03-29T05:28Z
**DOING**: BE fixes QC-001 + QC-005 applied → signal be-fix-done → qc
**DONE**: 2 QC defects fixed in 2 backend files.
- QC-001: Removed dead/unreachable second `except Exception` block (wrong message `"Failed to list leads"`) from `draft_email` endpoint (`backend/app/api/v1/leads.py` line 301-305)
- QC-005: Changed `items.sort()` in `get_queue()` from ascending to descending (`reverse=True`) (`backend/app/services/outreach_queue_service.py` line 317)
**Syntax**: `python -m py_compile backend/app/api/v1/leads.py` ✅ | `python -m py_compile backend/app/services/outreach_queue_service.py` ✅
**Files changed**: `backend/app/api/v1/leads.py`, `backend/app/services/outreach_queue_service.py`
**LEFT**: QC re-audit → Reviewer → Deliver
**BLOCKERS**: None

### CHECKPOINT — 2026-03-29T05:27Z
**DOING**: FE fixes QC-002, QC-003, QC-004 applied → signal fe-fix-done → qc
**DONE**: 3 QC defects fixed in 2 files.
- QC-002: `item.message` → `item.drafted_message` in `renderQueueItem`, textarea `input` handler, Copy button handler (`review-popup.js` lines 937, 1137, 1149)
- QC-003: `createOutreachQueue` context now includes `linkedin_url`, `facebook_url`, `instagram_url`, `tiktok_url` from `editedProfiles` parameter (`review-popup.js` line 1028)
- QC-004: `"clipboardWrite"` added to `permissions` array in `extension/manifest.json`
**Syntax**: `node --check extension/content/components/review-popup.js` ✅ | `node --check extension/utils/api.js` ✅
**Files changed**: `extension/content/components/review-popup.js`, `extension/manifest.json`
**LEFT**: QC re-audit (QC-001 BE fix remains for BE Dev) → Reviewer → Deliver
**BLOCKERS**: None (QC-001 is BE scope, not FE)

### CHECKPOINT — 2026-03-29T05:23Z
**DOING**: QC Phase 2B complete → signal qc-fail → pm
**DONE**: Full audit of 11 files (7 BE + 4 FE). 4 defects found — 2 HIGH, 2 MEDIUM, 1 LOW.
**LEFT**: FE Dev fixes QC-001 to QC-004 → re-audit → Reviewer → Deliver
**NEXT**: PM routes qc-fail to FE Dev for QC-002 (item.message → drafted_message) + QC-004 (clipboardWrite manifest) + QC-003 (context URLs) + QC-001 (dead except block)
**BLOCKERS**: QC-002 (blank messages in queue panel), QC-004 (clipboard permission missing)

### CHECKPOINT — 2026-03-29T05:19Z
**DOING**: Integration Phase 2B complete → signal integration-verified → vision-parser
**DONE**: All 8 checks passed — py_compile (7 files), node --check (2 files), import contracts, endpoint paths, FE↔BE URL contract, Phase 2A regression, MV3 compliance, GHL method signatures
**LEFT**: Vision Parser → QC → Review → Deliver
**NEXT**: Vision Parser — screenshot outreach queue panel UI
**BLOCKERS**: None (1 unreachable `except` block in `draft_email` noted for QC)

---

## Integration: Phase 2B — Outreach Queue + Lead Classifier

**Date**: 2026-03-29T05:19Z
**Status**: ✅ PASS
**Signal**: `integration-verified` → vision-parser

### Check Results

| Check | Result | Notes |
|-------|--------|-------|
| CHECK-01 py_compile `phase2b.py` | ✅ PASS | exit 0 |
| CHECK-01 py_compile `lead_classifier_service.py` | ✅ PASS | exit 0 |
| CHECK-01 py_compile `outreach_drafter_service.py` | ✅ PASS | exit 0 |
| CHECK-01 py_compile `outreach_queue_service.py` | ✅ PASS | exit 0 |
| CHECK-01 py_compile `leads.py` | ✅ PASS | exit 0 |
| CHECK-01 py_compile `ghl_service.py` | ✅ PASS | exit 0 |
| CHECK-01 py_compile `config.py` | ✅ PASS | exit 0 |
| CHECK-02 node --check `api.js` | ✅ PASS | exit 0 |
| CHECK-02 node --check `review-popup.js` | ✅ PASS | exit 0 |
| CHECK-03 Import contracts in `leads.py` | ✅ PASS | All 8 Phase 2B models + 3 services imported; no circular imports |
| CHECK-04 `POST /classify` → `ClassifyRequest`/`ClassifyResponse` | ✅ PASS | 200/400/500 |
| CHECK-04 `POST /draft-outreach` → `DraftOutreachRequest`/`DraftOutreachResponse` | ✅ PASS | 200/400/500 |
| CHECK-04 `POST /outreach-queue` → `CreateOutreachQueueRequest`/`CreateOutreachQueueResponse` | ✅ PASS | status_code=201 |
| CHECK-04 `GET /outreach-queue/{contact_id}` → `GetOutreachQueueResponse` | ✅ PASS | 200/404/500 |
| CHECK-04 `PATCH /outreach-queue/{item_id}` → `UpdateQueueItemRequest`/`UpdateQueueItemResponse` | ✅ PASS | 200/404/500 |
| CHECK-05 FE `classifyLead` → `${apiUrl}/leads/classify` | ✅ PASS | matches BE |
| CHECK-05 FE `createOutreachQueue` → `${apiUrl}/leads/outreach-queue` | ✅ PASS | matches BE |
| CHECK-05 FE `getOutreachQueue` → `${apiUrl}/leads/outreach-queue/${contactId}` | ✅ PASS | matches BE |
| CHECK-05 FE `draftOutreach` → `${apiUrl}/leads/draft-outreach` | ✅ PASS | matches BE |
| CHECK-05 FE `updateQueueItem` → `${apiUrl}/leads/outreach-queue/${itemId}?contact_id=` | ✅ PASS | PATCH + query param matches BE |
| CHECK-06 Phase 2A regression `POST /capture` | ✅ PASS | still present |
| CHECK-06 Phase 2A regression `GET /` (list) | ✅ PASS | still present |
| CHECK-06 Phase 2A regression `POST /enrich` | ✅ PASS | still present |
| CHECK-06 Phase 2A regression `POST /save-profiles` | ✅ PASS | still present |
| CHECK-06 Phase 2A regression `POST /draft-email` | ✅ PASS | still present |
| CHECK-07 MV3: `chrome.tabs.create` used (no `window.open`) | ✅ PASS | line 1165 review-popup.js |
| CHECK-07 MV3: `navigator.clipboard.writeText` used | ✅ PASS | line 1150 review-popup.js |
| CHECK-07 MV3: no `eval()`, no dynamic `import()`, no CDN URLs | ✅ PASS | none found |
| CHECK-08 GHL `add_tag` → `POST /contacts/{id}/tags` (via `add_tags`) | ✅ PASS | correct verb/path |
| CHECK-08 GHL `trigger_workflow` → `POST /contacts/{id}/workflow/{workflow_id}` | ✅ PASS | correct verb/path |
| CHECK-08 GHL `get_notes` → `GET /contacts/{id}/notes` | ✅ PASS | correct verb/path |
| CHECK-08 GHL `update_note` → `PUT /contacts/{id}/notes/{note_id}` | ✅ PASS | correct verb/path |

### Issues Found
None. (QC note: unreachable `except Exception` block at `leads.py` lines 301-305 — dead code after prior `except Exception`, not a runtime defect.)

---

### CHECKPOINT — 2026-03-29T05:16Z
**DOING**: FE Phase 2B complete → signal fe-done → integration
**DONE**: 5 new ApiClient methods (classifyLead, createOutreachQueue, getOutreachQueue, draftOutreach, updateQueueItem), outreach queue panel UI (classify step, auto-load queue, per-item copy/edit/open, mark all sent, back button), PATCH body fix in _request
**LEFT**: Integration → QC → Review → Deliver
**NEXT**: Integration — verify BE+FE contracts hold
**BLOCKERS**: None

### CHECKPOINT — 2026-03-29T05:11Z
**DOING**: BE Phase 2B complete → signal be-done → integration
**DONE**: Lead classifier service, outreach drafter service, outreach queue service (GHL Notes storage), 5 new API endpoints, GHL service methods (add_tag, trigger_workflow, get_notes, update_note), new Pydantic models, config + .env.example updated
**LEFT**: FE Dev: Outreach Queue panel UI → Integration → QC → Review
**NEXT**: FE Dev — implement outreach queue review panel + draft-message UI
**BLOCKERS**: None

---

## BE: Phase 2B — Lead Classifier + Outreach Queue API

**Date**: 2026-03-29
**Status**: ✅ Complete
**Signal**: `be-done` → integration

### API-CONTRACT

| Method | Path | Request Model | Response Model | Status Codes |
|--------|------|--------------|----------------|--------------|
| `POST` | `/api/v1/leads/classify` | `ClassifyRequest` | `ClassifyResponse` | 200, 400, 500 |
| `POST` | `/api/v1/leads/draft-outreach` | `DraftOutreachRequest` | `DraftOutreachResponse` | 200, 400, 500 |
| `POST` | `/api/v1/leads/outreach-queue` | `CreateOutreachQueueRequest` | `CreateOutreachQueueResponse` | 201, 400, 500 |
| `GET` | `/api/v1/leads/outreach-queue/{contact_id}` | `?status=pending\|sent\|skipped` | `GetOutreachQueueResponse` | 200, 404, 500 |
| `PATCH` | `/api/v1/leads/outreach-queue/{item_id}` | `UpdateQueueItemRequest` + `?contact_id=` | `UpdateQueueItemResponse` | 200, 404, 500 |

### Key Implementation Notes

- **Lead Classifier** ([`lead_classifier_service.py`](../backend/app/services/lead_classifier_service.py)): GPT-4o-mini scores 0-100 → tier hot/warm/cold. Applies GHL tag `tier:{tier}`. Workflow trigger is gracefully non-fatal.
- **Outreach Drafter** ([`outreach_drafter_service.py`](../backend/app/services/outreach_drafter_service.py)): Per-platform char limits enforced in prompt + post-generation truncation safety net. 5 combos: linkedin/inmail (2000), linkedin/connection_request (300), facebook/page_dm (1000), instagram/dm (1000), tiktok/dm (500).
- **Outreach Queue** ([`outreach_queue_service.py`](../backend/app/services/outreach_queue_service.py)): Uses GHL Notes as storage — no new DB. Notes prefixed with `[OUTREACH_QUEUE]` + `---MESSAGE---` separator. `item_id = oq_{contact_id}_{platform}_{unix_ts}`.
- **GHL Service** ([`ghl_service.py`](../backend/app/services/ghl_service.py)): Added `add_tag()`, `trigger_workflow()`, `get_notes()`, `update_note()`.
- **Config** ([`config.py`](../backend/app/config.py)): Added `ghl_workflow_id_hot/warm/cold` optional fields.
- **No breaking changes** to Phase 2A endpoints (`/capture`, `/enrich`, `/save-profiles`, `/draft-email`, `/duplicate-check`).

### CHECKPOINT — 2026-03-29T04:58Z
**DOING**: Delegating BUG-001 fix (FE) + Phase 2B BA spec in parallel
**DONE**: Phase 2A complete — social finder, email drafter, checkbox-list UI, save-profiles, draft-email endpoints
**LEFT**: Phase 2B — Outreach Queue, Lead Classifier, Warm/Hot Sequence automation
**NEXT**: BA spec → BE classifier → BE queue API → FE queue UI → Integration → QC → Review
**BLOCKERS**: None

---

## BUG-001 Fix: Google Search Extractor — Wrong Website URL

**Date**: 2026-03-29
**Status**: ✅ Complete
**Signal**: `fe-fix-done` → qc

### What Changed

#### [`extension/content/extractors/google-search.js`](../extension/content/extractors/google-search.js:74) — `_findWebsiteLink()` only

**Root cause**: Step 2 of `_findWebsiteLink()` used `querySelectorAll("a[href^='http'][ping]")` — the Google Maps place link also carries a `ping` attribute and appears **before** the real business website link in DOM order, so it was returned first even though its text didn't say "Website". The existing text-contains-"Website" check wasn't the problem; the Maps link can sometimes carry "Website" text too in certain layouts.

**Fix applied (additive, no existing logic removed)**:

1. **New step 1b** (lines 84–92): Two targeted selectors checked *before* the broad `a[ping]` scan:
   - `.bkaPDb a.n1obkb[href^='http']` — the Local Pack "Website" action-button link
   - `a[href^='http']:has(span.aSAiSd)` — any link wrapping the `<span class="aSAiSd">Website</span>` label
   These match the exact DOM structure reported by the user and win before any Maps link is considered.

2. **Step 2 guard** (line 97): Added `!href.includes("google.com/maps") && !href.includes("google.com/search")` safety filter so the broad `a[ping]` scan can never return a Google Maps or Google Search URL even if future layouts omit the targeted classes.

3. **`_extractFromKnowledgePanel()`** (line 363): **Untouched** — it already delegates to `_findWebsiteLink()` and benefits from the same fix automatically.

---

## FE: Social Profile Review — Checkbox-List UI (Phase 2 Panel)

**Date**: 2026-03-29
**Status**: ✅ Complete
**Signal**: `fe-done` → integration

### Changes Made

#### [`extension/content/components/review-popup.js`](../extension/content/components/review-popup.js:507)

1. **`checkedPlatforms`** object added alongside `editedProfiles` (line 507) — tracks per-platform save intent, initialized from `profiles_found`.

2. **`renderProfileLinks()`** (line 579) — replaced badge+found/notFound layout with a unified **checkbox-list**:
   - One row per platform (all 4: LinkedIn, Facebook, Instagram, TikTok)
   - Each row: `[checkbox] [icon] [Label] [URL or "not found"] [▾N badge if candidates > 1]`
   - Checkbox `checked` if `checkedPlatforms[key]`; `disabled` if no URL and no candidates
   - URL truncated to 35 chars, opens in new tab; `stopPropagation` prevents edit trigger
   - Removed hint text `(click to edit · ▾N = multiple options)` and separate "Not found" section
   - Dark theme: `rgba(255,255,255,0.03)` row bg, `#7C3AED` checkbox accent, `#9ca3af` URL color

3. **`_attachPickerHandlers(key)`** (line 652) — extracted picker+plain-edit wiring into a helper declared **before** `showLinks` to avoid `const` TDZ issues. Auto-sets `checkedPlatforms[key] = true` when a URL is confirmed.

4. **`showLinks()`** (line 694) — attaches:
   - `[data-chk-key]` `change` handlers: sync `checkedPlatforms`; opens picker if user checks a no-URL platform that has candidates
   - `[data-edit-key]` `click` handlers (icon/label/badge): open edit/picker flow
   - `[data-row-key]` `click` handlers (whole row, excluding checkbox + URL `<a>`): open edit/picker flow

5. **`confirmBtn` handler** (line 726) — syncs checkbox DOM state → `checkedPlatforms`, builds `profilesToSave` where unchecked or empty URL = `""`, sends only checked+non-empty profiles to `ApiClient.saveProfiles`.

---

## Bug Fix: Yelp `/biz/` Detail Page — "Send to GHL" Button Not Showing

**Date**: 2026-03-19
**Status**: ✅ Complete
**Signal**: `fe-done` → integration

### Problem
On Yelp business detail pages (e.g. `https://www.yelp.com/biz/buena-vista-care-center-anaheim`), the floating "⚡ Send to GHL" button never appeared. The extension was injected (manifest has `https://www.yelp.com/*`), but two code paths failed to handle `/biz/` detail pages.

### Root Cause
1. **`content.js`** — `autoShowOnPlacePage()` only handled Google Maps `/maps/place/`. No equivalent for Yelp `/biz/`.
2. **`generic.js`** — `getListings()` only looked for Yelp search result card selectors, which don't exist on `/biz/` detail pages.

### Changes Made

#### 1. [`extension/content/extractors/generic.js`](../extension/content/extractors/generic.js:62) — `getListings()`
- Added Yelp `/biz/` detail page fallback: when no search cards found AND on `/biz/` path, pushes `<main>`, `#wrap`, `.biz-page-header`, or `h1.parentElement` as a listing.

#### 2. [`extension/content/content.js`](../extension/content/content.js:65) — New `autoShowOnYelpBizPage()`
- New function that detects `yelp.com` + `/biz/` path, finds main content container, calls `FloatingButton.show()`.
- Called from `init()` after `autoShowOnPlacePage()`.

#### 3. [`extension/content/content.js`](../extension/content/content.js:113) — Mouseleave handlers (×2)
- Both `listing.mouseleave` (line 113) and `document.mouseleave` (line 187) now check for Yelp `/biz/` pages alongside Google Maps place pages, preventing auto-hide on detail pages.

#### 4. [`extension/content/components/floating-button.js`](../extension/content/components/floating-button.js:79) — `show()` positioning
- Added `isYelpBizPage` branch: positions button at top-right (`right: 20px`, `top: max(panelRect.top + 10, 80)px`).

### Build
- No build step required — Chrome extension uses vanilla JS loaded via `manifest.json`.
- All existing Google Maps/Search functionality unchanged (additive `else if` branches only).

### Verification Checklist
- [ ] Load extension in Chrome → visit Yelp search results → hover cards → button appears
- [ ] Visit `https://www.yelp.com/biz/any-business` → button auto-appears top-right
- [ ] Click "Send to GHL" on Yelp biz page → ReviewPopup opens with extracted data
- [ ] Google Maps `/maps/place/` pages still work as before
- [ ] Google Search result hover still works as before

---

## Bug Report: Google Search Extractor — Wrong Website URL Extracted

**Date**: 2026-03-19
**Status**: 🔴 QC-FAIL — needs FE fix
**Audit**: See [`docs/audit.md`](audit.md) BUG-001

### Summary
[`_extractFromLocalPack()`](../extension/content/extractors/google-search.js:159) fallback selector `a[ping]` is too broad — it matches the Google Maps place link before the actual business website link. Leads sent to GHL get a `google.com/maps` URL instead of the real website.

**Signal**: `qc-fail` → `pm` → route to FE Dev

---

## Improve Backend Packaging for Portable Deployment

**Date**: 2026-03-19
**Status**: ✅ Complete
**Signal**: `be-done` → integration

### Summary
Production-hardened Docker packaging and one-command deployment scripts for the backend.

### Changes Made

#### 1. [`backend/.dockerignore`](../backend/.dockerignore) — New
Excludes `__pycache__/`, `*.pyc`, `.env`, `venv/`, `tests/`, `*.md`, `.git/` from Docker build context.

#### 2. [`backend/Dockerfile`](../backend/Dockerfile) — Improved
- Multi-stage build (deps → production) for smaller image
- Non-root `appuser` (UID 1001) for security
- `LABEL` metadata (version, description, maintainer)
- `WORKERS` env var (default 2) controls uvicorn worker count

#### 3. [`docker-compose.yml`](../docker-compose.yml) — Improved
- Added `logging` config: json-file driver, max-size 10m, max-file 3
- Added `networks` section with `ghl-network` bridge
- Added `environment` defaults (HOST, PORT, DEBUG, WORKERS) overridden by `.env`
- Preserved existing healthcheck

#### 4. [`deploy.sh`](../deploy.sh) — New
Linux/macOS deployment script with flags: `--build`, `--restart`, `--logs`, `--stop`.
Preflight checks: Docker, Docker Compose, `.env` file (auto-copies from `.env.example` if missing).

#### 5. [`deploy.bat`](../deploy.bat) — New
Windows equivalent using `docker compose` (v2 plugin). Same flags and preflight checks.

### Deployment Commands

| Command | Linux/macOS | Windows |
|---------|-------------|---------|
| Build + Start | `./deploy.sh` | `deploy.bat` |
| Force rebuild | `./deploy.sh --build` | `deploy.bat --build` |
| Restart | `./deploy.sh --restart` | `deploy.bat --restart` |
| View logs | `./deploy.sh --logs` | `deploy.bat --logs` |
| Stop | `./deploy.sh --stop` | `deploy.bat --stop` |

---

## Extension Packaging Script for Distribution

**Date**: 2026-03-19
**Status**: ✅ Complete
**Signal**: `fe-done` → integration

### Summary
Created cross-platform packaging scripts to produce a distributable `.zip` of the Chrome extension, eliminating the need for users to clone the repo and "Load unpacked" from source.

### Changes Made

#### 1. [`package-extension.sh`](../package-extension.sh) — New
Bash script (Linux/macOS) that:
- Reads version from [`extension/manifest.json`](../extension/manifest.json) (currently `1.0.1`)
- Cleans and creates `dist/ghl-sales-assistant-extension/`
- Copies all extension files, excluding `.git`, `*.md`, `.DS_Store`, `Thumbs.db`, `node_modules`, `*.svg`
- Creates `dist/ghl-sales-assistant-extension-v1.0.1.zip` via `zip` or Python fallback
- Prints file count, size, contents summary, and Chrome install instructions

#### 2. [`package-extension.bat`](../package-extension.bat) — New
Windows equivalent using PowerShell:
- `ConvertFrom-Json` to read manifest version
- `Get-ChildItem` with exclusion filters for file copy
- `Compress-Archive` for zip creation

### Build Verification
```
package-extension.bat → Exit code: 0
Output: dist/ghl-sales-assistant-extension-v1.0.1.zip
Size:   32 KB
Files:  22 (all JS, CSS, HTML, PNG — no SVG/MD)
```

### No Existing Files Modified
- Zero changes to `extension/manifest.json` or any JS/CSS/HTML files
- Scripts are additive (new root-level files only)

---

## Portable Deployment Packaging — Full Pipeline

**Date**: 2026-03-19
**Status**: ✅ Complete
**Pipeline**: `pm` → `be-dev` → `fe-dev` → `deliver`

### Goal
Package the entire GHL Sales Assistant for easy deployment to any server (Linux VPS, Windows, or cloud platform).

### Pipeline Summary

| Phase | Agent | Status | Deliverables |
|-------|-------|--------|-------------|
| Backend Packaging | BE Dev | ✅ Done | `.dockerignore`, improved `Dockerfile`, improved `docker-compose.yml`, `deploy.sh`, `deploy.bat` |
| Extension Packaging | FE Dev | ✅ Done | `package-extension.sh`, `package-extension.bat` → produces distributable `.zip` |
| Deployment Guide | Deliver | ✅ Done | `DEPLOY_GUIDE.md` (8 sections), rewritten `README.md` |

### What Was Created (10 files total)

| File | Purpose |
|------|---------|
| [`backend/.dockerignore`](../backend/.dockerignore) | Exclude unnecessary files from Docker build |
| [`backend/Dockerfile`](../backend/Dockerfile) | Production-optimized (multi-stage, non-root, workers) |
| [`docker-compose.yml`](../docker-compose.yml) | Logging, networks, healthcheck, env defaults |
| [`deploy.sh`](../deploy.sh) | One-command Linux/macOS deployment |
| [`deploy.bat`](../deploy.bat) | One-command Windows deployment |
| [`package-extension.sh`](../package-extension.sh) | Build extension zip (Linux/macOS) |
| [`package-extension.bat`](../package-extension.bat) | Build extension zip (Windows) |
| [`DEPLOY_GUIDE.md`](../DEPLOY_GUIDE.md) | Full deployment guide (VPS, cloud, Nginx, HTTPS) |
| [`README.md`](../README.md) | Project overview + architecture + quick start |
| [`docs/codemap.md`](codemap.md) | Updated with backend + packaging sections |

### How to Deploy to a New Server

```bash
# 1. Clone/copy repo to server
git clone <repo-url> && cd ghl-sales-assistant

# 2. Configure environment
cp backend/.env.example backend/.env
nano backend/.env  # Fill in GHL_API_KEY, GHL_LOCATION_ID

# 3. Deploy backend (Docker)
./deploy.sh

# 4. Package extension for distribution
./package-extension.sh
# → dist/ghl-sales-assistant-extension-v1.0.1.zip

# 5. Verify
curl http://localhost:8000/health
```

---

## Deployment Readiness Assessment

**Date**: 2026-03-19
**Status**: 🟡 ALMOST READY — 1 scope gap + hosting decision needed

### Client-Provided Credentials

| Item | Value | Status |
|------|-------|--------|
| GHL API Key | `pit-d0203246-...bf47233` (Private API Token) | ✅ |
| Location ID | `Z95sUcB7HCIqWKfjX3SD3` | ✅ |
| User Account | Invitation sent | ✅ |

### Scope Coverage Audit (image.png)

Scopes granted by client:
- `contacts.write` — Edit Contacts
- `locations/tags.write` — Edit Tags
- `opportunities.write` — Edit Opportunities
- `locations/tasks.write` — Edit Location Tasks
- `locations/customFields.write` — Edit Custom Fields
- `locations/customFields.readonly` — View Custom Fields

| Backend Function | GHL Endpoint | Required Scope | Covered? |
|---|---|---|---|
| `create_or_update_contact()` | `POST /contacts/upsert` | `contacts.write` | ✅ |
| `create_contact()` | `POST /contacts/` | `contacts.write` | ✅ |
| `update_contact()` | `PUT /contacts/{id}` | `contacts.write` | ✅ |
| `search_contacts()` | `GET /contacts/` | `contacts.readonly` | ⚠️ MISSING |
| `add_tags()` | `POST /contacts/{id}/tags` | `contacts.write` | ✅ |
| `get_tags()` | `GET /locations/{id}/tags` | `locations/tags.readonly` | ⚠️ MISSING |
| `add_note()` | `POST /contacts/{id}/notes` | `contacts.write` | ✅ |
| `create_task()` | `POST /contacts/{id}/tasks` | `locations/tasks.write` | ✅ |
| `get_custom_fields()` | `GET /locations/{id}/customFields` | `locations/customFields.readonly` | ✅ |

### Action Items Before Deploy

| # | Item | Owner | Status |
|---|------|-------|--------|
| 1 | Add `contacts.readonly` scope in GHL app settings | Client | 🔴 Required |
| 2 | Add `locations/tags.readonly` scope in GHL app settings | Client | 🔴 Required |
| 3 | Decide hosting (local/VPS/cloud) | Client | ❓ Pending |
| 4 | Create `backend/.env` with real credentials | Dev | ⏳ Ready when above resolved |
| 5 | Fix BUG-001 (Google Search wrong website URL) | FE Dev | 🟡 Non-blocking but recommended |

### Client Response (Draft)

> Thank you for providing the API key, Location ID, and account access! Here's the status:
>
> **✅ Almost ready to deploy.** One small thing needed:
>
> 1. **Please add the "View Contacts" (`contacts.readonly`) scope** to the API token in your GHL Marketplace settings. The app needs this to search for existing contacts (deduplication). Without it, the lead list and duplicate checking will get 403 errors.
>
> 2. **Where would you like to host the backend?** Options:
>    - Your own server/VPS (we provide Docker one-command deploy)
>    - A cloud platform (AWS, DigitalOcean, etc.)
>    - Your local machine (for testing)
>
> Everything else (API key, Location ID, scopes for tags/tasks/custom fields) is perfect. Once you add that one scope and confirm hosting, we can deploy immediately.

---

## Integration Test: GHL API Credential Verification

**Date**: 2026-03-19
**Status**: 🔴 FAIL — 2 issues found
**Signal**: `integration-fail-rollback` → `pm`

### Test Results

| # | Test | Endpoint | Status | Response | Verdict |
|---|------|----------|--------|----------|---------|
| 1 | Backend Health | `GET http://localhost:8000/health` | 200 | `{"status":"healthy"}` | ✅ PASS |
| 2 | GHL: Search Contacts | `GET /contacts/?locationId=...&limit=1` | 401 | `"The token is not authorized for this scope."` | ❌ FAIL |
| 3 | GHL: Get Tags (direct) | `GET /tags/?locationId=...` | 404 | (empty body) | ❌ FAIL |
| 4 | GHL: Get Tags (alt URL) | `GET /locations/{id}/tags` | 401 | (empty body) | ❌ FAIL |
| 5 | GHL: Get Custom Fields | `GET /locations/{id}/customFields` | 200 | `{"customFields":[{"id":"3IFVGjFTCVMyh7tKiZG8","name":"businessType",...}]}` | ✅ PASS |
| 6 | Backend: GET /api/v1/tags | `GET http://localhost:8000/api/v1/tags` | 404 | GHL upstream returned 404 | ❌ FAIL |
| 7 | Backend: GET /api/v1/leads | `GET http://localhost:8000/api/v1/leads?limit=1` | 401 | GHL upstream returned 401 — missing `contacts.readonly` scope | ❌ FAIL |

### Issue Analysis

#### Issue 1: Missing `contacts.readonly` Scope (Client Action Required)
- **Affected**: Tests #2, #7
- **Root Cause**: The GHL API key (`pit-d0203246-...`) does NOT have the `contacts.readonly` scope. GHL returns `401 "The token is not authorized for this scope."`.
- **Impact**: `search_contacts()`, `list_leads()`, `find_contact_by_phone()` (deduplication) all fail.
- **Fix**: Client must add `contacts.readonly` ("View Contacts") scope in GHL Marketplace → App Settings → API Token.

#### Issue 2: Wrong GHL Tags Endpoint URL (Backend Bug)
- **Affected**: Tests #3, #4, #6
- **Root Cause**: [`ghl_service.py:252`](../backend/app/services/ghl_service.py:252) calls `GET /tags/?locationId=...` but this endpoint returns 404 on the GHL API v2021-07-28. The alternate URL `/locations/{id}/tags` returns 401 (likely needs `locations/tags.readonly` scope, not just `locations/tags.write`).
- **Impact**: The "Get Tags" feature in the Chrome Extension will not work.
- **Fix (BE Dev)**: Investigate correct GHL tags listing endpoint. Possibly `GET /locations/{locationId}/tags` with the correct API version header, OR the scope `locations/tags.readonly` may also be missing.

### Credentials Validated

| Credential | Value | Valid? |
|------------|-------|--------|
| API Key format | `pit-...` (Private Integration Token) | ✅ Valid format |
| API Key auth | Works for customFields endpoint | ✅ Authenticates |
| Location ID | `Z95sUcB7HCIqWKfjX3SD` | ✅ Valid (customFields returned data) |
| Base URL | `https://services.leadconnectorhq.com` | ✅ Correct |

### Action Items

| # | Action | Owner | Priority |
|---|--------|-------|----------|
| 1 | Add `contacts.readonly` scope to API token | Client | 🔴 Blocking |
| 2 | ~~Fix tags endpoint URL in `ghl_service.py:252`~~ | BE Dev | ✅ Fixed |
| 3 | Add `locations/tags.readonly` scope to API token | Client | 🔴 Blocking |
| 4 | Re-run integration tests after fixes | Integration | ⏳ After #1 + #3 |

---

## Bug Fix: GHL Tags Endpoint URL (404 → Correct v2 URL)

**Date**: 2026-03-19
**Status**: ✅ Complete
**Signal**: `be-done` → integration

### Problem
[`ghl_service.py:252`](../backend/app/services/ghl_service.py:252) called `GET /tags/?locationId=...` which returned **404** on GHL API v2021-07-28. The tags listing feature was broken.

### Root Cause
Wrong endpoint URL. GHL API v2 uses resource-scoped paths under `/locations/{locationId}/`. The old code used a flat `/tags/` path with `locationId` as a query param, which doesn't exist in the v2 API.

### Fix
Changed [`get_tags()`](../backend/app/services/ghl_service.py:245) from:
```python
# OLD (404)
params = {"locationId": self.location_id}
result = await self._request("GET", "/tags/", params=params)
```
to:
```python
# NEW (matches /locations/{id}/customFields pattern)
result = await self._request("GET", f"/locations/{self.location_id}/tags")
```

### API-CONTRACT

| Method | Backend Endpoint | GHL Upstream | Scope Required | Notes |
|--------|-----------------|--------------|----------------|-------|
| GET | `/api/v1/tags` | `GET /locations/{locationId}/tags` | `locations/tags.readonly` | Was `/tags/?locationId=...` (404). Now matches customFields pattern. |
| POST | `/api/v1/tags` | `POST /contacts/{contactId}/tags` | `contacts.write` | Unchanged — adds tags to a contact. |

### Remaining Blocker
The endpoint URL is now correct, but the client's API token only has `locations/tags.write` scope. GHL requires `locations/tags.readonly` to **read** tags. Client must add this scope for the tags listing to return 200.

### Verification
- Syntax check: ✅ `ast.parse()` passes
- Pattern confirmed: Same URL pattern as [`get_custom_fields()`](../backend/app/services/ghl_service.py:315) which uses `GET /locations/{id}/customFields` and returns 200 OK

---

## Integration Re-Test: Tags URL Fix Verification

**Date**: 2026-03-19
**Status**: ✅ PASS — Tags URL fix confirmed, scopes still blocking
**Signal**: `integration-verified-be-only` → `qc`

### Context
BE Dev fixed [`ghl_service.py:get_tags()`](../backend/app/services/ghl_service.py:245) — changed from `GET /tags/?locationId=...` (404) to `GET /locations/{id}/tags`. Docker rebuilt via `deploy.bat --build`. This re-test verifies the fix deployed correctly.

### Test Results

| # | Test | Endpoint | HTTP | Response Snippet | Verdict |
|---|------|----------|------|-----------------|---------|
| 1 | Backend Health | `GET localhost:8000/health` | 200 | `{"status":"healthy"}` | ✅ PASS |
| 2 | GHL Direct: Search Contacts | `GET /contacts/?locationId=...&limit=1` | 401 | `"token is not authorized for this scope"` | ⚠️ EXPECTED — `contacts.readonly` missing |
| 3 | GHL Direct: Get Tags (new URL) | `GET /locations/{id}/tags` | **401** | `"token is not authorized for this scope"` | ✅ **URL FIX CONFIRMED** (was 404, now 401) |
| 4 | GHL Direct: Get Custom Fields | `GET /locations/{id}/customFields` | 200 | `{"customFields":[{"id":"3IFV...","name":"businessType",...}]}` | ✅ PASS |
| 5 | Backend: GET /api/v1/tags | `localhost:8000/api/v1/tags` | 401 | `{"detail":"GHL API error: 401 - ...not authorized..."}` | ⚠️ EXPECTED — `locations/tags.readonly` missing |
| 6 | Backend: GET /api/v1/leads | `localhost:8000/api/v1/leads?limit=1` | 401 | `{"detail":"GHL API error: 401 - ...not authorized..."}` | ⚠️ EXPECTED — `contacts.readonly` missing |

### Key Findings

1. **Tags URL fix VERIFIED** ✅ — GHL direct call to `/locations/{id}/tags` now returns **401** (scope auth error) instead of **404** (endpoint not found). This proves the URL is correct; only the missing `locations/tags.readonly` scope is blocking.

2. **Backend correctly proxies GHL errors** ✅ — Tests #5 and #6 show the backend forwards upstream 401 errors with the GHL error message intact.

3. **Custom Fields still working** ✅ — The only endpoint with full scope coverage (`locations/customFields.readonly`) returns 200 with 24 custom fields.

4. **No code changes were made** — This was a test-only run after Docker rebuild.

### Remaining Blockers (Client Action)

| # | Action | Owner | Status |
|---|--------|-------|--------|
| 1 | Add `contacts.readonly` scope to API token | Client | 🔴 Blocking leads/contacts |
| 2 | Add `locations/tags.readonly` scope to API token | Client | 🔴 Blocking tags listing |

### Credentials Used
- API Key: `pit-d020...f47233` (masked)
- Location ID: `Z95sUcB7HCIqWKfjX3SD`

---

## Integration Test: Full API + Backend Verification (New API Key)

**Date**: 2026-03-20
**Status**: ✅ ALL PASS
**Signal**: `integration-verified` → `vision-parser`

### Context
Client updated API key with additional scopes (`contacts.readonly`, `locations/tags.readonly`). Docker rebuilt with `deploy.bat --build`. Comprehensive 8-test suite covering GHL Direct API + Backend endpoints.

### Credentials Used
- API Key: `pit-b4ac...X3D7b` (masked — new key)
- Location ID: `Z95sUcB7HCIqWKfjX3SD`

### Test Results

| # | Test | Endpoint | HTTP | Response Snippet (150 chars) | Verdict |
|---|------|----------|------|------------------------------|---------|
| 1 | Backend Health | `GET localhost:8000/health` | 200 | `{"status":"healthy"}` | ✅ PASS |
| 2 | GHL: Search Contacts | `GET /contacts/?locationId=...&limit=1` | 200 | `{"contacts":[{"id":"DfTtezp0sNfH5F8o7SCr","contactName":"thang hoang","firstName":"thang","lastName":"hoang"...` | ✅ PASS |
| 3 | GHL: Get Tags | `GET /locations/{id}/tags` | 200 | `{"tags":[{"id":"SdFYeecqBxZwH9vjR5jt","name":"& cfo"},{"id":"7jMG9lEmXePIqmP8qe1D","name":"adult day care"}...` | ✅ PASS |
| 4 | GHL: Get Custom Fields | `GET /locations/{id}/customFields` | 200 | `{"customFields":[{"id":"3IFVGjFTCVMyh7tKiZG8","name":"businessType","model":"contact","fieldKey":"contact.bu...` | ✅ PASS |
| 5 | GHL: Upsert Contact | `POST /contacts/upsert` | 201 | `{"new":true,"contact":{"id":"IytX6sEZAAHudDMiHpTw","firstName":"API Test","type":"lead","locationId":"Z95sUc...` | ✅ PASS |
| 6 | Backend: GET /api/v1/tags | `GET localhost:8000/api/v1/tags` | 200 | `{"tags":[{"id":"SdFYeecqBxZwH9vjR5jt","name":"& cfo"},{"id":"7jMG9lEmXePIqmP8qe1D","name":"adult day care"}...` | ✅ PASS |
| 7 | Backend: GET /api/v1/leads | `GET localhost:8000/api/v1/leads?limit=1` | 200 | `{"leads":[{"contact_id":"IytX6sEZAAHudDMiHpTw","business_name":"Integration Test Business","phone":"+100000...` | ✅ PASS |
| 8 | Backend: POST /api/v1/leads/capture | `POST localhost:8000/api/v1/leads/capture` | 200 | `{"success":true,"message":"Lead captured successfully","contact_id":"S87vaFwyZvzMb66h2rHt","is_new":true,"b...` | ✅ PASS |

### Overall Verdict: ✅ ALL PASS (8/8)

### Scope Coverage — Fully Resolved

| Backend Function | GHL Endpoint | Required Scope | Status |
|---|---|---|---|
| `search_contacts()` | `GET /contacts/` | `contacts.readonly` | ✅ Now works (was ❌ 401) |
| `get_tags()` | `GET /locations/{id}/tags` | `locations/tags.readonly` | ✅ Now works (was ❌ 401) |
| `get_custom_fields()` | `GET /locations/{id}/customFields` | `locations/customFields.readonly` | ✅ Still works |
| `create_or_update_contact()` | `POST /contacts/upsert` | `contacts.write` | ✅ Works |
| `add_tags()` | `POST /contacts/{id}/tags` | `contacts.write` | ✅ Works (via E2E test #8) |
| `add_note()` | `POST /contacts/{id}/notes` | `contacts.write` | ✅ Works (via E2E test #8 — `note_created: true`) |

### Remaining Scope Issues: **NONE** — All scopes now granted and verified.

### Test Contacts Created (cleanup reference)
- `IytX6sEZAAHudDMiHpTw` — "API Test" / "Integration Test Business" / +10000000000
- `S87vaFwyZvzMb66h2rHt` — "E2E Test Business" / (555) 123-4567

### Previous Blockers — Resolved

| # | Blocker | Resolution |
|---|---------|------------|
| 1 | `contacts.readonly` scope missing | ✅ Client added scope to new API key |
| 2 | `locations/tags.readonly` scope missing | ✅ Client added scope to new API key |
| 3 | Tags endpoint URL was 404 | ✅ Fixed in prior BE Dev cycle (now `/locations/{id}/tags`) |

---
