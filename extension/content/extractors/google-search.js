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

    // Try to extract from #local-place-viewer panel
    const localPlaceResult = this._extractFromLocalPlaceViewer(targetElement);
    if (localPlaceResult) return localPlaceResult;

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
      if (panel && !listings.includes(panel)) listings.push(panel);
    }

    // Local place viewer panel (rendered when clicking a listing in the local pack,
    // e.g. URL contains #sv=... — Google renders a side panel with class .kp-wholepage
    // or a dedicated place panel that may not have [data-cid] on the root).
    const placePanel = document.querySelector(".kp-wholepage, .liYKde");
    if (placePanel && !listings.includes(placePanel)) {
      listings.push(placePanel);
    }

    // #local-place-viewer panel (id="local-place-viewer", class="yf") — rendered when
    // the user clicks a local pack listing; contains h2.BK5CCe for name, [data-phone-number]
    // for phone, and .bkaPDb a.n1obkb for website. Not matched by any other selector above.
    const localPlaceViewer = document.querySelector("#local-place-viewer");
    if (localPlaceViewer && !listings.includes(localPlaceViewer)) {
      listings.push(localPlaceViewer);
    }

    return listings;
  },

  /**
   * Best-effort detection of the real external "Website" link inside a Google
   * Search local/knowledge panel block.
   * - Prefer anchors that are explicitly marked as website buttons.
   * - Fallback to non-Google, non-Maps HTTP links.
   * @param {HTMLElement} root
   * @returns {HTMLAnchorElement|null}
   * @private
   */
  _findWebsiteLink(root) {
    if (!root) return null;

    // 1) Explicit website attrid (older layouts)
    let link =
      root.querySelector("a[href^='http'][data-attrid*='website']") ||
      root.querySelector("[data-attrid*='website'] a[href^='http']");
    if (link) return link;

    // 1b) Targeted action-button selectors (BUG-001 fix):
    //     .bkaPDb is the "Website" action button container in Local Pack;
    //     a[href]:has(span.aSAiSd) matches the link that wraps the "Website" label span.
    //     These are checked BEFORE the broad a[ping] scan so the Maps place
    //     link (which also carries ping) can never win.
    const actionLink =
      root.querySelector(".bkaPDb a.n1obkb[href^='http']") ||
      root.querySelector("a[href^='http']:has(span.aSAiSd)");
    if (actionLink) return actionLink;

    // 2) Buttons whose text contains "Website" (newer layouts, e.g. span.aSAiSd).
    //    Guard: skip any link whose href points to google.com/maps or google.com/search.
    const websiteButtons = Array.from(
      root.querySelectorAll("a[href^='http'][ping]")
    );
    for (const a of websiteButtons) {
      const label = a.textContent || "";
      const href = a.href || "";
      if (
        label.toLowerCase().includes("website") &&
        !href.includes("google.com/maps") &&
        !href.includes("google.com/search")
      ) {
        return a;
      }
    }

    // 3) Fallback: any non-Google, non-Maps link inside the panel/container.
    const candidates = Array.from(root.querySelectorAll("a[href^='http']"));
    for (const a of candidates) {
      try {
        const url = new URL(a.href);
        const host = url.hostname.toLowerCase();
        const path = url.pathname || "";
        const isGoogleDomain = host.includes("google.") || host.endsWith(".google");
        const isMapsPath = path.includes("/maps/");
        if (!isGoogleDomain && !isMapsPath) {
          return a;
        }
      } catch {
        // Ignore malformed URLs and keep looking
        continue;
      }
    }

    return null;
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

    // #local-place-viewer is handled by _extractFromLocalPlaceViewer; skip here.
    if (!container) return null;

    const data = {
      businessName: "",
      phone: "",
      website: "",
      address: "",
      city: "",
      state: "",
      rating: "",
      socialLinks: { linkedin: "", facebook: "", instagram: "", tiktok: "" },
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

    // Website link - prefer explicit "Website" button and external domains,
    // avoid Google Maps / internal Google URLs.
    const websiteLink = this._findWebsiteLink(container);
    if (websiteLink) data.website = websiteLink.href;

    // Rating
    const ratingEl =
      container.querySelector("span.Aq14fc") ||
      container.querySelector("span.yi40Hd");
    if (ratingEl) {
      data.rating = ratingEl.textContent.trim();
    }

    // Social links — also check the full Knowledge Panel in case local pack
    // card doesn't have them but the sidebar does.
    const kpRoot = document.querySelector(".kp-wholepage, .knowledge-panel, .liYKde");
    data.socialLinks = this._extractSocialLinks(kpRoot || container);

    // Only return if we got at least a business name
    return data.businessName ? data : null;
  },

  /**
   * Extract social profile links directly from a DOM root element.
   * Looks for anchor hrefs pointing to known social platforms.
   * @param {HTMLElement} root
   * @returns {{ linkedin: string, facebook: string, instagram: string, tiktok: string }}
   * @private
   */
  _extractSocialLinks(root) {
    const social = { linkedin: "", facebook: "", instagram: "", tiktok: "" };
    if (!root) return social;

    const anchors = Array.from(root.querySelectorAll("a[href]"));
    for (const a of anchors) {
      const href = a.href || "";
      try {
        const url = new URL(href);
        const host = url.hostname.toLowerCase();
        const path = url.pathname || "";

        if (!social.linkedin && host.includes("linkedin.com")) {
          // Accept only company or person profile pages
          if (/^\/(company|in)\/[^/]+\/?$/.test(path)) {
            social.linkedin = href;
          }
        } else if (!social.facebook && host.includes("facebook.com")) {
          // Reject photo, video, event, location, explore, story pages
          if (!/\/(photo|video|events|pages|groups|stories|explore|permalink|media)/.test(path) &&
              path !== "/" && path.length > 1) {
            social.facebook = href;
          }
        } else if (!social.instagram && host.includes("instagram.com")) {
          // Reject explore, p/, reel/, stories/ — accept only /@handle or /handle/
          if (!/\/(explore|p\/|reel\/|stories\/|tv\/)/.test(path) &&
              path !== "/" && path.length > 1) {
            social.instagram = href;
          }
        } else if (!social.tiktok && host.includes("tiktok.com")) {
          // Accept only profile pages: /@handle (no /video/ sub-path)
          if (/^\/@[^/]+\/?$/.test(path)) {
            social.tiktok = href;
          }
        }
      } catch {
        // ignore malformed URLs
      }
    }
    return social;
  },

  /**
   * Extract business data from the #local-place-viewer panel.
   * This panel (id="local-place-viewer", class="yf") is rendered when the user
   * clicks a listing in the local pack. It uses different selectors than the
   * standard local pack card: h2.BK5CCe for name, [data-phone-number] attr for
   * phone, .bkaPDb a.n1obkb for website, .Bye9Fc for rating.
   * @param {HTMLElement} element
   * @returns {Object|null}
   */
  _extractFromLocalPlaceViewer(element) {
    const panel =
      element.closest("#local-place-viewer") ||
      (element.id === "local-place-viewer" ? element : null) ||
      document.querySelector("#local-place-viewer");

    if (!panel) return null;

    const data = {
      businessName: "",
      phone: "",
      website: "",
      address: "",
      city: "",
      state: "",
      rating: "",
      socialLinks: { linkedin: "", facebook: "", instagram: "", tiktok: "" },
      sourceUrl: window.location.href,
      sourceType: GHL_ASSISTANT.SOURCE_TYPES.GOOGLE_SEARCH,
    };

    // Business name: h2.BK5CCe is the primary heading in this panel
    const nameEl =
      panel.querySelector("h2.BK5CCe") ||
      panel.querySelector("h2") ||
      panel.querySelector("[data-attrid='title']");
    if (nameEl) {
      const clone = nameEl.cloneNode(true);
      clone.querySelectorAll("a, button").forEach((el) => el.remove());
      data.businessName = clone.textContent.trim();
    }

    // Phone: data-phone-number attribute on anchor elements
    const phoneAnchor = panel.querySelector("a[data-phone-number]");
    if (phoneAnchor) {
      const raw = phoneAnchor.getAttribute("data-phone-number") || "";
      const digits = raw.replace(/\D/g, "");
      if (digits.length >= 10) {
        // Display text is in nested .C9waJd div; fall back to raw attribute
        const displayEl = phoneAnchor.querySelector(".C9waJd");
        data.phone = (displayEl ? displayEl.textContent.trim() : "") || raw;
      }
    }

    // Fallback phone selectors
    if (!data.phone) {
      const phoneSelectors = [
        "[data-attrid*='phone'] .LrzXr",
        "[data-attrid*='phone'] span",
        "[data-dtype='d3ph'] .LrzXr",
      ];
      for (const sel of phoneSelectors) {
        const el = panel.querySelector(sel);
        if (el) {
          const text = el.textContent.trim();
          if (text.replace(/\D/g, "").length >= 10) {
            data.phone = text;
            break;
          }
        }
      }
    }

    // Website: .bkaPDb a.n1obkb is the "Website" action button in this panel
    const websiteLink = this._findWebsiteLink(panel);
    if (websiteLink) data.website = websiteLink.href;

    // Address
    const addressEl =
      panel.querySelector(".C9waJd.y7xX3d span") ||
      panel.querySelector(".y7xX3d span") ||
      panel.querySelector("[data-attrid*='address'] .LrzXr") ||
      panel.querySelector("[data-attrid*='address']");
    if (addressEl) {
      data.address = addressEl.textContent.trim();
      const parts = this._parseCityState(data.address);
      data.city = parts.city;
      data.state = parts.state;
    }

    // Rating: .Bye9Fc is the rating span in this panel
    const ratingEl =
      panel.querySelector(".Bye9Fc") ||
      panel.querySelector("span.Aq14fc") ||
      panel.querySelector("span.yi40Hd");
    if (ratingEl) {
      data.rating = ratingEl.textContent.trim();
    }

    data.socialLinks = this._extractSocialLinks(panel);

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
      socialLinks: { linkedin: "", facebook: "", instagram: "", tiktok: "" },
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

    // Website - use the same helper we use for local pack cards so that we
    // correctly pick the "Website" button (e.g. <span class="aSAiSd">Website</span>)
    // instead of Google Maps URLs.
    const websiteEl = this._findWebsiteLink(panel);
    if (websiteEl) data.website = websiteEl.href;

    // Rating
    const ratingEl = panel.querySelector("span.Aq14fc, span.yi40Hd");
    if (ratingEl) {
      data.rating = ratingEl.textContent.trim();
    }

    // Social links - scrape directly from Knowledge Panel DOM (free, instant)
    data.socialLinks = this._extractSocialLinks(panel);

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
