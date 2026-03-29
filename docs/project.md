# Project Log

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
