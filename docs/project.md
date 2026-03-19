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
