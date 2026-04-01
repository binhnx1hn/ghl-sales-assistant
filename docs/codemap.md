# Codemap

## Frontend — Chrome Extension (`extension/`)

### Architecture
- **Type**: Chrome Manifest V3 Extension (vanilla JS, no bundler)
- **Entry**: [`manifest.json`](../extension/manifest.json) → content scripts injected on Google, Yelp, Yellow Pages

### Content Scripts (`extension/content/`)

| File | Purpose | Key Exports |
|------|---------|-------------|
| [`content.js`](../extension/content/content.js) | Main entry — init, attach listeners, auto-show on detail pages | `init()`, `autoShowOnPlacePage()`, `autoShowOnYelpBizPage()`, `attachListingListeners()`, `observeDOMChanges()` |
| [`components/floating-button.js`](../extension/content/components/floating-button.js) | "⚡ Send to GHL" floating button — positioning + capture trigger | `FloatingButton { init, show, hide }` |
| [`components/review-popup.js`](../extension/content/components/review-popup.js) | Review/edit popup before sending to GHL. Phase 2A: social profile enrichment with checkbox-list UI, `checkedPlatforms` intent state, `_attachPickerHandlers` helper, candidate picker flow. Phase 2B: `showOutreachQueue()` panel with classify step, auto-load queue, per-item copy/edit/open, mark-all-sent; `_attachOutreachQueueHandlers()`; `_tierResult` + `_queueItems` state. | `ReviewPopup { show, showOutreachQueue }` |
| [`extractors/google-search.js`](../extension/content/extractors/google-search.js) | Google Search result extractor | `GoogleSearchExtractor { isMatch, extract, getListings }` |
| [`extractors/google-maps.js`](../extension/content/extractors/google-maps.js) | Google Maps extractor (search + place pages) | `GoogleMapsExtractor { isMatch, extract, getListings }` |
| [`extractors/generic.js`](../extension/content/extractors/generic.js) | Yelp, Yellow Pages, Schema.org fallback extractor | `GenericExtractor { isMatch, extract, getListings }` |
| [`content.css`](../extension/content/content.css) | Styles for floating button, popup, toast | — |

### Utils (`extension/utils/`)

| File | Purpose |
|------|---------|
| [`constants.js`](../extension/utils/constants.js) | `GHL_ASSISTANT` namespace, CSS prefix, source types |
| [`storage.js`](../extension/utils/storage.js) | Chrome storage wrapper for settings |
| [`api.js`](../extension/utils/api.js) | Backend API client. Phase 2B: added `classifyLead()`, `createOutreachQueue()`, `getOutreachQueue()`, `draftOutreach()`, `updateQueueItem()`; `_request()` now supports PATCH. |

### Popup & Options

| File | Purpose |
|------|---------|
| [`popup/popup.html`](../extension/popup/popup.html) | Extension popup UI |
| [`popup/popup.js`](../extension/popup/popup.js) | Popup logic |
| [`options/options.html`](../extension/options/options.html) | Settings page |
| [`options/options.js`](../extension/options/options.js) | Settings logic |

### Supported Sites & Detection Flow

```
URL matched by manifest.json
  → content.js init() (1500ms delay)
    → FloatingButton.init()
    → attachListingListeners()  ← hover on search result cards
    → observeDOMChanges()       ← re-scan on SPA navigation
    → autoShowOnPlacePage()     ← Google Maps /maps/place/ detail
    → autoShowOnYelpBizPage()   ← Yelp /biz/ detail pages
```

### FloatingButton Positioning Logic

| Page Type | Detection | Position Strategy |
|-----------|-----------|-------------------|
| Google Maps place page | `/maps/place/` + `h1.DUwDvf` | Right of info panel |
| Yelp `/biz/` detail page | `yelp.com` + `/biz/` path | Top-right of content (fixed, right: 20px) |
| Search result cards | Default | Right of hovered listing |

### Extension Packaging

| File | Purpose |
|------|---------|
| [`package-extension.sh`](../package-extension.sh) | Linux/macOS packaging script — reads version from `manifest.json`, copies to `dist/`, excludes `.svg`/`.md`/`.git`/`node_modules`, creates `.zip` |
| [`package-extension.bat`](../package-extension.bat) | Windows equivalent using PowerShell `Compress-Archive` |

**Output**: `dist/ghl-sales-assistant-extension-v{version}.zip` (22 files, ~32 KB)

---

## Backend — FastAPI API (`backend/`)

### Architecture
- **Type**: Python FastAPI REST API
- **Entry**: [`app/main.py`](../backend/app/main.py) → FastAPI app with CORS, health endpoint, v1 router
- **Config**: [`app/config.py`](../backend/app/config.py) → Pydantic Settings from `.env`

### API Layer (`backend/app/api/v1/`)

| File | Purpose | Key Endpoints |
|------|---------|---------------|
| [`router.py`](../backend/app/api/v1/router.py) | V1 router aggregator | Mounts leads + tags routers |
| [`leads.py`](../backend/app/api/v1/leads.py) | Lead CRUD via GHL API. Phase 2A: `/enrich`, `/save-profiles`, `/draft-email`. Phase 2B: `/classify`, `/draft-outreach`, `/outreach-queue` (POST/GET/PATCH). | `POST /capture`, `GET /leads`, `POST /enrich`, `POST /save-profiles`, `POST /draft-email`, `POST /classify`, `POST /draft-outreach`, `POST /outreach-queue`, `GET /outreach-queue/{id}`, `PATCH /outreach-queue/{item_id}` |
| [`tags.py`](../backend/app/api/v1/tags.py) | Tag management via GHL API | `GET /tags`, `POST /tags` |

### Webhook Layer (`backend/app/api/webhooks/`) — Phase 3

| File | Purpose | Key Endpoints |
|------|---------|---------------|
| [`webhooks/__init__.py`](../backend/app/api/webhooks/__init__.py) | Empty package init | — |
| [`webhooks/ghl.py`](../backend/app/api/webhooks/ghl.py) | GHL inbound webhook receiver. Mounted at `/webhooks` (separate from `/api/v1`). Optional `X-Webhook-Secret` HMAC-safe check. Filter chain: event type → config guard → stage ID → contactId. Enqueues `_run_hot_lead_enrichment()` background task (8-step: fetch contact → notes → social profiles → save profiles → draft email → save note). | `POST /webhooks/ghl/hot-lead` |

### Models (`backend/app/models/`)

| File | Purpose |
|------|---------|
| [`lead.py`](../backend/app/models/lead.py) | `LeadCaptureRequest`, `LeadCaptureResponse`, `LeadListResponse` |
| [`enrich.py`](../backend/app/models/enrich.py) | Phase 2A: `EnrichRequest`, `EnrichResponse`, `SocialProfiles`, `DraftEmailRequest`, `DraftEmailResponse` |
| [`phase2b.py`](../backend/app/models/phase2b.py) | Phase 2B: `ClassifyRequest/Response`, `DraftOutreachRequest/Response`, `OutreachQueueItem`, `CreateOutreachQueueRequest/Response`, `GetOutreachQueueResponse`, `UpdateQueueItemRequest/Response` |

### Services (`backend/app/services/`)

| File | Purpose |
|------|---------|
| [`ghl_service.py`](../backend/app/services/ghl_service.py) | HTTP client for GoHighLevel API v2 (2021-07-28). Phase 2B adds: `add_tag()`, `trigger_workflow()`, `get_notes()`, `update_note()`. |
| [`lead_service.py`](../backend/app/services/lead_service.py) | Lead business logic layer |
| [`social_research_service.py`](../backend/app/services/social_research_service.py) | Phase 2A: Serper.dev social profile finder |
| [`ai_email_drafter_service.py`](../backend/app/services/ai_email_drafter_service.py) | Phase 2A: GPT-4o-mini email drafter |
| [`lead_classifier_service.py`](../backend/app/services/lead_classifier_service.py) | Phase 2B: GPT-4o-mini lead tier classifier (hot/warm/cold), applies GHL tag, optionally triggers GHL workflow |
| [`outreach_drafter_service.py`](../backend/app/services/outreach_drafter_service.py) | Phase 2B: GPT-4o-mini per-platform outreach message drafter with char limits (linkedin/inmail 2000, connection_request 300, facebook/page_dm 1000, instagram/dm 1000, tiktok/dm 500) |
| [`outreach_queue_service.py`](../backend/app/services/outreach_queue_service.py) | Phase 2B: Outreach queue CRUD via GHL Notes — create, get, update status; serializes items with `[OUTREACH_QUEUE]` prefix |

### Utils (`backend/app/utils/`)

| File | Purpose |
|------|---------|
| [`exceptions.py`](../backend/app/utils/exceptions.py) | Custom exception classes |

### Deployment & Packaging

| File | Purpose |
|------|---------|
| [`Dockerfile`](../backend/Dockerfile) | Multi-stage build, non-root user, `WORKERS` env var |
| [`.dockerignore`](../backend/.dockerignore) | Excludes `__pycache__`, `.env`, `venv`, `tests` from build context |
| [`docker-compose.yml`](../docker-compose.yml) | Single-service compose with healthcheck, logging (json-file 10m×3), `ghl-network` |
| [`deploy.sh`](../deploy.sh) | Linux/macOS one-command deploy script (`--build`, `--restart`, `--logs`, `--stop`) |
| [`deploy.bat`](../deploy.bat) | Windows equivalent deploy script |
| [`.env.example`](../backend/.env.example) | Template for required environment variables |
