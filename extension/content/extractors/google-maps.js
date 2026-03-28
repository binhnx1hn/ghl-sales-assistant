/**
 * Google Maps Data Extractor
 *
 * Extracts business information from Google Maps place details panel.
 */

const GoogleMapsExtractor = {
  /**
   * Check if the current page is Google Maps.
   * @returns {boolean}
   */
  isMatch() {
    return (
      window.location.hostname.includes("google.com") &&
      (window.location.pathname.startsWith("/maps") ||
        window.location.hostname === "maps.google.com")
    );
  },

  /**
   * Extract business data from the Google Maps place detail panel.
   * When a user clicks on a business in Maps, a side panel appears with details.
   *
   * @param {HTMLElement} targetElement - The element the user clicked near
   * @returns {Object|null} Extracted business data or null
   */
  extract(targetElement) {
    // Try the place details panel first
    const panelResult = this._extractFromPlacePanel();
    if (panelResult) return panelResult;

    // Try from the search results list in Maps
    const listResult = this._extractFromSearchList(targetElement);
    if (listResult) return listResult;

    return null;
  },

  /**
   * Get all visible business listings on Google Maps.
   * @returns {Array<HTMLElement>}
   */
  getListings() {
    const listings = [];

    // Search result items in the left panel
    document.querySelectorAll("[data-result-index], .Nv2PK").forEach((el) => {
      listings.push(el);
    });

    // Direct place page (e.g. /maps/place/...) — the whole place panel is the "listing"
    if (listings.length === 0 && this._isDirectPlacePage()) {
      const placePanel =
        document.querySelector("div[role='main'] div.m6QErb") ||
        document.querySelector("div[role='main']") ||
        document.querySelector("#QA0Szd");
      if (placePanel) {
        listings.push(placePanel);
      }
    }

    return listings;
  },

  /**
   * Check if we are on a direct place page (not search results).
   * @returns {boolean}
   */
  _isDirectPlacePage() {
    return (
      window.location.pathname.includes("/maps/place/") &&
      !!document.querySelector("h1.DUwDvf, h1.fontHeadlineLarge")
    );
  },

  /**
   * Extract from the main place details panel (right side or expanded view).
   * @returns {Object|null}
   */
  _extractFromPlacePanel() {
    const data = {
      businessName: "",
      phone: "",
      website: "",
      address: "",
      city: "",
      state: "",
      rating: "",
      category: "",
      sourceUrl: window.location.href,
      sourceType: GHL_ASSISTANT.SOURCE_TYPES.GOOGLE_MAPS,
    };

    // Business name - main heading in place panel
    const nameEl =
      document.querySelector("h1.DUwDvf") || // Main place name
      document.querySelector("h1.fontHeadlineLarge") ||
      document.querySelector("[data-item-id='title'] h1") ||
      document.querySelector(".tAiQpe h1");

    if (!nameEl) return null;
    data.businessName = nameEl.textContent.trim();

    // Category (e.g., "Nursing home", "Assisted living facility")
    const categoryEl =
      document.querySelector("button[jsaction*='category'] .DkEaL") ||
      document.querySelector(".skqShb .YhemCb") ||
      document.querySelector("[jsaction*='pane.rating.category']");
    if (categoryEl) {
      data.category = categoryEl.textContent.trim();
    }

    // Rating
    const ratingEl =
      document.querySelector("div.F7nice span[aria-hidden='true']") ||
      document.querySelector("span.ceNzKf") ||
      document.querySelector(".fontDisplayLarge");
    if (ratingEl) {
      data.rating = ratingEl.textContent.trim();
    }

    // Address - first try the explicit data-item-id="address" button (works
    // for all locales including Vietnamese, Japanese, etc.)
    const addressBtn = document.querySelector(
      "button[data-item-id='address'], [data-item-id='address']"
    );
    if (addressBtn) {
      const addrEl = addressBtn.querySelector(".Io6YTe, .rogA2c div");
      const addrText = (addrEl || addressBtn).textContent.trim();
      if (addrText && !this._looksLikePlusCode(addrText)) {
        data.address = addrText;
        const parts = this._parseCityState(addrText);
        data.city = parts.city;
        data.state = parts.state;
      }
    }

    // Fallback: scan all info items for address / phone (covers older layouts
    // and oloc* plus-code containers).
    const infoItems = document.querySelectorAll(
      "[data-item-id] .Io6YTe, button[data-item-id] .rogA2c"
    );

    // On some Google Maps layouts, `oloc*` can contain a plus code like
    // "R365+JQ ...", which is NOT the street address we want in GHL.
    // We capture it as a fallback, but we prefer a real street address.
    let plusCodeCandidate = "";

    infoItems.forEach((item) => {
      const parentButton = item.closest("[data-item-id]");
      if (!parentButton) return;

      const itemId = parentButton.getAttribute("data-item-id") || "";
      const text = item.textContent.trim();

      const looksLikePlusCode = this._looksLikePlusCode(text);
      const looksLikeStreetAddress = this._looksLikeStreetAddress(text);

      if (itemId.includes("address") || itemId.startsWith("oloc")) {
        // If we already have a good address from the explicit button, skip.
        if (data.address) return;

        if (looksLikeStreetAddress) {
          data.address = text;
          const parts = this._parseCityState(text);
          data.city = parts.city;
          data.state = parts.state;
          return;
        }

        // Store plus code as fallback only.
        if (looksLikePlusCode) {
          if (!plusCodeCandidate) plusCodeCandidate = text;
          return;
        }
      } else if (itemId.includes("phone") || itemId.startsWith("phone")) {
        data.phone = text;
      }
    });

    if (!data.address && plusCodeCandidate) {
      data.address = plusCodeCandidate;
      const parts = this._parseCityState(plusCodeCandidate);
      data.city = parts.city;
      data.state = parts.state;
    }

    // Alternative phone extraction
    if (!data.phone) {
      const phoneButton = document.querySelector(
        "button[data-tooltip*='phone'], button[aria-label*='Phone'], " +
        "[data-item-id*='phone'] .Io6YTe"
      );
      if (phoneButton) {
        const phoneText =
          phoneButton.querySelector(".Io6YTe, .rogA2c")?.textContent ||
          phoneButton.textContent;
        const phoneMatch = phoneText.match(
          /\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}/
        );
        if (phoneMatch) {
          data.phone = phoneMatch[0];
        }
      }
    }

    // Website
    const websiteButton = document.querySelector(
      "a[data-item-id='authority'], a[data-item-id*='website'], " +
      "[data-tooltip*='website'] a"
    );
    if (websiteButton) {
      data.website = websiteButton.href;
    }

    // Alternative website extraction
    if (!data.website) {
      const websiteLink = document.querySelector(
        "a.CsEnBe[aria-label*='Website']"
      );
      if (websiteLink) {
        data.website = websiteLink.href;
      }
    }

    return data.businessName ? data : null;
  },

  /**
   * Extract from a search result list item in the Maps left panel.
   * @param {HTMLElement} element
   * @returns {Object|null}
   */
  _extractFromSearchList(element) {
    const container =
      element.closest("[data-result-index]") ||
      element.closest(".Nv2PK") ||
      element.closest("div[jsaction*='mouseover:pane']");

    if (!container) return null;

    const data = {
      businessName: "",
      phone: "",
      website: "",
      address: "",
      city: "",
      state: "",
      rating: "",
      sourceUrl: window.location.href,
      sourceType: GHL_ASSISTANT.SOURCE_TYPES.GOOGLE_MAPS,
    };

    // Name
    const nameEl =
      container.querySelector(".qBF1Pd") || // Search result name
      container.querySelector(".fontHeadlineSmall") ||
      container.querySelector("a .lhCR5d");
    if (nameEl) {
      data.businessName = nameEl.textContent.trim();
    }

    // Rating
    const ratingEl = container.querySelector(
      "span.MW4etd, span[aria-hidden='true']"
    );
    if (ratingEl) {
      data.rating = ratingEl.textContent.trim();
    }

    // Address and phone from detail lines
    const detailLines = container.querySelectorAll(
      ".W4Efsd .W4Efsd span:not(.UY7F9)"
    );
    detailLines.forEach((line) => {
      const text = line.textContent.trim();
      // Check if it's a phone number
      if (/\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}/.test(text)) {
        data.phone = text.match(/\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}/)[0];
      }
      // Check if it looks like an address (contains street indicators)
      else if (
        /\d+\s+[A-Za-z]/.test(text) ||
        /\b(St|Ave|Blvd|Dr|Rd|Ln|Way|Ct)\b/i.test(text)
      ) {
        data.address = text;
        const parts = this._parseCityState(text);
        data.city = parts.city;
        data.state = parts.state;
      }
    });

    // Website from the action buttons
    const websiteLink = container.querySelector(
      "a[href*='http']:not([href*='google'])"
    );
    if (websiteLink) {
      data.website = websiteLink.href;
    }

    return data.businessName ? data : null;
  },

  /**
   * Parse city and state from an address string.
   * @param {string} address
   * @returns {{city: string, state: string}}
   */
  _parseCityState(address) {
    if (!address) return { city: "", state: "" };

    const stateMatch = address.match(
      /,\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*\d{0,5}/
    );
    if (stateMatch) {
      return { city: stateMatch[1].trim(), state: stateMatch[2] };
    }

    const simpleMatch = address.match(/,\s*([^,]+),\s*([A-Z]{2})\s*$/);
    if (simpleMatch) {
      return { city: simpleMatch[1].trim(), state: simpleMatch[2] };
    }

    return { city: "", state: "" };
  },

  /**
   * Basic heuristic: Open Location Code (plus code) often looks like
   * "R365+JQ" or "9F5R+8M" and should not be used as a street address.
   * @param {string} text
   * @returns {boolean}
   */
  _looksLikePlusCode(text) {
    if (!text) return false;
    // Example: "R365+JQ" (4+2 chars around '+'), sometimes lowercased.
    return /\b[A-Z0-9]{3,4}\+[A-Z0-9]{2,4}\b/i.test(text);
  },

  /**
   * Basic heuristic to detect a "real" US street address.
   * We want to avoid saving plus codes or partial locality strings.
   * @param {string} text
   * @returns {boolean}
   */
  _looksLikeStreetAddress(text) {
    if (!text) return false;
    const t = String(text).replace(/\s+/g, " ").trim();
    if (!t) return false;
    if (this._looksLikePlusCode(t)) return false;

    // Typical: "1440 S Euclid St, Anaheim, CA 92802"
    const hasHouseNumber = /^\d{1,6}\b/.test(t);
    const hasStreetAbbrev =
      /\b(St|Street|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Rd|Road|Ln|Lane|Way|Ct|Court|Pl|Place|Ter|Terrace)\b/i.test(t);
    const hasStateZip = /,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?\b/.test(t);

    return (hasHouseNumber && hasStreetAbbrev) || hasStateZip;
  },
};
