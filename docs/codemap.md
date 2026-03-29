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
| [`components/review-popup.js`](../extension/content/components/review-popup.js) | Review/edit popup before sending to GHL. Phase 2: social profile enrichment with checkbox-list UI, `checkedPlatforms` intent state, `_attachPickerHandlers` helper, candidate picker flow. | `ReviewPopup { show }` |
| [`extractors/google-search.js`](../extension/content/extractors/google-search.js) | Google Search result extractor | `GoogleSearchExtractor { isMatch, extract, getListings }` |
| [`extractors/google-maps.js`](../extension/content/extractors/google-maps.js) | Google Maps extractor (search + place pages) | `GoogleMapsExtractor { isMatch, extract, getListings }` |
| [`extractors/generic.js`](../extension/content/extractors/generic.js) | Yelp, Yellow Pages, Schema.org fallback extractor | `GenericExtractor { isMatch, extract, getListings }` |
| [`content.css`](../extension/content/content.css) | Styles for floating button, popup, toast | — |

### Utils (`extension/utils/`)

| File | Purpose |
|------|---------|
| [`constants.js`](../extension/utils/constants.js) | `GHL_ASSISTANT` namespace, CSS prefix, source types |
| [`storage.js`](../extension/utils/storage.js) | Chrome storage wrapper for settings |
| [`api.js`](../extension/utils/api.js) | Backend API client for lead submission |

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
| [`leads.py`](../backend/app/api/v1/leads.py) | Lead CRUD via GHL API | `POST /leads`, `GET /leads/{id}` |
| [`tags.py`](../backend/app/api/v1/tags.py) | Tag management via GHL API | `GET /tags`, `POST /tags` |

### Services (`backend/app/services/`)

| File | Purpose |
|------|---------|
| [`ghl_service.py`](../backend/app/services/ghl_service.py) | HTTP client for GoHighLevel API v2 (2021-07-28). Endpoints: `/contacts/upsert`, `/contacts/{id}/tags`, `/locations/{id}/tags`, `/locations/{id}/customFields`, `/contacts/{id}/notes`, `/contacts/{id}/tasks`. |
| [`lead_service.py`](../backend/app/services/lead_service.py) | Lead business logic layer |

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
