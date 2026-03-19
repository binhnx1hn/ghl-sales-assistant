/**
 * Main Content Script
 *
 * Entry point for the GHL Sales Assistant content script.
 * Detects business listings on the page, attaches hover listeners,
 * and shows the floating capture button.
 */

(function () {
  "use strict";

  // Prevent double initialization
  if (window.__ghlSalesAssistantLoaded) return;
  window.__ghlSalesAssistantLoaded = true;

  let hideTimeout = null;

  /**
   * Initialize the content script.
   * Detects the current page type and sets up listing detection.
   */
  function init() {
    // Wait a bit for dynamic content to load (especially Maps)
    setTimeout(() => {
      FloatingButton.init();
      attachListingListeners();
      observeDOMChanges();

      // Auto-show floating button on direct Google Maps place pages
      autoShowOnPlacePage();

      // Auto-show floating button on Yelp business detail pages
      autoShowOnYelpBizPage();
    }, 1500);
  }

  /**
   * On direct Google Maps place pages (e.g. /maps/place/Business+Name),
   * there are no search result items to hover. Auto-show the floating
   * button anchored to the place panel.
   */
  function autoShowOnPlacePage() {
    if (!GoogleMapsExtractor.isMatch()) return;
    if (!window.location.pathname.includes("/maps/place/")) return;

    const nameEl = document.querySelector("h1.DUwDvf, h1.fontHeadlineLarge");
    if (!nameEl) return;

    // Find the place panel to anchor the button
    const placePanel =
      document.querySelector("div[role='main'] div.m6QErb") ||
      document.querySelector("div[role='main']") ||
      document.querySelector("#QA0Szd");

    if (placePanel) {
      FloatingButton.show(placePanel);
    }
  }

  /**
   * On Yelp business detail pages (e.g. /biz/business-name),
   * there are no search result cards to hover. Auto-show the floating
   * button anchored to the main content area.
   */
  function autoShowOnYelpBizPage() {
    if (!window.location.hostname.includes("yelp.com")) return;
    if (!window.location.pathname.startsWith("/biz/")) return;

    const contentArea =
      document.querySelector("main") ||
      document.querySelector("#wrap") ||
      document.querySelector(".biz-page-header");

    if (!contentArea) {
      // Fallback: use the parent of the business name heading
      const h1 = document.querySelector("h1");
      if (h1 && h1.parentElement) {
        FloatingButton.show(h1.parentElement);
      }
      return;
    }

    FloatingButton.show(contentArea);
  }

  /**
   * Find all business listings on the current page and attach
   * hover event listeners to show the floating capture button.
   */
  function attachListingListeners() {
    let listings = [];

    if (GoogleSearchExtractor.isMatch()) {
      listings = GoogleSearchExtractor.getListings();
    } else if (GoogleMapsExtractor.isMatch()) {
      listings = GoogleMapsExtractor.getListings();
    }

    // Also get generic directory listings
    const genericListings = GenericExtractor.getListings();
    listings = [...listings, ...genericListings];

    listings.forEach((listing) => {
      // Skip if already processed
      if (listing.dataset.ghlProcessed) return;
      listing.dataset.ghlProcessed = "true";

      listing.addEventListener("mouseenter", () => {
        clearTimeout(hideTimeout);
        FloatingButton.show(listing);
      });

      listing.addEventListener("mouseleave", () => {
        // Don't auto-hide on direct place pages or Yelp biz pages (button is permanently shown)
        if (
          (window.location.pathname.includes("/maps/place/") &&
            GoogleMapsExtractor.isMatch()) ||
          (window.location.hostname.includes("yelp.com") &&
            window.location.pathname.startsWith("/biz/"))
        ) {
          return;
        }
        hideTimeout = setTimeout(() => {
          FloatingButton.hide();
        }, 800);
      });
    });
  }

  /**
   * Observe DOM changes to detect dynamically loaded listings.
   * Google Search and Maps load content dynamically, so we need
   * to re-scan when new content appears.
   */
  function observeDOMChanges() {
    const observer = new MutationObserver((mutations) => {
      let hasNewContent = false;

      for (const mutation of mutations) {
        if (mutation.addedNodes.length > 0) {
          for (const node of mutation.addedNodes) {
            if (
              node.nodeType === Node.ELEMENT_NODE &&
              !node.classList?.contains(GHL_ASSISTANT.CSS_PREFIX + "-overlay") &&
              !node.classList?.contains(GHL_ASSISTANT.CSS_PREFIX + "-floating-btn") &&
              !node.classList?.contains(GHL_ASSISTANT.CSS_PREFIX + "-toast")
            ) {
              hasNewContent = true;
              break;
            }
          }
        }
        if (hasNewContent) break;
      }

      if (hasNewContent) {
        // Debounce re-scanning
        clearTimeout(observeDOMChanges._debounce);
        observeDOMChanges._debounce = setTimeout(() => {
          attachListingListeners();
        }, 500);
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  // Keep floating button visible when hovering over it
  document.addEventListener("mouseenter", (e) => {
    if (
      e.target.closest &&
      e.target.closest(`#${GHL_ASSISTANT.CSS_PREFIX}-floating-btn`)
    ) {
      clearTimeout(hideTimeout);
    }
  }, true);

  document.addEventListener("mouseleave", (e) => {
    if (
      e.target.closest &&
      e.target.closest(`#${GHL_ASSISTANT.CSS_PREFIX}-floating-btn`)
    ) {
      // Don't auto-hide on direct place pages or Yelp biz pages
      if (
        (window.location.pathname.includes("/maps/place/") &&
          GoogleMapsExtractor.isMatch()) ||
        (window.location.hostname.includes("yelp.com") &&
          window.location.pathname.startsWith("/biz/"))
      ) {
        return;
      }
      hideTimeout = setTimeout(() => {
        FloatingButton.hide();
      }, 400);
    }
  }, true);

  // Initialize when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
