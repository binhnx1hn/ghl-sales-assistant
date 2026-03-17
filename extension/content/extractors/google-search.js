/**
 * Google Search Results Data Extractor
 *
 * Extracts business information from Google Search result pages,
 * including the local pack (map results) and knowledge panel.
 */

const GoogleSearchExtractor = {
  /**
   * Check if the current page is a Google Search results page.
   * @returns {boolean}
   */
  isMatch() {
    return (
      window.location.hostname.includes("google.com") &&
      window.location.pathname === "/search"
    );
  },

  /**
   * Extract business data from a clicked/selected element on Google Search.
   * Traverses up from the target element to find the parent business listing container.
   *
   * @param {HTMLElement} targetElement - The element the user clicked near
   * @returns {Object|null} Extracted business data or null if not found
   */
  extract(targetElement) {
    // Try to extract from local pack (map results)
    const localResult = this._extractFromLocalPack(targetElement);
    if (localResult) return localResult;

    // Try to extract from knowledge panel (right sidebar)
    const knowledgeResult = this._extractFromKnowledgePanel();
    if (knowledgeResult) return knowledgeResult;

    // Try to extract from organic results with business info
    const organicResult = this._extractFromOrganicResult(targetElement);
    if (organicResult) return organicResult;

    return null;
  },

  /**
   * Get all visible business listings on the page for highlighting.
   * @returns {Array<HTMLElement>} List of business listing DOM elements
   */
  getListings() {
    const listings = [];

    // Local pack listings (map results)
    document.querySelectorAll("[data-cid]").forEach((el) => {
      listings.push(el);
    });

    // Knowledge panel
    const knowledgePanel = document.querySelector("[data-attrid='title']");
    if (knowledgePanel) {
      const panel = knowledgePanel.closest(".kp-wholepage, .knowledge-panel, .liYKde");
      if (panel) listings.push(panel);
    }

    return listings;
  },

  /**
   * Extract business data from a local pack (map) result.
   * @param {HTMLElement} element
   * @returns {Object|null}
   */
  _extractFromLocalPack(element) {
    // Find the local result container
    const container =
      element.closest("[data-cid]") ||
      element.closest(".VkpGBb") ||
      element.closest("[jscontroller]");

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
      sourceType: GHL_ASSISTANT.SOURCE_TYPES.GOOGLE_SEARCH,
    };

    // Business name - try multiple selectors
    const nameEl =
      container.querySelector(".OSrXXb") || // Local pack name
      container.querySelector("[data-attrid='title'] span") ||
      container.querySelector(".dbg0pd") ||
      container.querySelector("span.czHgge") ||
      container.querySelector("a .lhCR5d") ||
      container.querySelector("div[role='heading']");

    if (nameEl) {
      data.businessName = nameEl.textContent.trim();
    }

    // Address
    const addressEl =
      container.querySelector(".rllt__details div:nth-child(2)") ||
      container.querySelector("[data-attrid='kc:/location/location:address'] .LrzXr");

    if (addressEl) {
      const addressText = addressEl.textContent.trim();
      data.address = addressText;
      // Try to extract city and state from address
      const parts = this._parseCityState(addressText);
      data.city = parts.city;
      data.state = parts.state;
    }

    // Phone
    const phoneEl = container.querySelector(
      "[data-attrid='kc:/collection/knowledge_panels/has_phone:phone'] .LrzXr, " +
      "[data-dtype='d3ph'] .LrzXr, " +
      "span[data-phone-number]"
    );
    if (phoneEl) {
      data.phone = phoneEl.textContent.trim();
    }

    // Try to find phone in the text content
    if (!data.phone) {
      const allText = container.textContent;
      const phoneMatch = allText.match(
        /\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}/
      );
      if (phoneMatch) {
        data.phone = phoneMatch[0];
      }
    }

    // Website link
    const websiteLink =
      container.querySelector("a[href*='http'][data-attrid*='website']") ||
      container.querySelector("a.yYlJEf") ||
      container.querySelector("a[ping]");

    if (websiteLink) {
      data.website = websiteLink.href;
    }

    // Rating
    const ratingEl =
      container.querySelector("span.Aq14fc") ||
      container.querySelector("span.yi40Hd");
    if (ratingEl) {
      data.rating = ratingEl.textContent.trim();
    }

    // Only return if we got at least a business name
    return data.businessName ? data : null;
  },

  /**
   * Extract business data from the Knowledge Panel (right sidebar).
   * @returns {Object|null}
   */
  _extractFromKnowledgePanel() {
    const panel = document.querySelector(
      ".kp-wholepage, .knowledge-panel, .liYKde"
    );
    if (!panel) return null;

    const data = {
      businessName: "",
      phone: "",
      website: "",
      address: "",
      city: "",
      state: "",
      rating: "",
      sourceUrl: window.location.href,
      sourceType: GHL_ASSISTANT.SOURCE_TYPES.GOOGLE_SEARCH,
    };

    // Business name
    const nameEl =
      panel.querySelector("[data-attrid='title'] span") ||
      panel.querySelector("h2[data-attrid='title']") ||
      panel.querySelector("div[data-attrid='title']");
    if (nameEl) {
      data.businessName = nameEl.textContent.trim();
    }

    // Phone
    const phoneEl = panel.querySelector(
      "[data-attrid*='phone'] .LrzXr, [data-attrid*='phone'] span.LrzXr"
    );
    if (phoneEl) {
      data.phone = phoneEl.textContent.trim();
    }

    // Address
    const addressEl = panel.querySelector(
      "[data-attrid*='address'] .LrzXr"
    );
    if (addressEl) {
      data.address = addressEl.textContent.trim();
      const parts = this._parseCityState(data.address);
      data.city = parts.city;
      data.state = parts.state;
    }

    // Website
    const websiteEl = panel.querySelector(
      "[data-attrid*='website'] a, a[data-attrid*='visit']"
    );
    if (websiteEl) {
      data.website = websiteEl.href;
    }

    // Rating
    const ratingEl = panel.querySelector("span.Aq14fc, span.yi40Hd");
    if (ratingEl) {
      data.rating = ratingEl.textContent.trim();
    }

    return data.businessName ? data : null;
  },

  /**
   * Extract basic business info from an organic search result.
   * @param {HTMLElement} element
   * @returns {Object|null}
   */
  _extractFromOrganicResult(element) {
    const container = element.closest(".g, .tF2Cxc, .MjjYud");
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
      sourceType: GHL_ASSISTANT.SOURCE_TYPES.GOOGLE_SEARCH,
    };

    // Title as business name
    const titleEl = container.querySelector("h3");
    if (titleEl) {
      data.businessName = titleEl.textContent.trim();
    }

    // URL as website
    const linkEl = container.querySelector("a[href]");
    if (linkEl && linkEl.href.startsWith("http")) {
      data.website = linkEl.href;
    }

    // Try to find phone in snippet text
    const snippet = container.querySelector(".VwiC3b, .lEBKkf");
    if (snippet) {
      const phoneMatch = snippet.textContent.match(
        /\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}/
      );
      if (phoneMatch) {
        data.phone = phoneMatch[0];
      }
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

    // Common US address pattern: "City, ST ZIP" or "Street, City, ST"
    const stateMatch = address.match(
      /,\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*\d{0,5}/
    );
    if (stateMatch) {
      return { city: stateMatch[1].trim(), state: stateMatch[2] };
    }

    // Try simpler pattern: "..., City, ST"
    const simpleMatch = address.match(/,\s*([^,]+),\s*([A-Z]{2})\s*$/);
    if (simpleMatch) {
      return { city: simpleMatch[1].trim(), state: simpleMatch[2] };
    }

    return { city: "", state: "" };
  },
};
