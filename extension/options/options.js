/**
 * Extension Options Page Script
 *
 * Manages extension settings including backend URL,
 * default tags, and market configuration.
 */

document.addEventListener("DOMContentLoaded", async () => {
  // Load saved settings
  await loadSettings();

  // Test connection button
  document.getElementById("btn-test").addEventListener("click", testConnection);

  // Save settings button
  document.getElementById("btn-save").addEventListener("click", saveSettings);
});

/**
 * Load saved settings from Chrome storage and populate form fields.
 */
async function loadSettings() {
  const settings = await StorageHelper.getMultiple({
    [GHL_ASSISTANT.STORAGE_KEYS.API_URL]: GHL_ASSISTANT.API_BASE_URL,
    [GHL_ASSISTANT.STORAGE_KEYS.DEFAULT_TAGS]: GHL_ASSISTANT.DEFAULT_TAGS.join(", "),
    [GHL_ASSISTANT.STORAGE_KEYS.DEFAULT_MARKET]: "",
  });

  document.getElementById("api-url").value =
    settings[GHL_ASSISTANT.STORAGE_KEYS.API_URL];
  document.getElementById("default-tags").value =
    typeof settings[GHL_ASSISTANT.STORAGE_KEYS.DEFAULT_TAGS] === "string"
      ? settings[GHL_ASSISTANT.STORAGE_KEYS.DEFAULT_TAGS]
      : settings[GHL_ASSISTANT.STORAGE_KEYS.DEFAULT_TAGS].join(", ");
  document.getElementById("default-market").value =
    settings[GHL_ASSISTANT.STORAGE_KEYS.DEFAULT_MARKET];
}

/**
 * Save settings to Chrome storage.
 */
async function saveSettings() {
  const apiUrl = document.getElementById("api-url").value.trim();
  const defaultTags = document.getElementById("default-tags").value.trim();
  const defaultMarket = document.getElementById("default-market").value.trim();

  await StorageHelper.set(GHL_ASSISTANT.STORAGE_KEYS.API_URL, apiUrl || GHL_ASSISTANT.API_BASE_URL);
  await StorageHelper.set(GHL_ASSISTANT.STORAGE_KEYS.DEFAULT_TAGS, defaultTags);
  await StorageHelper.set(GHL_ASSISTANT.STORAGE_KEYS.DEFAULT_MARKET, defaultMarket);

  const result = document.getElementById("save-result");
  result.textContent = "✅ Settings saved!";
  result.className = "save-result success";
  setTimeout(() => {
    result.textContent = "";
  }, 3000);
}

/**
 * Test the connection to the backend server.
 */
async function testConnection() {
  const btn = document.getElementById("btn-test");
  const result = document.getElementById("test-result");

  btn.disabled = true;
  result.textContent = "Testing...";
  result.className = "test-result testing";

  // Temporarily save the URL for testing
  const apiUrl = document.getElementById("api-url").value.trim();
  await StorageHelper.set(
    GHL_ASSISTANT.STORAGE_KEYS.API_URL,
    apiUrl || GHL_ASSISTANT.API_BASE_URL
  );

  try {
    const response = await chrome.runtime.sendMessage({
      action: "healthCheck",
    });

    if (response && response.status === "healthy") {
      result.textContent = "✅ Connected successfully!";
      result.className = "test-result success";
    } else {
      result.textContent = `❌ ${response?.error || "Connection failed"}`;
      result.className = "test-result error";
    }
  } catch (error) {
    result.textContent = `❌ ${error.message}`;
    result.className = "test-result error";
  }

  btn.disabled = false;
}
