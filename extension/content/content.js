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
    }, 1000);
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
