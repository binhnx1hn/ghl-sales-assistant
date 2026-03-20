/**
 * Review Popup Component
 *
 * Modal popup that shows extracted business data for review before
 * sending to GoHighLevel. Allows editing fields, adding notes,
 * selecting tags, and setting follow-up dates.
 */

const ReviewPopup = {
  _overlay: null,
  _popup: null,
  _currentData: null,

  /**
   * Show the review popup with pre-filled data.
   * @param {Object} data - Extracted business data
   */
  show(data) {
    this._currentData = data;
    this._createPopup(data);
  },

  /**
   * Hide and remove the review popup.
   */
  hide() {
    if (this._overlay) {
      this._overlay.classList.add(`${GHL_ASSISTANT.CSS_PREFIX}-popup-fade-out`);
      setTimeout(() => {
        this._overlay?.remove();
        this._overlay = null;
        this._popup = null;
        // Restore the floating button if user opened the popup from it.
        // EN: Keep UX consistent: user closes popup then can click again.
        FloatingButton?.onPopupClosed?.();
      }, 200);
    }
  },

  /**
   * Create the popup DOM elements with the extracted data.
   * @param {Object} data
   * @private
   */
  _createPopup(data) {
    // Remove existing popup if any
    this._overlay?.remove();

    // Create overlay
    this._overlay = document.createElement("div");
    this._overlay.className = `${GHL_ASSISTANT.CSS_PREFIX}-overlay`;
    this._overlay.addEventListener("click", (e) => {
      if (e.target === this._overlay) this.hide();
    });

    // Default follow-up: +3 calendar days in the user's local timezone.
    // Do not use toISOString() for the date part — it is UTC and shifts the
    // calendar day ahead of UTC (e.g. Asia) or can mismatch the date picker.
    const defaultFollowUp = new Date();
    defaultFollowUp.setDate(defaultFollowUp.getDate() + 3);
    const followUpStr = this._formatLocalDateYmd(defaultFollowUp);

    // Build tag checkboxes
    const tagCheckboxes = GHL_ASSISTANT.TAG_OPTIONS.map((tag) => {
      const isChecked =
        (data.tags && data.tags.includes(tag)) ||
        GHL_ASSISTANT.DEFAULT_TAGS.includes(tag) ||
        (tag === "Nursing Home" && (data.category || "").toLowerCase().includes("nursing"));
      return `
        <label class="${GHL_ASSISTANT.CSS_PREFIX}-tag-label">
          <input type="checkbox" value="${tag}" ${isChecked ? "checked" : ""} />
          <span>${tag}</span>
        </label>
      `;
    }).join("");

    // Create popup
    this._popup = document.createElement("div");
    this._popup.className = `${GHL_ASSISTANT.CSS_PREFIX}-popup`;
    this._popup.innerHTML = `
      <div class="${GHL_ASSISTANT.CSS_PREFIX}-popup-header">
        <h3>⚡ Send to GoHighLevel</h3>
        <button class="${GHL_ASSISTANT.CSS_PREFIX}-popup-close" title="Close">&times;</button>
      </div>

      <div class="${GHL_ASSISTANT.CSS_PREFIX}-popup-body">
        <div class="${GHL_ASSISTANT.CSS_PREFIX}-form-group">
          <label>Business Name *</label>
          <input type="text" id="${GHL_ASSISTANT.CSS_PREFIX}-name" value="${this._escapeHtml(data.businessName || "")}" />
        </div>

        <div class="${GHL_ASSISTANT.CSS_PREFIX}-form-row">
          <div class="${GHL_ASSISTANT.CSS_PREFIX}-form-group ${GHL_ASSISTANT.CSS_PREFIX}-form-half">
            <label>Phone</label>
            <input type="text" id="${GHL_ASSISTANT.CSS_PREFIX}-phone" value="${this._escapeHtml(data.phone || "")}" />
          </div>
          <div class="${GHL_ASSISTANT.CSS_PREFIX}-form-group ${GHL_ASSISTANT.CSS_PREFIX}-form-half">
            <label>Website</label>
            <input type="text" id="${GHL_ASSISTANT.CSS_PREFIX}-website" value="${this._escapeHtml(data.website || "")}" />
          </div>
        </div>

        <div class="${GHL_ASSISTANT.CSS_PREFIX}-form-group">
          <label>Address</label>
          <input type="text" id="${GHL_ASSISTANT.CSS_PREFIX}-address" value="${this._escapeHtml(data.address || "")}" />
        </div>

        <div class="${GHL_ASSISTANT.CSS_PREFIX}-form-row" style="display:none !important;">
          <div class="${GHL_ASSISTANT.CSS_PREFIX}-form-group ${GHL_ASSISTANT.CSS_PREFIX}-form-half">
            <label>City</label>
            <input type="text" id="${GHL_ASSISTANT.CSS_PREFIX}-city" value="${this._escapeHtml(data.city || "")}" />
          </div>
          <div class="${GHL_ASSISTANT.CSS_PREFIX}-form-group ${GHL_ASSISTANT.CSS_PREFIX}-form-half">
            <label>State</label>
            <input type="text" id="${GHL_ASSISTANT.CSS_PREFIX}-state" value="${this._escapeHtml(data.state || "")}" />
          </div>
        </div>

        <div class="${GHL_ASSISTANT.CSS_PREFIX}-form-group">
          <label>Quick Note</label>
          <textarea id="${GHL_ASSISTANT.CSS_PREFIX}-note" rows="3" placeholder="Add a note about this lead...">${this._escapeHtml(data.note || "")}</textarea>
        </div>

        <div class="${GHL_ASSISTANT.CSS_PREFIX}-form-group" style="display:none !important;">
          <label>Follow-up Date</label>
          <input type="date" id="${GHL_ASSISTANT.CSS_PREFIX}-followup" value="${data.followUpDate || followUpStr}" />
        </div>

        <div class="${GHL_ASSISTANT.CSS_PREFIX}-form-group">
          <label>Tags</label>
          <div class="${GHL_ASSISTANT.CSS_PREFIX}-tags-container">
            ${tagCheckboxes}
          </div>
          <div class="${GHL_ASSISTANT.CSS_PREFIX}-custom-tag">
            <input type="text" id="${GHL_ASSISTANT.CSS_PREFIX}-custom-tag-input" placeholder="Add custom tag..." />
            <button id="${GHL_ASSISTANT.CSS_PREFIX}-add-tag-btn" type="button">+</button>
          </div>
        </div>

        <div class="${GHL_ASSISTANT.CSS_PREFIX}-source-info">
          <small>Source: ${this._escapeHtml(data.sourceType || "unknown")} | ${this._escapeHtml(this._truncateUrl(data.sourceUrl || ""))}</small>
        </div>
      </div>

      <div class="${GHL_ASSISTANT.CSS_PREFIX}-popup-footer">
        <button class="${GHL_ASSISTANT.CSS_PREFIX}-btn ${GHL_ASSISTANT.CSS_PREFIX}-btn-cancel">Cancel</button>
        <button class="${GHL_ASSISTANT.CSS_PREFIX}-btn ${GHL_ASSISTANT.CSS_PREFIX}-btn-save">
          <span class="${GHL_ASSISTANT.CSS_PREFIX}-btn-save-text">Save to GHL</span>
          <span class="${GHL_ASSISTANT.CSS_PREFIX}-btn-save-loading" style="display:none;">Saving...</span>
        </button>
      </div>
    `;

    this._overlay.appendChild(this._popup);
    document.body.appendChild(this._overlay);

    // Attach event handlers
    this._attachEvents();
  },

  /**
   * Attach event handlers to popup elements.
   * @private
   */
  _attachEvents() {
    // Close button
    this._popup
      .querySelector(`.${GHL_ASSISTANT.CSS_PREFIX}-popup-close`)
      .addEventListener("click", () => this.hide());

    // Cancel button
    this._popup
      .querySelector(`.${GHL_ASSISTANT.CSS_PREFIX}-btn-cancel`)
      .addEventListener("click", () => this.hide());

    // Save button
    this._popup
      .querySelector(`.${GHL_ASSISTANT.CSS_PREFIX}-btn-save`)
      .addEventListener("click", () => this._onSave());

    // Custom tag add button
    const addTagBtn = this._popup.querySelector(
      `#${GHL_ASSISTANT.CSS_PREFIX}-add-tag-btn`
    );
    const customTagInput = this._popup.querySelector(
      `#${GHL_ASSISTANT.CSS_PREFIX}-custom-tag-input`
    );

    addTagBtn.addEventListener("click", () => {
      this._addCustomTag(customTagInput.value.trim());
      customTagInput.value = "";
    });

    customTagInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        this._addCustomTag(customTagInput.value.trim());
        customTagInput.value = "";
      }
    });

    // ESC key to close
    document.addEventListener("keydown", this._escHandler);
  },

  /**
   * ESC key handler to close the popup.
   * @param {KeyboardEvent} e
   * @private
   */
  _escHandler(e) {
    if (e.key === "Escape") {
      ReviewPopup.hide();
      document.removeEventListener("keydown", ReviewPopup._escHandler);
    }
  },

  /**
   * Add a custom tag to the tags container.
   * @param {string} tagName
   * @private
   */
  _addCustomTag(tagName) {
    if (!tagName) return;

    const container = this._popup.querySelector(
      `.${GHL_ASSISTANT.CSS_PREFIX}-tags-container`
    );

    // Check if tag already exists
    const existing = container.querySelector(`input[value="${tagName}"]`);
    if (existing) {
      existing.checked = true;
      return;
    }

    const label = document.createElement("label");
    label.className = `${GHL_ASSISTANT.CSS_PREFIX}-tag-label`;
    label.innerHTML = `
      <input type="checkbox" value="${this._escapeHtml(tagName)}" checked />
      <span>${this._escapeHtml(tagName)}</span>
    `;
    container.appendChild(label);
  },

  /**
   * Handle the save button click.
   * Collects form data and sends it to the background service worker.
   * @private
   */
  async _onSave() {
    const saveBtn = this._popup.querySelector(
      `.${GHL_ASSISTANT.CSS_PREFIX}-btn-save`
    );
    const saveText = saveBtn.querySelector(
      `.${GHL_ASSISTANT.CSS_PREFIX}-btn-save-text`
    );
    const saveLoading = saveBtn.querySelector(
      `.${GHL_ASSISTANT.CSS_PREFIX}-btn-save-loading`
    );

    // Show loading state
    saveText.style.display = "none";
    saveLoading.style.display = "inline";
    saveBtn.disabled = true;

    // Collect form data
    const formData = {
      business_name: this._getVal("name"),
      phone: this._getVal("phone"),
      website: this._getVal("website"),
      address: this._getVal("address"),
      city: this._getVal("city"),
      state: this._getVal("state"),
      source_url: this._currentData?.sourceUrl || window.location.href,
      source_type: this._currentData?.sourceType || "other",
      rating: this._currentData?.rating || "",
      category: this._currentData?.category || "",
      note: this._getVal("note"),
      follow_up_date: this._getVal("followup") || null,
      tags: this._getSelectedTags(),
    };

    // Validate required fields
    if (!formData.business_name) {
      this._showFormError("Business name is required.");
      saveText.style.display = "inline";
      saveLoading.style.display = "none";
      saveBtn.disabled = false;
      return;
    }

    // OPTIMISTIC UI: Close popup immediately, send to GHL in background.
    // This makes the extension feel instant (no waiting for GHL API ~1-2s).
    // If GHL fails, show an error notification after the fact.
    this.hide();
    this._showToast(
      `⏳ Saving ${formData.business_name} to GHL...`,
      "info"
    );

    // Defensive check: in some environments the `chrome.runtime` API
    // or `sendMessage` may not be available (e.g. if this script is
    // evaluated outside of a proper extension context).
    if (!window.chrome || !chrome.runtime || !chrome.runtime.sendMessage) {
      this._showToast(
        "❌ Cannot save lead: extension messaging API is unavailable on this page.",
        "error"
      );
      return;
    }

    // Fire and don't await - background handles it
    chrome.runtime.sendMessage(
      { action: "captureLead", data: formData },
      (response) => {
        if (chrome.runtime.lastError) {
          this._showToast(
            `❌ Failed to save: ${chrome.runtime.lastError.message}`,
            "error"
          );
          return;
        }
        if (response && response.success) {
          this._showToast(
            `✅ ${response.is_new ? "New lead" : "Lead updated"}: ${formData.business_name}`,
            "success"
          );
        } else {
          this._showToast(
            `❌ Error: ${response?.error || "Failed to save lead"}`,
            "error"
          );
        }
      }
    );
  },

  /**
   * Get selected tags from checkboxes.
   * @returns {Array<string>}
   * @private
   */
  _getSelectedTags() {
    const checkboxes = this._popup.querySelectorAll(
      `.${GHL_ASSISTANT.CSS_PREFIX}-tags-container input[type="checkbox"]:checked`
    );
    return Array.from(checkboxes).map((cb) => cb.value);
  },

  /**
   * Get a form field value by ID suffix.
   * @param {string} idSuffix
   * @returns {string}
   * @private
   */
  _getVal(idSuffix) {
    const el = this._popup.querySelector(
      `#${GHL_ASSISTANT.CSS_PREFIX}-${idSuffix}`
    );
    return el ? el.value.trim() : "";
  },

  /**
   * Show an error message inside the form.
   * @param {string} message
   * @private
   */
  _showFormError(message) {
    // Remove existing error
    const existing = this._popup.querySelector(
      `.${GHL_ASSISTANT.CSS_PREFIX}-form-error`
    );
    if (existing) existing.remove();

    const error = document.createElement("div");
    error.className = `${GHL_ASSISTANT.CSS_PREFIX}-form-error`;
    error.textContent = message;

    const footer = this._popup.querySelector(
      `.${GHL_ASSISTANT.CSS_PREFIX}-popup-footer`
    );
    footer.insertBefore(error, footer.firstChild);

    setTimeout(() => error.remove(), 5000);
  },

  /**
   * Show a toast notification on the page.
   * Info toasts auto-dismiss after 1.5s (they're transient "saving..." messages).
   * Success/error toasts stay for 3s.
   * @param {string} message
   * @param {string} type - "success" or "error"
   * @private
   */
  _showToast(message, type = "success") {
    // Remove any existing info toast when new toast arrives
    const existingInfo = document.querySelector(
      `.${GHL_ASSISTANT.CSS_PREFIX}-toast-info`
    );
    if (existingInfo) existingInfo.remove();

    const toast = document.createElement("div");
    toast.className = `${GHL_ASSISTANT.CSS_PREFIX}-toast ${GHL_ASSISTANT.CSS_PREFIX}-toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    // Info toasts disappear faster (they're just "saving..." indicators)
    const duration = type === "info" ? 1500 : 3000;
    setTimeout(() => {
      toast.classList.add(`${GHL_ASSISTANT.CSS_PREFIX}-toast-fade`);
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  /**
   * Escape HTML special characters to prevent XSS.
   * @param {string} str
   * @returns {string}
   * @private
   */
  _escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  },

  /**
   * Truncate a URL for display.
   * @param {string} url
   * @returns {string}
   * @private
   */
  _truncateUrl(url) {
    if (!url) return "";
    try {
      const u = new URL(url);
      const path = u.pathname.length > 30 ? u.pathname.substring(0, 30) + "..." : u.pathname;
      return u.hostname + path;
    } catch {
      return url.length > 50 ? url.substring(0, 50) + "..." : url;
    }
  },

  /**
   * Format a Date as YYYY-MM-DD in local timezone (for type="date" inputs).
   * @param {Date} d
   * @returns {string}
   * @private
   */
  _formatLocalDateYmd(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  },
};
