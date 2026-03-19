/**
 * Floating Action Button Component
 *
 * Creates a floating "⚡ Send to GHL" button that appears near business
 * listings on supported pages. The button triggers data extraction
 * and opens the review popup.
 */

const FloatingButton = {
  _button: null,
  _currentTarget: null,
  _yelpRepositionHandler: null,

  /**
   * Initialize the floating button and attach it to the page.
   */
  init() {
    if (this._button) return;

    this._button = document.createElement("div");
    this._button.id = `${GHL_ASSISTANT.CSS_PREFIX}-floating-btn`;
    this._button.className = `${GHL_ASSISTANT.CSS_PREFIX}-floating-btn`;
    this._button.innerHTML = `
      <span class="${GHL_ASSISTANT.CSS_PREFIX}-btn-icon">⚡</span>
      <span class="${GHL_ASSISTANT.CSS_PREFIX}-btn-text">Send to GHL</span>
    `;
    this._button.style.display = "none";

    this._button.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      this._onCapture();
    });

    document.body.appendChild(this._button);
  },

  /**
   * Best-effort anchor element for Yelp screens.
   * - Prefer visible modal/dialog containers (Yelp often shows biz details in a modal over map/search).
   * - Fallback to business name heading container.
   * - Fallback to main content container.
   * @returns {HTMLElement|null}
   * @private
   */
  _getYelpAnchor() {
    // Prefer the right sidebar on Yelp biz pages when present
    const sidebar =
      document.querySelector("[data-testid='sidebar-content']") ||
      document.querySelector("div[data-testid='sidebar-content']") ||
      null;
    if (sidebar) {
      const rect = sidebar.getBoundingClientRect();
      if (rect.width > 200 && rect.height > 200) return sidebar;
    }

    // Prefer an active dialog/modal if present
    const dialog =
      document.querySelector(
        "div[role='dialog'], [data-testid*='modal'], [data-testid*='Modal']"
      ) || null;
    if (dialog) {
      const rect = dialog.getBoundingClientRect();
      // Filter out hidden/offscreen dialogs
      if (rect.width > 200 && rect.height > 200) return dialog;
    }

    const h1 = document.querySelector("h1");
    if (h1) return h1.closest("header, section, div") || h1.parentElement || h1;

    return (
      document.querySelector("main") ||
      document.querySelector("#wrap") ||
      document.querySelector(".biz-page-header")
    );
  },

  /**
   * Show the floating button near a target element.
   * @param {HTMLElement} element - The business listing element
   */
  show(element) {
    if (!this._button) this.init();

    this._currentTarget = element;

    // Check if this is a direct Google Maps place page
    const isDirectPlacePage =
      window.location.pathname.includes("/maps/place/") &&
      !!document.querySelector("h1.DUwDvf, h1.fontHeadlineLarge");

    // Check if this is a Yelp business detail page
    const isYelpBizPage =
      window.location.hostname.includes("yelp.com") &&
      window.location.pathname.startsWith("/biz/");

    this._button.style.position = "fixed";
    this._button.style.zIndex = "2147483647";
    this._button.style.display = "flex";

    if (isDirectPlacePage) {
      // On direct place pages, position adjacent to the business info panel
      // so the button is contextually associated with the business being viewed
      const panelRect = element.getBoundingClientRect();
      const btnWidth = 150; // approximate button width with text + padding

      if (panelRect.width > 0) {
        // Place just to the right of the panel, near the top
        const leftPos = Math.min(panelRect.right + 12, window.innerWidth - btnWidth);
        const topPos = Math.max(panelRect.top + 10, 10);
        this._button.style.top = `${topPos}px`;
        this._button.style.left = `${leftPos}px`;
        this._button.style.right = "auto";
      } else {
        // Fallback: position next to typical panel width (~408px)
        this._button.style.top = "80px";
        this._button.style.left = "420px";
        this._button.style.right = "auto";
      }
    } else if (isYelpBizPage) {
      // On Yelp biz detail pages, Yelp may render details either inline or inside a modal.
      // Prefer anchoring to the right sidebar; otherwise anchor to dialog/heading.
      const anchor = this._getYelpAnchor() || element;
      const rect = anchor.getBoundingClientRect();

      const btnWidth = 170; // a bit safer for longer text
      const margin = 16;

      // Place adjacent to the right edge of anchor when possible.
      // If that would go offscreen, fall back to inside the anchor's top-right.
      const desiredTop = rect.top + margin;
      const clampedTop = Math.min(
        Math.max(desiredTop, 96), // keep below common Yelp header heights
        window.innerHeight - 56
      );
      const desiredOutsideLeft = rect.right + 12;
      const outsideFits =
        desiredOutsideLeft + btnWidth <= window.innerWidth - margin;
      const desiredLeft = outsideFits
        ? desiredOutsideLeft
        : rect.right - btnWidth - margin;
      const clampedLeft = Math.min(Math.max(desiredLeft, margin), window.innerWidth - btnWidth - margin);

      this._button.style.top = `${clampedTop}px`;
      this._button.style.left = `${clampedLeft}px`;
      this._button.style.right = "auto";

      // Keep it stable if Yelp reflows (modal open/close, dynamic content).
      if (!this._yelpRepositionHandler) {
        this._yelpRepositionHandler = () => {
          if (!this._button || this._button.style.display === "none") return;
          if (
            !window.location.hostname.includes("yelp.com") ||
            !window.location.pathname.startsWith("/biz/")
          ) {
            return;
          }
          const a = this._getYelpAnchor();
          if (!a) return;
          const r = a.getBoundingClientRect();
          const top = Math.min(
            Math.max(r.top + margin, 96),
            window.innerHeight - 56
          );
          const outsideLeft = r.right + 12;
          const fits = outsideLeft + btnWidth <= window.innerWidth - margin;
          const baseLeft = fits ? outsideLeft : r.right - btnWidth - margin;
          const left = Math.min(Math.max(baseLeft, margin), window.innerWidth - btnWidth - margin);
          this._button.style.top = `${top}px`;
          this._button.style.left = `${left}px`;
          this._button.style.right = "auto";
        };
        window.addEventListener("resize", this._yelpRepositionHandler, { passive: true });
        window.addEventListener("scroll", this._yelpRepositionHandler, { passive: true, capture: true });
      }
    } else {
      // On search results, position near the hovered listing
      const rect = element.getBoundingClientRect();
      this._button.style.top = `${Math.max(rect.top, 10)}px`;
      this._button.style.left = `${Math.min(rect.right + 8, window.innerWidth - 160)}px`;
      this._button.style.right = "auto";
    }
  },

  /**
   * Hide the floating button.
   */
  hide() {
    if (this._button) {
      this._button.style.display = "none";
      this._currentTarget = null;
    }
  },

  /**
   * Handle the capture button click.
   * Extracts data from the current target and opens the review popup.
   * @private
   */
  _onCapture() {
    if (!this._currentTarget) return;

    // Extract data using the appropriate extractor
    let extractedData = null;

    if (GoogleSearchExtractor.isMatch()) {
      extractedData = GoogleSearchExtractor.extract(this._currentTarget);
    } else if (GoogleMapsExtractor.isMatch()) {
      extractedData = GoogleMapsExtractor.extract(this._currentTarget);
    }

    // Fallback to generic extractor
    if (!extractedData) {
      extractedData = GenericExtractor.extract(this._currentTarget);
    }

    if (extractedData) {
      // Open the review popup with extracted data
      ReviewPopup.show(extractedData);
      this.hide();
    } else {
      // Show a brief error notification
      this._showError("Could not extract business data from this element.");
    }
  },

  /**
   * Show a brief error message near the button.
   * @param {string} message
   * @private
   */
  _showError(message) {
    const toast = document.createElement("div");
    toast.className = `${GHL_ASSISTANT.CSS_PREFIX}-toast ${GHL_ASSISTANT.CSS_PREFIX}-toast-error`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.classList.add(`${GHL_ASSISTANT.CSS_PREFIX}-toast-fade`);
      setTimeout(() => toast.remove(), 300);
    }, 2500);
  },
};
