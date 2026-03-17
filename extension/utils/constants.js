/**
 * Shared constants for the GHL Sales Assistant Chrome Extension.
 */

const GHL_ASSISTANT = {
  // Backend API URL (configurable via options page)
  API_BASE_URL: "http://localhost:8000/api/v1",

  // Source type identifiers
  SOURCE_TYPES: {
    GOOGLE_SEARCH: "google_search",
    GOOGLE_MAPS: "google_maps",
    YELP: "yelp",
    YELLOW_PAGES: "yellow_pages",
    DIRECTORY: "directory",
    OTHER: "other",
  },

  // Default tags for new leads
  DEFAULT_TAGS: ["New Lead"],

  // Predefined tag options for quick selection
  TAG_OPTIONS: [
    "New Lead",
    "Nursing Home",
    "Assisted Living",
    "Senior Care",
    "Called",
    "Need Email",
    "Follow Up",
    "Hot Lead",
    "Not Interested",
  ],

  // CSS class prefix to avoid conflicts with page styles
  CSS_PREFIX: "ghl-sa",

  // Storage keys
  STORAGE_KEYS: {
    API_URL: "ghl_api_url",
    DEFAULT_TAGS: "ghl_default_tags",
    DEFAULT_MARKET: "ghl_default_market",
    LAST_CAPTURED: "ghl_last_captured",
  },
};
