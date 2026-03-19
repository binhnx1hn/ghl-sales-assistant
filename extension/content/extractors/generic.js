/**
 * Generic Directory Site Data Extractor
 *
 * Extracts business information from common directory sites like
 * Yelp, Yellow Pages, and other listing sites using Schema.org
 * markup and common HTML patterns.
 */

const GenericExtractor = {
  /**
   * Check if this extractor should be used as a fallback.
   * Always returns true since it's the generic catch-all.
   * @returns {boolean}
   */
  isMatch() {
    return true;
  },

  /**
   * Extract business data from the current page using multiple strategies.
   *
   * @param {HTMLElement} targetElement - The element the user clicked near
   * @returns {Object|null} Extracted business data or null
   */
  extract(targetElement) {
    // Strategy 1: Try Schema.org structured data (JSON-LD)
    const schemaResult = this._extractFromSchemaOrg();
    if (schemaResult && schemaResult.businessName) return schemaResult;

    // Strategy 2: Try Yelp-specific extraction
    if (window.location.hostname.includes("yelp.com")) {
      const yelpResult = this._extractFromYelp(targetElement);
      if (yelpResult) return yelpResult;
    }

    // Strategy 3: Try Yellow Pages-specific extraction
    if (window.location.hostname.includes("yellowpages.com")) {
      const ypResult = this._extractFromYellowPages(targetElement);
      if (ypResult) return ypResult;
    }

    // Strategy 4: Try generic page extraction
    const genericResult = this._extractFromPage(targetElement);
    if (genericResult && genericResult.businessName) return genericResult;

    return null;
  },

  /**
   * Get all visible business listings on directory pages.
   * @returns {Array<HTMLElement>}
   */
  getListings() {
    const listings = [];

    // Yelp listings
    if (window.location.hostname.includes("yelp.com")) {
      document
        .querySelectorAll("[data-testid='serp-ia-card'], .container__09f24__FeTO6")
        .forEach((el) => listings.push(el));

      // Yelp business detail page (/biz/...) — no search cards present,
      // so push the main content container as a single "listing"
      if (listings.length === 0 && window.location.pathname.startsWith("/biz/")) {
        const bizContainer =
          document.querySelector("main") ||
          document.querySelector("#wrap") ||
          document.querySelector(".biz-page-header");
        if (!bizContainer) {
          // Fallback: use the parent of the business name heading
          const h1 = document.querySelector("h1");
          if (h1 && h1.parentElement) {
            listings.push(h1.parentElement);
          }
        } else {
          listings.push(bizContainer);
        }
      }
    }

    // Yellow Pages listings
    if (window.location.hostname.includes("yellowpages.com")) {
      document
        .querySelectorAll(".result, .srp-listing")
        .forEach((el) => listings.push(el));
    }

    return listings;
  },

  /**
   * Extract data from Schema.org JSON-LD structured data.
   * Many business websites include this for SEO.
   * @returns {Object|null}
   */
  _extractFromSchemaOrg() {
    const scripts = document.querySelectorAll(
      'script[type="application/ld+json"]'
    );
    const data = {
      businessName: "",
      phone: "",
      website: "",
      address: "",
      city: "",
      state: "",
      rating: "",
      sourceUrl: window.location.href,
      sourceType: this._detectSourceType(),
    };

    for (const script of scripts) {
      try {
        const json = JSON.parse(script.textContent);
        const items = Array.isArray(json) ? json : [json];

        for (const item of items) {
          if (
            item["@type"] === "LocalBusiness" ||
            item["@type"] === "Organization" ||
            item["@type"] === "MedicalBusiness" ||
            item["@type"] === "NursingHome" ||
            (typeof item["@type"] === "string" &&
              item["@type"].includes("Business"))
          ) {
            data.businessName = item.name || "";
            data.phone = item.telephone || "";
            data.website = item.url || window.location.href;

            if (item.address) {
              const addr = item.address;
              if (typeof addr === "string") {
                data.address = addr;
              } else {
                data.address = [
                  addr.streetAddress,
                  addr.addressLocality,
                  addr.addressRegion,
                  addr.postalCode,
                ]
                  .filter(Boolean)
                  .join(", ");
                data.city = addr.addressLocality || "";
                data.state = addr.addressRegion || "";
              }
            }

            if (item.aggregateRating) {
              data.rating = String(item.aggregateRating.ratingValue || "");
            }

            return data;
          }
        }
      } catch (e) {
        // Skip invalid JSON-LD
        continue;
      }
    }

    return data.businessName ? data : null;
  },

  /**
   * Extract business data from Yelp listing pages.
   * @param {HTMLElement} element
   * @returns {Object|null}
   */
  _extractFromYelp(element) {
    const container =
      element.closest("[data-testid='serp-ia-card']") ||
      element.closest(".container__09f24__FeTO6") ||
      element.closest("li");

    const data = {
      businessName: "",
      phone: "",
      website: "",
      address: "",
      city: "",
      state: "",
      rating: "",
      sourceUrl: window.location.href,
      sourceType: GHL_ASSISTANT.SOURCE_TYPES.YELP,
    };

    if (container) {
      // Business name from listing card
      const nameEl = container.querySelector(
        "a[href*='/biz/'] h3, a[href*='/biz/'] span.css-1egxyvc"
      );
      if (nameEl) {
        data.businessName = nameEl.textContent.trim().replace(/^\d+\.\s*/, "");
      }

      // Rating
      const ratingEl = container.querySelector(
        "[aria-label*='star rating'], div[role='img']"
      );
      if (ratingEl) {
        const label = ratingEl.getAttribute("aria-label") || "";
        const ratingMatch = label.match(/(\d+\.?\d*)/);
        if (ratingMatch) data.rating = ratingMatch[1];
      }

      // Phone
      const phoneEl = container.querySelector("p[class*='phone']");
      if (phoneEl) {
        data.phone = phoneEl.textContent.trim();
      }

      // Address
      const addressEl = container.querySelector(
        "p[class*='address'], address"
      );
      if (addressEl) {
        data.address = addressEl.textContent.trim();
      }
    } else {
      // We might be on a business detail page
      const nameEl = document.querySelector(
        "h1[class*='heading'], h1[class*='businessName']"
      );
      if (nameEl) data.businessName = nameEl.textContent.trim();

      const phoneEl = document.querySelector(
        "p[class*='phone'] a[href^='tel:'], a[href^='tel:']"
      );
      if (phoneEl) {
        data.phone = phoneEl.textContent.trim();
      }

      const addressEl = document.querySelector("address, p[class*='address']");
      if (addressEl) data.address = addressEl.textContent.trim();

      const websiteLink = document.querySelector(
        "a[href*='biz_redir'], a[class*='website']"
      );
      if (websiteLink) data.website = websiteLink.href;
    }

    return data.businessName ? data : null;
  },

  /**
   * Extract business data from Yellow Pages listing pages.
   * @param {HTMLElement} element
   * @returns {Object|null}
   */
  _extractFromYellowPages(element) {
    const container =
      element.closest(".result") ||
      element.closest(".srp-listing") ||
      element.closest(".v-card");

    const data = {
      businessName: "",
      phone: "",
      website: "",
      address: "",
      city: "",
      state: "",
      rating: "",
      sourceUrl: window.location.href,
      sourceType: GHL_ASSISTANT.SOURCE_TYPES.YELLOW_PAGES,
    };

    if (container) {
      const nameEl = container.querySelector(
        ".business-name a, .n a, h2.n a"
      );
      if (nameEl) data.businessName = nameEl.textContent.trim();

      const phoneEl = container.querySelector(".phones, .phone");
      if (phoneEl) data.phone = phoneEl.textContent.trim();

      const streetEl = container.querySelector(".street-address, .adr .street-address");
      const localityEl = container.querySelector(".locality, .adr .locality");
      if (streetEl) data.address = streetEl.textContent.trim();
      if (localityEl) {
        const localityText = localityEl.textContent.trim();
        if (data.address) {
          data.address += ", " + localityText;
        } else {
          data.address = localityText;
        }
        const parts = this._parseCityState(localityText);
        data.city = parts.city;
        data.state = parts.state;
      }

      const websiteLink = container.querySelector(
        "a.track-visit-website, a[href*='website']"
      );
      if (websiteLink) data.website = websiteLink.href;
    }

    return data.businessName ? data : null;
  },

  /**
   * Generic extraction from page content.
   * Uses common patterns to find business information.
   * @param {HTMLElement} element
   * @returns {Object|null}
   */
  _extractFromPage(element) {
    const data = {
      businessName: "",
      phone: "",
      website: window.location.href,
      address: "",
      city: "",
      state: "",
      rating: "",
      sourceUrl: window.location.href,
      sourceType: this._detectSourceType(),
    };

    // Try the page title or main heading
    const h1 = document.querySelector("h1");
    if (h1) {
      data.businessName = h1.textContent.trim();
    } else {
      data.businessName = document.title.split("|")[0].split("-")[0].trim();
    }

    // Try to find phone number on the page near the clicked element
    const nearbyText = element.closest("div, section, article")?.textContent || "";
    const phoneMatch = nearbyText.match(/\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}/);
    if (phoneMatch) {
      data.phone = phoneMatch[0];
    }

    // Try to find address using common selectors
    const addressEl = document.querySelector(
      "address, [itemprop='address'], .address, #address"
    );
    if (addressEl) {
      data.address = addressEl.textContent.trim().replace(/\s+/g, " ");
    }

    return data.businessName ? data : null;
  },

  /**
   * Detect the source type based on the current URL.
   * @returns {string}
   */
  _detectSourceType() {
    const hostname = window.location.hostname;
    if (hostname.includes("yelp.com")) return GHL_ASSISTANT.SOURCE_TYPES.YELP;
    if (hostname.includes("yellowpages.com"))
      return GHL_ASSISTANT.SOURCE_TYPES.YELLOW_PAGES;
    return GHL_ASSISTANT.SOURCE_TYPES.DIRECTORY;
  },

  /**
   * Parse city and state from an address/locality string.
   * @param {string} text
   * @returns {{city: string, state: string}}
   */
  _parseCityState(text) {
    if (!text) return { city: "", state: "" };

    // "City, ST" or "City, ST ZIP"
    const match = text.match(/([^,]+),\s*([A-Z]{2})\s*\d{0,5}/);
    if (match) {
      return { city: match[1].trim(), state: match[2] };
    }

    return { city: "", state: "" };
  },
};
