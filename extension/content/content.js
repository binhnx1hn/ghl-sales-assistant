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
    FloatingButton.init();
    attachListingListeners();
    observeDOMChanges();

    // Auto-show floating button on direct Google Maps place pages
    autoShowOnPlacePage();

    // Auto-show floating button on Yelp business detail pages
    autoShowOnYelpBizPage();

    // Auto-show floating button when #local-place-viewer panel is already present
    autoShowOnLocalPlaceViewer();
  }

  /**
   * Auto-show the floating button when #local-place-viewer is present.
   * Called on init and from observeDOMChanges when the panel appears.
   */
  function autoShowOnLocalPlaceViewer() {
    if (!GoogleSearchExtractor.isMatch()) return;
    const panel = document.querySelector("#local-place-viewer");
    if (!panel) return;
    // Only auto-show if the panel has a visible business name
    const nameEl = panel.querySelector("h2.BK5CCe, h2, [data-attrid='title']");
    if (!nameEl || !nameEl.textContent.trim()) return;
    FloatingButton.show(panel);
  }

  /**
   * On direct Google Maps place pages (e.g. /maps/place/Business+Name),
   * there are no search result items to hover. Auto-show the floating
   * button anchored to the place panel.
   *
   * Maps renders the panel asynchronously — retry up to ~3s.
   */
  function autoShowOnPlacePage() {
    if (!GoogleMapsExtractor.isMatch()) return;
    if (!window.location.pathname.includes("/maps/place/")) return;

    const tryShow = (attempts = 0) => {
      const nameEl = document.querySelector("h1.DUwDvf, h1.fontHeadlineLarge");
      if (!nameEl) {
        if (attempts < 10) setTimeout(() => tryShow(attempts + 1), 300);
        return;
      }
      const placePanel =
        document.querySelector("div[role='main'] div.m6QErb") ||
        document.querySelector("div[role='main']") ||
        document.querySelector("#QA0Szd");
      if (placePanel) FloatingButton.show(placePanel);
    };
    tryShow();
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
   * @param {boolean} resetPanels - If true, reset ghlProcessed on panel elements
   *   so they get re-attached after Google re-renders them.
   */
  function attachListingListeners(resetPanels = false) {
    // Reset ghlProcessed on panel-type elements so Google's async re-renders
    // get re-attached (panels are replaced in-place, not newly added to DOM).
    if (resetPanels && GoogleSearchExtractor.isMatch()) {
      document.querySelectorAll(".kp-wholepage, .liYKde, .knowledge-panel, #local-place-viewer").forEach((el) => {
        delete el.dataset.ghlProcessed;
      });
    }

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
        // 1200ms grace — long enough to move the mouse from listing to button
        hideTimeout = setTimeout(() => {
          FloatingButton.hide();
        }, 1200);
      });
    });
  }

  /**
   * Observe DOM changes to detect dynamically loaded listings.
   * Scoped to subtree childList only; skips our own injected nodes.
   * Debounced at 300ms to catch Google's async panel renders quickly.
   */
  function observeDOMChanges() {
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType !== Node.ELEMENT_NODE) continue;
          // Ignore our own injected elements
          const cls = node.className || "";
          if (
            typeof cls === "string" && (
              cls.includes(GHL_ASSISTANT.CSS_PREFIX + "-overlay") ||
              cls.includes(GHL_ASSISTANT.CSS_PREFIX + "-floating-btn") ||
              cls.includes(GHL_ASSISTANT.CSS_PREFIX + "-toast") ||
              cls.includes(GHL_ASSISTANT.CSS_PREFIX + "-phase2")
            )
          ) continue;
          // Only re-scan when a meaningful content node is added
          clearTimeout(observeDOMChanges._debounce);
          observeDOMChanges._debounce = setTimeout(() => {
            attachListingListeners(true);
            autoShowOnLocalPlaceViewer();
          }, 300);
          return;
        }
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
      }, 600);
    }
  }, true);

  // Initialize immediately — no blind delay
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
