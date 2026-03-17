/**
 * Chrome Storage Helper Utilities
 *
 * Wraps Chrome storage API calls in Promise-based helpers
 * for cleaner async/await usage.
 */

const StorageHelper = {
  /**
   * Get a value from Chrome sync storage.
   * @param {string} key - Storage key
   * @param {*} defaultValue - Default value if key not found
   * @returns {Promise<*>}
   */
  async get(key, defaultValue = null) {
    return new Promise((resolve) => {
      chrome.storage.sync.get({ [key]: defaultValue }, (result) => {
        resolve(result[key]);
      });
    });
  },

  /**
   * Set a value in Chrome sync storage.
   * @param {string} key - Storage key
   * @param {*} value - Value to store
   * @returns {Promise<void>}
   */
  async set(key, value) {
    return new Promise((resolve) => {
      chrome.storage.sync.set({ [key]: value }, resolve);
    });
  },

  /**
   * Get multiple values from Chrome sync storage.
   * @param {Object} defaults - Object with keys and default values
   * @returns {Promise<Object>}
   */
  async getMultiple(defaults) {
    return new Promise((resolve) => {
      chrome.storage.sync.get(defaults, resolve);
    });
  },

  /**
   * Get the configured backend API URL.
   * @returns {Promise<string>}
   */
  async getApiUrl() {
    const url = await this.get(
      GHL_ASSISTANT.STORAGE_KEYS.API_URL,
      GHL_ASSISTANT.API_BASE_URL
    );
    return url;
  },

  /**
   * Save the backend API URL.
   * @param {string} url
   * @returns {Promise<void>}
   */
  async setApiUrl(url) {
    return this.set(GHL_ASSISTANT.STORAGE_KEYS.API_URL, url);
  },
};
