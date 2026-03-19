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

    this._button.style.position = "fixed";
    this._button.style.zIndex = "2147483647";
    this._button.style.display = "flex";

    if (isDirectPlacePage) {
      // On direct place pages, show button at a fixed prominent position
      // (top-right area, always visible)
      this._button.style.top = "80px";
      this._button.style.left = "auto";
      this._button.style.right = "20px";
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
