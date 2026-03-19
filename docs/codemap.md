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
| [`components/review-popup.js`](../extension/content/components/review-popup.js) | Review/edit popup before sending to GHL | `ReviewPopup { show }` |
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
