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
  // Phase 2A: store last captured contact_id for enrichment/email drafting
  _lastContactId: null,
  _lastFormData: null,

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

    // Build industry radio buttons (single selection)
    const categoryLower = (data.category || "").toLowerCase();
    const autoIndustry = GHL_ASSISTANT.INDUSTRY_OPTIONS.find((opt) =>
      categoryLower.includes(opt.toLowerCase().split("/")[0].trim())
    ) || "";
    const industryRadios = GHL_ASSISTANT.INDUSTRY_OPTIONS.map((opt) => {
      const isChecked = opt === autoIndustry;
      return `
        <label class="${GHL_ASSISTANT.CSS_PREFIX}-tag-label">
          <input type="radio" name="${GHL_ASSISTANT.CSS_PREFIX}-industry" value="${opt}" ${isChecked ? "checked" : ""} />
          <span>${opt}</span>
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
          <label>Industry</label>
          <div class="${GHL_ASSISTANT.CSS_PREFIX}-tags-container">
            ${industryRadios}
          </div>
        </div>

        <div class="${GHL_ASSISTANT.CSS_PREFIX}-form-group">
          <label>Social Profiles</label>
          <div class="${GHL_ASSISTANT.CSS_PREFIX}-social-inputs">
            <div class="${GHL_ASSISTANT.CSS_PREFIX}-social-row">
              <img class="${GHL_ASSISTANT.CSS_PREFIX}-social-icon" src="https://ssl.gstatic.com/kpui/social/linkedin_32x32.png" alt="LinkedIn" title="LinkedIn" width="22" height="22" />
              <input type="url" id="${GHL_ASSISTANT.CSS_PREFIX}-linkedin" placeholder="https://linkedin.com/company/..." value="${this._escapeHtml((data.socialLinks || {}).linkedin || "")}" />
            </div>
            <div class="${GHL_ASSISTANT.CSS_PREFIX}-social-row">
              <img class="${GHL_ASSISTANT.CSS_PREFIX}-social-icon" src="https://ssl.gstatic.com/kpui/social/fb_32x32.png" alt="Facebook" title="Facebook" width="22" height="22" />
              <input type="url" id="${GHL_ASSISTANT.CSS_PREFIX}-facebook" placeholder="https://facebook.com/..." value="${this._escapeHtml((data.socialLinks || {}).facebook || "")}" />
            </div>
            <div class="${GHL_ASSISTANT.CSS_PREFIX}-social-row">
              <img class="${GHL_ASSISTANT.CSS_PREFIX}-social-icon" src="https://ssl.gstatic.com/kpui/social/instagram_32x32.png" alt="Instagram" title="Instagram" width="22" height="22" />
              <input type="url" id="${GHL_ASSISTANT.CSS_PREFIX}-instagram" placeholder="https://instagram.com/..." value="${this._escapeHtml((data.socialLinks || {}).instagram || "")}" />
            </div>
            <div class="${GHL_ASSISTANT.CSS_PREFIX}-social-row">
              <img class="${GHL_ASSISTANT.CSS_PREFIX}-social-icon" src="https://ssl.gstatic.com/kpui/social/tiktok_32x32.png" alt="TikTok" title="TikTok" width="22" height="22" />
              <input type="url" id="${GHL_ASSISTANT.CSS_PREFIX}-tiktok" placeholder="https://tiktok.com/@..." value="${this._escapeHtml((data.socialLinks || {}).tiktok || "")}" />
            </div>
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
      industry: this._getSelectedIndustry(),
      // Social links — read from editable inputs (user may have corrected them)
      // Use snake_case to match backend Pydantic model field: social_links
      social_links: {
        linkedin: this._getVal("linkedin"),
        facebook: this._getVal("facebook"),
        instagram: this._getVal("instagram"),
        tiktok: this._getVal("tiktok"),
      },
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

    // When chrome.runtime.sendMessage is unavailable (e.g. after extension reload
    // without page refresh), fall back to calling ApiClient directly from the
    // content script — both paths hit the same backend endpoint.
    const messagingAvailable =
      typeof chrome !== "undefined" &&
      chrome.runtime &&
      typeof chrome.runtime.sendMessage === "function";

    if (!messagingAvailable) {
      // Direct API call fallback
      try {
        const response = await ApiClient.captureLead(formData);
        this._handleSaveResponse(response, formData, contactId);
      } catch (err) {
        this._showToast(`❌ Failed to save: ${err.message}`, "error");
      }
      return;
    }

    // Normal path: route through service worker
    chrome.runtime.sendMessage(
      { action: "captureLead", data: formData },
      (response) => {
        if (chrome.runtime.lastError) {
          // Service worker disconnected — retry via direct API
          ApiClient.captureLead(formData)
            .then((r) => this._handleSaveResponse(r, formData, contactId))
            .catch((err) => this._showToast(`❌ Failed to save: ${err.message}`, "error"));
          return;
        }
        this._handleSaveResponse(response, formData);
      }
    );
  },

  /**
   * Handle the API response after saving a lead (shared by messaging and direct API paths).
   * @param {Object} response
   * @param {Object} formData
   * @private
   */
  _handleSaveResponse(response, formData) {
    if (response && response.success) {
      this._showToast(
        `✅ ${response.is_new ? "New lead" : "Lead updated"}: ${formData.business_name}`,
        "success"
      );
      if (response.contact_id) {
        this._lastContactId = response.contact_id;
        this._lastFormData = formData;
        this._showPhase2Panel(formData, response.contact_id);
      }
    } else {
      this._showToast(
        `❌ Error: ${response?.error || "Failed to save lead"}`,
        "error"
      );
    }
  },

  /**
   * Phase 2A: Show the AI enrichment panel after successful lead save.
   * Renders a floating panel with "Find Social Profiles" and "Draft Email" buttons.
   *
   * @param {Object} formData - The form data that was just saved
   * @param {string} contactId - GHL contact ID returned from capture
   * @private
   */
  _showPhase2Panel(formData, contactId) {
    // Remove any existing Phase 2 panel
    const existing = document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-phase2-panel`);
    if (existing) existing.remove();

    // Check for pre-extracted social links from DOM
    const preLinks = formData.social_links || { linkedin: "", facebook: "", instagram: "", tiktok: "" };
    const preFound = Object.values(preLinks).filter(Boolean).length;
    const hasPreLinks = preFound > 0;

    const panel = document.createElement("div");
    panel.id = `${GHL_ASSISTANT.CSS_PREFIX}-phase2-panel`;
    panel.style.cssText = `
      position: fixed;
      bottom: 80px;
      right: 20px;
      background: #1a1a2e;
      border: 1px solid #4a4a8a;
      border-radius: 12px;
      padding: 16px;
      z-index: 2147483646;
      min-width: 280px;
      max-width: 320px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.4);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      color: #fff;
    `;

    // Build pre-found social links summary for display
    const preFoundLinks = [];
    if (preLinks.linkedin) preFoundLinks.push(`<a href="${preLinks.linkedin}" target="_blank" style="color:#a78bfa;">LinkedIn</a>`);
    if (preLinks.facebook) preFoundLinks.push(`<a href="${preLinks.facebook}" target="_blank" style="color:#60a5fa;">Facebook</a>`);
    if (preLinks.instagram) preFoundLinks.push(`<a href="${preLinks.instagram}" target="_blank" style="color:#f472b6;">Instagram</a>`);
    if (preLinks.tiktok) preFoundLinks.push(`<a href="${preLinks.tiktok}" target="_blank" style="color:#34d399;">TikTok</a>`);

    const enrichBtnLabel = hasPreLinks
      ? `<span>✅</span><div><div>${preFound} profile${preFound !== 1 ? "s" : ""} found on page</div><div style="font-size:11px; opacity:0.8; font-weight:400;">Click to search for more</div></div>`
      : `<span>🔍</span><div><div>Find Social Profiles</div><div style="font-size:11px; opacity:0.8; font-weight:400;">LinkedIn · Facebook · Instagram · TikTok</div></div>`;

    panel.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <div style="font-size:13px; font-weight:600; color:#a78bfa;">
          🤖 AI Actions for ${this._escapeHtml(formData.business_name || "")}
        </div>
        <button id="${GHL_ASSISTANT.CSS_PREFIX}-phase2-close"
          style="background:none;border:none;color:#888;cursor:pointer;font-size:18px;line-height:1;padding:0 4px;">
          ×
        </button>
      </div>
      ${hasPreLinks ? `<div style="margin-bottom:10px; font-size:12px; color:#9ca3af;">Found on page: ${preFoundLinks.join(" · ")}</div>` : ""}
      <div style="display:flex; flex-direction:column; gap:8px;">
        <button id="${GHL_ASSISTANT.CSS_PREFIX}-btn-enrich"
          style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; border: none; border-radius: 8px;
            padding: 10px 14px; font-size: 13px; font-weight: 600;
            cursor: pointer; text-align: left; display: flex;
            align-items: center; gap: 8px; transition: opacity 0.2s;
          ">
          ${enrichBtnLabel}
        </button>
        <button id="${GHL_ASSISTANT.CSS_PREFIX}-btn-draft"
          style="
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white; border: none; border-radius: 8px;
            padding: 10px 14px; font-size: 13px; font-weight: 600;
            cursor: pointer; text-align: left; display: flex;
            align-items: center; gap: 8px; transition: opacity 0.2s;
          ">
          <span>✉️</span>
          <div>
            <div>Draft Email from LinkedIn</div>
            <div style="font-size:11px; opacity:0.8; font-weight:400;">AI-personalized outreach email</div>
          </div>
        </button>
      </div>
      <div id="${GHL_ASSISTANT.CSS_PREFIX}-phase2-status" style="margin-top:10px; font-size:12px; color:#888; min-height:16px;"></div>
    `;

    document.body.appendChild(panel);

    // Auto-remove after 30 seconds
    const autoRemoveTimer = setTimeout(() => panel.remove(), 30000);

    // Close button handler
    document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-phase2-close`)
      .addEventListener("click", () => {
        clearTimeout(autoRemoveTimer);
        panel.remove();
      });

    // Pre-set linkedin_url on draft button if already found from DOM extraction
    const draftBtnEl = document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-btn-draft`);
    if (draftBtnEl && preLinks.linkedin) {
      draftBtnEl.dataset.linkedinUrl = preLinks.linkedin;
    }

    // Find Social Profiles handler
    document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-btn-enrich`)
      .addEventListener("click", () => this._onEnrichLead(formData, contactId, panel, autoRemoveTimer));

    // Draft Email handler
    draftBtnEl.addEventListener("click", () => this._onDraftEmail(formData, contactId, panel, autoRemoveTimer));
  },

  /**
   * Phase 2A: Handle "Find Social Profiles" button click.
   * Calls the /leads/enrich endpoint and shows results in the panel.
   *
   * @param {Object} formData - Lead form data
   * @param {string} contactId - GHL contact ID
   * @param {HTMLElement} panel - The Phase 2 panel element
   * @param {number} autoRemoveTimer - Timer ID for auto-remove
   * @private
   */
  async _onEnrichLead(formData, contactId, panel, autoRemoveTimer) {
    const enrichBtn = document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-btn-enrich`);
    const statusEl = document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-phase2-status`);

    enrichBtn.disabled = true;
    enrichBtn.style.opacity = "0.6";
    if (statusEl) statusEl.textContent = "🔍 Searching social profiles...";

    try {
      const result = await ApiClient.enrichLead(contactId, formData);

      if (result.success) {
        const count = result.profiles_count || 0;
        const profiles = result.profiles_found || {};
        const candidates = result.candidates || {};

        enrichBtn.innerHTML = `<span>🔍</span><div><div>${count} profile${count !== 1 ? "s" : ""} found</div><div style="font-size:11px;opacity:0.8;">Review before saving</div></div>`;

        if (count === 0) {
          if (statusEl) statusEl.textContent = "No public profiles found for this business.";
          enrichBtn.disabled = false;
          enrichBtn.style.opacity = "1";
          return;
        }

        // Store editable state per platform (start as display mode)
        const platformMeta = [
          { key: "linkedin", label: "LinkedIn", color: "#a78bfa", icon: "https://ssl.gstatic.com/kpui/social/linkedin_32x32.png" },
          { key: "facebook", label: "Facebook", color: "#60a5fa", icon: "https://ssl.gstatic.com/kpui/social/fb_32x32.png" },
          { key: "instagram", label: "Instagram", color: "#f472b6", icon: "https://ssl.gstatic.com/kpui/social/instagram_32x32.png" },
          { key: "tiktok", label: "TikTok", color: "#34d399", icon: "https://ssl.gstatic.com/kpui/social/tiktok_32x32.png" },
        ];

        // Mutable copy of profiles the user can edit
        const editedProfiles = {
          linkedin: profiles.linkedin || "",
          facebook: profiles.facebook || "",
          instagram: profiles.instagram || "",
          tiktok: profiles.tiktok || "",
        };

        // Checkbox intent state — checked = user wants to save this platform
        const checkedPlatforms = {
          linkedin: !!profiles.linkedin,
          facebook: !!profiles.facebook,
          instagram: !!profiles.instagram,
          tiktok: !!profiles.tiktok,
        };

        const renderCandidatePicker = (key, onDone) => {
          const meta = platformMeta.find(p => p.key === key);
          const list = (candidates[key] || []);
          const current = editedProfiles[key] || "";

          const itemsHtml = list.map((url, i) => {
            const isSelected = url === current;
            const handle = url.split("/").filter(Boolean).pop() || url;
            return `
              <label style="
                display:flex;align-items:center;gap:6px;padding:5px 6px;border-radius:5px;cursor:pointer;
                background:${isSelected ? "rgba(124,58,237,0.25)" : "rgba(255,255,255,0.04)"};
                border:1px solid ${isSelected ? "#7C3AED" : "rgba(255,255,255,0.1)"};
                font-size:11px;
              ">
                <input type="radio" name="${GHL_ASSISTANT.CSS_PREFIX}-pick-${key}" value="${url}" ${isSelected ? "checked" : ""}
                  style="accent-color:#7C3AED;cursor:pointer;" />
                <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#d1d5db;" title="${url}">
                  ${handle}
                </span>
                <a href="${url}" target="_blank" style="color:#6b7280;font-size:10px;flex-shrink:0;" onclick="event.stopPropagation()">↗</a>
              </label>
            `;
          }).join("");

          const noneItem = `
            <label style="
              display:flex;align-items:center;gap:6px;padding:5px 6px;border-radius:5px;cursor:pointer;
              background:${!current ? "rgba(239,68,68,0.15)" : "rgba(255,255,255,0.04)"};
              border:1px solid ${!current ? "#ef4444" : "rgba(255,255,255,0.1)"};
              font-size:11px;
            ">
              <input type="radio" name="${GHL_ASSISTANT.CSS_PREFIX}-pick-${key}" value="" ${!current ? "checked" : ""}
                style="accent-color:#ef4444;cursor:pointer;" />
              <span style="color:#9ca3af;">None / skip this platform</span>
            </label>
          `;

          return `
            <div style="margin-top:8px;padding:8px;background:rgba(0,0,0,0.2);border-radius:8px;border:1px solid rgba(255,255,255,0.1);">
              <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
                <img src="${meta.icon}" width="14" height="14" style="border-radius:3px;" />
                <span style="font-size:12px;font-weight:600;color:${meta.color};">${meta.label}</span>
                <span style="font-size:10px;opacity:0.5;margin-left:auto;">${list.length} candidate${list.length !== 1 ? "s" : ""}</span>
              </div>
              <div id="${GHL_ASSISTANT.CSS_PREFIX}-pick-list-${key}" style="display:flex;flex-direction:column;gap:4px;">
                ${itemsHtml}
                ${noneItem}
              </div>
              <div style="display:flex;gap:4px;margin-top:6px;">
                <input id="${GHL_ASSISTANT.CSS_PREFIX}-pick-custom-${key}" type="url"
                  placeholder="Or paste custom URL..."
                  style="flex:1;background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.2);
                    border-radius:4px;padding:4px 7px;color:#fff;font-size:11px;outline:none;" />
              </div>
              <button id="${GHL_ASSISTANT.CSS_PREFIX}-pick-ok-${key}" data-key="${key}"
                style="margin-top:6px;width:100%;padding:5px;background:#4F46E5;border:none;border-radius:5px;
                  color:#fff;font-size:11px;font-weight:600;cursor:pointer;">
                ✓ Use selected
              </button>
            </div>
          `;
        };

        const renderProfileLinks = () => {
          const rowsHtml = platformMeta.map(({ key, label, color, icon }) => {
            const url = editedProfiles[key] || "";
            const candidateCount = (candidates[key] || []).length;
            const hasCandidates = candidateCount > 0;
            const isChecked = checkedPlatforms[key];
            const hasUrl = !!url;
            const isDisabled = !hasUrl && !hasCandidates;

            const truncated = url.length > 35 ? url.slice(0, 32) + "…" : url;

            const urlHtml = hasUrl
              ? `<a href="${url}" target="_blank"
                   style="color:#9ca3af;font-size:11px;text-decoration:none;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
                   onclick="event.stopPropagation()" title="${url}">${truncated}</a>`
              : `<span style="color:#6b7280;font-size:11px;flex:1;">not found</span>`;

            const badgeHtml = candidateCount > 1
              ? `<span style="font-size:9px;background:rgba(124,58,237,0.4);border-radius:3px;padding:1px 4px;color:#c4b5fd;flex-shrink:0;" data-edit-key="${key}">▾${candidateCount}</span>`
              : "";

            return `
              <div style="display:flex;align-items:center;gap:8px;padding:5px 6px;border-radius:6px;cursor:pointer;
                background:rgba(255,255,255,0.03);margin-bottom:4px;border:1px solid rgba(255,255,255,0.07);
                opacity:${isDisabled ? 0.4 : 1};"
                data-row-key="${key}">
                <input type="checkbox"
                  id="${GHL_ASSISTANT.CSS_PREFIX}-chk-${key}"
                  ${isChecked ? "checked" : ""}
                  ${isDisabled ? "disabled" : ""}
                  style="accent-color:#7C3AED;cursor:${isDisabled ? "default" : "pointer"};flex-shrink:0;"
                  data-chk-key="${key}" />
                <img src="${icon}" width="14" height="14" style="border-radius:3px;flex-shrink:0;" data-edit-key="${key}" />
                <span style="color:${color};font-size:12px;font-weight:500;flex-shrink:0;min-width:60px;" data-edit-key="${key}">${label}</span>
                ${urlHtml}
                ${badgeHtml}
              </div>
            `;
          }).join("");

          return `
            <div style="margin-top:6px;">
              <div style="margin-bottom:4px;">${rowsHtml}</div>
              <button id="${GHL_ASSISTANT.CSS_PREFIX}-enrich-confirm" style="
                margin-top:4px;width:100%;padding:7px;background:#7C3AED;border:none;border-radius:6px;
                color:#fff;font-size:12px;font-weight:600;cursor:pointer;">
                ✅ Confirm & Save to GHL
              </button>
            </div>
          `;
        };

        const renderEditInput = (key) => {
          const hasCandidates = (candidates[key] || []).length > 0;
          if (hasCandidates) {
            return renderCandidatePicker(key, () => showLinks());
          }
          const meta = platformMeta.find(p => p.key === key);
          return `
            <div style="margin-top:6px;">
              <div style="font-size:11px;opacity:0.6;margin-bottom:4px;">Edit ${meta.label} URL:</div>
              <div style="display:flex;gap:4px;align-items:center;">
                <img src="${meta.icon}" width="16" height="16" style="border-radius:3px;flex-shrink:0;" />
                <input id="${GHL_ASSISTANT.CSS_PREFIX}-enrich-edit-input" type="url"
                  value="${editedProfiles[key]}"
                  placeholder="${meta.label} URL"
                  style="flex:1;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.3);border-radius:4px;padding:5px 8px;color:#fff;font-size:12px;outline:none;" />
                <button id="${GHL_ASSISTANT.CSS_PREFIX}-enrich-edit-ok" data-key="${key}" style="padding:5px 8px;background:#4F46E5;border:none;border-radius:4px;color:#fff;font-size:11px;cursor:pointer;">OK</button>
              </div>
            </div>
          `;
        };

        // Show profile links in statusEl
        if (statusEl) {
          // Helper: attach candidate picker or plain-edit handlers after renderEditInput
          // Declared before showLinks so it is in scope when showLinks references it
          const _attachPickerHandlers = (key) => {
            // Candidate picker flow
            const okBtn = document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-pick-ok-${key}`);
            if (okBtn) {
              okBtn.addEventListener("click", () => {
                const customInput = document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-pick-custom-${key}`);
                const customVal = customInput?.value?.trim();
                if (customVal) {
                  editedProfiles[key] = customVal;
                } else {
                  const selected = statusEl.querySelector(`input[name="${GHL_ASSISTANT.CSS_PREFIX}-pick-${key}"]:checked`);
                  editedProfiles[key] = selected?.value || "";
                }
                // Auto-check if a URL was set
                if (editedProfiles[key]) checkedPlatforms[key] = true;
                showLinks();
              });
            }

            // Plain edit input flow (no candidates)
            const plainOkBtn = document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-enrich-edit-ok`);
            if (plainOkBtn) {
              const input = document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-enrich-edit-input`);
              if (input) input.focus();
              plainOkBtn.addEventListener("click", () => {
                const val = document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-enrich-edit-input`)?.value || "";
                editedProfiles[plainOkBtn.dataset.key] = val.trim();
                // Auto-check if a URL was set
                if (editedProfiles[plainOkBtn.dataset.key]) checkedPlatforms[plainOkBtn.dataset.key] = true;
                showLinks();
              });
            }
          };

          const showLinks = () => {
            statusEl.innerHTML = renderProfileLinks();

            // Attach checkbox change handlers
            statusEl.querySelectorAll("[data-chk-key]").forEach(chk => {
              chk.addEventListener("change", (e) => {
                e.stopPropagation();
                const key = chk.dataset.chkKey;
                checkedPlatforms[key] = chk.checked;
                // If user checks a platform that has no URL but has candidates, open picker
                if (chk.checked && !editedProfiles[key] && (candidates[key] || []).length > 0) {
                  statusEl.innerHTML = renderEditInput(key);
                  _attachPickerHandlers(key);
                }
              });
            });

            // Attach edit triggers on row cells (icon, label, badge — not checkbox, not URL link)
            statusEl.querySelectorAll("[data-edit-key]").forEach(el => {
              el.addEventListener("click", (e) => {
                if (e.target.tagName === "A") return; // let link open
                const key = el.dataset.editKey || el.closest("[data-edit-key]")?.dataset.editKey;
                if (!key) return;
                statusEl.innerHTML = renderEditInput(key);
                _attachPickerHandlers(key);
              });
            });

            // Row-level click: clicking anywhere on the row (not checkbox, not URL) triggers edit
            statusEl.querySelectorAll("[data-row-key]").forEach(row => {
              row.addEventListener("click", (e) => {
                if (e.target.tagName === "A") return;
                if (e.target.tagName === "INPUT" && e.target.type === "checkbox") return;
                const key = row.dataset.rowKey;
                if (!key) return;
                statusEl.innerHTML = renderEditInput(key);
                _attachPickerHandlers(key);
              });
            });

            // Confirm save button
            const confirmBtn = document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-enrich-confirm`);
            if (confirmBtn) {
              confirmBtn.addEventListener("click", async () => {
                confirmBtn.disabled = true;
                confirmBtn.textContent = "Saving...";
                try {
                  // Sync checkbox state from DOM before saving
                  platformMeta.forEach(({ key }) => {
                    const chk = document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-chk-${key}`);
                    if (chk) checkedPlatforms[key] = chk.checked;
                  });

                  // Build profiles to save: only checked + non-empty urls; unchecked = ""
                  const profilesToSave = {};
                  platformMeta.forEach(({ key }) => {
                    profilesToSave[key] = (checkedPlatforms[key] && editedProfiles[key]) ? editedProfiles[key] : "";
                  });

                  await ApiClient.saveProfiles(contactId, profilesToSave);
                  const savedCount = Object.values(profilesToSave).filter(Boolean).length;
                  enrichBtn.innerHTML = `<span>✅</span><div><div>${savedCount} profile${savedCount !== 1 ? "s" : ""} saved</div><div style="font-size:11px;opacity:0.8;">Saved to GHL contact</div></div>`;
                  statusEl.textContent = "✅ Social profiles saved to GHL.";
                  const draftBtn = document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-btn-draft`);
                  if (draftBtn && profilesToSave.linkedin) {
                    draftBtn.dataset.linkedinUrl = profilesToSave.linkedin;
                  }
                } catch (saveErr) {
                  confirmBtn.disabled = false;
                  confirmBtn.textContent = `❌ Save failed: ${saveErr.message}`;
                }
              });
            }
          };

          showLinks();

        }
      } else {
        if (statusEl) statusEl.textContent = "⚠️ Search completed but no profiles found.";
        enrichBtn.disabled = false;
        enrichBtn.style.opacity = "1";
      }
    } catch (err) {
      if (statusEl) statusEl.textContent = `❌ Error: ${err.message}`;
      enrichBtn.disabled = false;
      enrichBtn.style.opacity = "1";
    }

    clearTimeout(autoRemoveTimer);
  },

  /**
   * Phase 2A: Handle "Draft Email from LinkedIn" button click.
   * Calls the /leads/draft-email endpoint and shows the draft in the panel.
   *
   * @param {Object} formData - Lead form data
   * @param {string} contactId - GHL contact ID
   * @param {HTMLElement} panel - The Phase 2 panel element
   * @param {number} autoRemoveTimer - Timer ID for auto-remove
   * @private
   */
  async _onDraftEmail(formData, contactId, panel, autoRemoveTimer) {
    const draftBtn = document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-btn-draft`);
    const statusEl = document.getElementById(`${GHL_ASSISTANT.CSS_PREFIX}-phase2-status`);

    // Get LinkedIn URL if previously found by enrichment
    const linkedinUrl = draftBtn?.dataset?.linkedinUrl || null;

    draftBtn.disabled = true;
    draftBtn.style.opacity = "0.6";
    if (statusEl) statusEl.textContent = "✉️ AI is drafting your email...";

    try {
      const result = await ApiClient.draftEmail(contactId, {
        ...formData,
        linkedin_url: linkedinUrl,
      });

      if (result.success && result.draft_email) {
        const { subject, body } = result.draft_email;

        draftBtn.innerHTML = `<span>✅</span><div><div>Email Draft Ready</div><div style="font-size:11px;opacity:0.8;">Saved to GHL Notes</div></div>`;

        // Show a preview of the draft in an expandable section
        const previewDiv = document.createElement("div");
        previewDiv.style.cssText = `
          margin-top: 10px;
          background: rgba(255,255,255,0.05);
          border-radius: 8px;
          padding: 10px;
          font-size: 12px;
          line-height: 1.5;
          max-height: 150px;
          overflow-y: auto;
          color: #d1d5db;
        `;
        previewDiv.innerHTML = `
          <div style="color:#a78bfa; font-weight:600; margin-bottom:4px;">Subject: ${this._escapeHtml(subject)}</div>
          <div style="white-space:pre-wrap;">${this._escapeHtml(body)}</div>
        `;
        panel.appendChild(previewDiv);

        if (statusEl) statusEl.textContent = result.saved_as_note
          ? "📋 Draft saved to GHL Notes — review before sending"
          : "⚠️ Draft ready but could not save to GHL Notes";

      } else {
        if (statusEl) statusEl.textContent = "⚠️ Could not generate email draft.";
        draftBtn.disabled = false;
        draftBtn.style.opacity = "1";
      }
    } catch (err) {
      if (statusEl) statusEl.textContent = `❌ Error: ${err.message}`;
      draftBtn.disabled = false;
      draftBtn.style.opacity = "1";
    }

    clearTimeout(autoRemoveTimer);
  },

  /**
   * Get the selected industry from radio buttons.
   * @returns {string}
   * @private
   */
  _getSelectedIndustry() {
    const checked = this._popup.querySelector(
      `input[name="${GHL_ASSISTANT.CSS_PREFIX}-industry"]:checked`
    );
    return checked ? checked.value : "";
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
