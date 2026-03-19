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

    // Business name - use data-attrid='title' first (most reliable),
    // avoid .OSrXXb which matches "Suggest an edit" container
    const nameEl =
      container.querySelector("div[data-attrid='title']") ||
      container.querySelector("[data-attrid='title'] span") ||
      container.querySelector("h2[data-attrid='title']") ||
      container.querySelector(".dbg0pd") ||
      container.querySelector("span.czHgge") ||
      container.querySelector("a .lhCR5d");

    if (nameEl) {
      // Get text but exclude nested "Suggest an edit" buttons
      const clone = nameEl.cloneNode(true);
      // Remove any <a>, <button> child elements that might contain "Suggest an edit"
      clone.querySelectorAll("a, button").forEach((el) => el.remove());
      const nameText = clone.textContent.trim();
      data.businessName = nameText || nameEl.childNodes[0]?.textContent?.trim() || "";
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

    // Phone - use data-attrid selectors for GHL Knowledge Panel
    const phoneSelectors = [
      "[data-attrid*='phone'] .LrzXr",
      "[data-attrid*='phone'] span",
      "[data-dtype='d3ph'] .LrzXr",
      "span[data-phone-number]",
      "[data-attrid='kc:/collection/knowledge_panels/has_phone:phone'] .LrzXr",
    ];
    for (const sel of phoneSelectors) {
      const el = container.querySelector(sel);
      if (el) {
        const text = el.textContent.trim();
        // Validate: must have at least 10 digits
        const digits = text.replace(/\D/g, "");
        if (digits.length >= 10) {
          data.phone = text;
          break;
        }
      }
    }

    // Fallback: scan full text for E.164 or standard US format
    // Use strict pattern to avoid partial numbers like 568.2352941
    if (!data.phone) {
      const allText = container.textContent;
      // Match full US phone: (xxx) xxx-xxxx OR +1 xxx-xxx-xxxx OR xxx-xxx-xxxx
      const phoneMatch = allText.match(
        /(?:\+1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}/
      );
      if (phoneMatch) {
        data.phone = phoneMatch[0].trim();
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

    // Business name - get from data-attrid='title', exclude nested buttons/links
    const nameEl =
      panel.querySelector("div[data-attrid='title']") ||
      panel.querySelector("[data-attrid='title'] span") ||
      panel.querySelector("h2[data-attrid='title']");
    if (nameEl) {
      const clone = nameEl.cloneNode(true);
      clone.querySelectorAll("a, button").forEach((el) => el.remove());
      const nameText = clone.textContent.trim();
      data.businessName = nameText || nameEl.childNodes[0]?.textContent?.trim() || "";
    }

    // Phone - try all data-attrid phone selectors, validate 10+ digits
    const phoneSelectors = [
      "[data-attrid*='phone'] .LrzXr",
      "[data-attrid*='phone'] span",
      "[data-dtype='d3ph'] .LrzXr",
    ];
    for (const sel of phoneSelectors) {
      const el = panel.querySelector(sel);
      if (el) {
        const text = el.textContent.trim();
        const digits = text.replace(/\D/g, "");
        if (digits.length >= 10) {
          data.phone = text;
          break;
        }
      }
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
