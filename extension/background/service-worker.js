/**
 * Background Service Worker
 *
 * Handles messages from content scripts and popup,
 * coordinates API calls to the backend server.
 */

// Import utilities (service workers use importScripts in MV3)
importScripts("../utils/constants.js", "../utils/storage.js", "../utils/api.js");

/**
 * Listen for messages from content scripts and popup.
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "captureLead") {
    handleCaptureLead(message.data)
      .then(sendResponse)
      .catch((error) => {
        sendResponse({
          success: false,
          error: error.message || "Unknown error occurred",
        });
      });
    // Return true to indicate we'll send a response asynchronously
    return true;
  }

  if (message.action === "getLeads") {
    ApiClient.getLeads(message.limit, message.query)
      .then(sendResponse)
      .catch((error) => {
        sendResponse({
          success: false,
          error: error.message,
        });
      });
    return true;
  }

  if (message.action === "getTags") {
    ApiClient.getTags()
      .then(sendResponse)
      .catch((error) => {
        sendResponse({
          success: false,
          error: error.message,
        });
      });
    return true;
  }

  if (message.action === "healthCheck") {
    ApiClient.healthCheck()
      .then(sendResponse)
      .catch((error) => {
        sendResponse({
          success: false,
          error: error.message,
        });
      });
    return true;
  }

  if (message.action === "checkDuplicate") {
    ApiClient.checkDuplicate(message.phone)
      .then(sendResponse)
      .catch((error) => {
        sendResponse({
          success: false,
          error: error.message,
        });
      });
    return true;
  }
});

/**
 * Handle the lead capture request.
 * @param {Object} leadData - Lead data from the content script
 * @returns {Promise<Object>} Result of the capture operation
 */
async function handleCaptureLead(leadData) {
  try {
    const result = await ApiClient.captureLead(leadData);
    return {
      success: true,
      ...result,
    };
  } catch (error) {
    console.error("[GHL Assistant] Lead capture failed:", error);
    return {
      success: false,
      error: error.message || "Failed to capture lead",
    };
  }
}

/**
 * Handle extension installation or update.
 */
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    console.log("[GHL Assistant] Extension installed successfully.");
    // Open options page on first install
    chrome.runtime.openOptionsPage();
  } else if (details.reason === "update") {
    console.log(
      `[GHL Assistant] Extension updated to version ${chrome.runtime.getManifest().version}`
    );
  }
});
