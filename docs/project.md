# Project Log

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
