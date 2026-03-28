/**
 * Backend API Client
 *
 * Handles communication between the Chrome Extension and the FastAPI backend.
 */

const ApiClient = {
  /**
   * Send a lead capture request to the backend.
   * @param {Object} leadData - Lead data to capture
   * @returns {Promise<Object>} API response
   */
  async captureLead(leadData) {
    const apiUrl = await StorageHelper.getApiUrl();
    return this._request("POST", `${apiUrl}/leads/capture`, leadData);
  },

  /**
   * Get recent leads from the backend.
   * @param {number} limit - Maximum number of leads
   * @param {string} query - Optional search query
   * @returns {Promise<Object>}
   */
  async getLeads(limit = 20, query = null) {
    const apiUrl = await StorageHelper.getApiUrl();
    const params = new URLSearchParams({ limit: String(limit) });
    if (query) params.set("query", query);
    return this._request("GET", `${apiUrl}/leads?${params.toString()}`);
  },

  /**
   * Check if a lead already exists by phone number.
   * @param {string} phone - Phone number to check
   * @returns {Promise<Object>}
   */
  async checkDuplicate(phone) {
    const apiUrl = await StorageHelper.getApiUrl();
    const params = new URLSearchParams({ phone });
    return this._request(
      "POST",
      `${apiUrl}/leads/duplicate-check?${params.toString()}`
    );
  },

  /**
   * Get available tags from the backend.
   * @returns {Promise<Object>}
   */
  async getTags() {
    const apiUrl = await StorageHelper.getApiUrl();
    return this._request("GET", `${apiUrl}/tags`);
  },

  /**
   * Test the backend connection.
   * @returns {Promise<Object>}
   */
  async healthCheck() {
    const apiUrl = await StorageHelper.getApiUrl();
    // Health check is at root, not under /api/v1
    const baseUrl = apiUrl.replace("/api/v1", "");
    return this._request("GET", `${baseUrl}/health`);
  },

  /**
   * Phase 2A: Find social profiles for an existing GHL contact.
   * Calls POST /leads/enrich — searches LinkedIn, Facebook, Instagram, TikTok
   * via Serper.dev and saves found URLs as GHL custom fields.
   *
   * @param {string} contactId - GHL contact ID
   * @param {Object} businessData - { business_name, website, city, state }
   * @returns {Promise<Object>} EnrichResponse with profiles_found, profiles_count, saved_to_ghl
   */
  async enrichLead(contactId, businessData) {
    const apiUrl = await StorageHelper.getApiUrl();
    return this._request("POST", `${apiUrl}/leads/enrich`, {
      contact_id: contactId,
      business_name: businessData.business_name || businessData.businessName || "",
      website: businessData.website || null,
      city: businessData.city || null,
      state: businessData.state || null,
    });
  },

  /**
   * Phase 2A: Draft a personalized email from a LinkedIn profile using AI.
   * Calls POST /leads/draft-email — fetches LinkedIn profile via Google Search
   * and uses GPT-4o-mini to draft a cold outreach email. Draft is saved as GHL note.
   *
   * @param {string} contactId - GHL contact ID
   * @param {Object} businessData - { business_name, linkedin_url }
   * @param {Object} senderInfo - { sender_name, sender_company, pitch } (all optional)
   * @returns {Promise<Object>} DraftEmailResponse with draft_email { subject, body }
   */
  async draftEmail(contactId, businessData, senderInfo = {}) {
    const apiUrl = await StorageHelper.getApiUrl();
    return this._request("POST", `${apiUrl}/leads/draft-email`, {
      contact_id: contactId,
      business_name: businessData.business_name || businessData.businessName || "",
      linkedin_url: businessData.linkedin_url || null,
      sender_name: senderInfo.sender_name || null,
      sender_company: senderInfo.sender_company || null,
      pitch: senderInfo.pitch || null,
    });
  },

  /**
   * Make an HTTP request to the backend API.
   * @param {string} method - HTTP method
   * @param {string} url - Full URL
   * @param {Object|null} body - Request body for POST/PUT
   * @returns {Promise<Object>} Parsed JSON response
   * @private
   */
  async _request(method, url, body = null) {
    const options = {
      method,
      headers: {
        "Content-Type": "application/json",
      },
    };

    if (body && (method === "POST" || method === "PUT")) {
      options.body = JSON.stringify(body);
    }

    try {
      const response = await fetch(url, options);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || `HTTP ${response.status}`);
      }

      return data;
    } catch (error) {
      if (error.message.includes("Failed to fetch") || error.message.includes("NetworkError")) {
        throw new Error(
          "Cannot connect to backend server. Please check that the server is running and the API URL is correct in extension settings."
        );
      }
      throw error;
    }
  },
};
