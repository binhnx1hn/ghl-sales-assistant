/**
 * Extension Popup Script
 *
 * Manages the popup UI shown when clicking the extension icon.
 * Displays connection status, recent captures, and quick actions.
 */

document.addEventListener("DOMContentLoaded", async () => {
  // Show version
  const manifest = chrome.runtime.getManifest();
  document.getElementById("version").textContent = `v${manifest.version}`;

  // Check backend connection
  await checkConnection();

  // Load recent leads
  await loadRecentLeads();

  // Settings button
  document.getElementById("btn-settings").addEventListener("click", () => {
    chrome.runtime.openOptionsPage();
  });

  // Refresh button
  document.getElementById("btn-refresh").addEventListener("click", async () => {
    await checkConnection();
    await loadRecentLeads();
  });
});

/**
 * Check if the backend server is reachable.
 */
async function checkConnection() {
  const dot = document.getElementById("status-dot");
  const text = document.getElementById("status-text");

  dot.className = "status-dot status-checking";
  text.textContent = "Checking connection...";

  try {
    const response = await chrome.runtime.sendMessage({
      action: "healthCheck",
    });

    if (response && response.status === "healthy") {
      dot.className = "status-dot status-connected";
      text.textContent = "Connected to backend";
    } else {
      dot.className = "status-dot status-error";
      text.textContent = response?.error || "Backend not responding";
    }
  } catch (error) {
    dot.className = "status-dot status-error";
    text.textContent = "Cannot reach backend";
  }
}

/**
 * Load and display recently captured leads.
 */
async function loadRecentLeads() {
  try {
    const response = await chrome.runtime.sendMessage({
      action: "getLeads",
      limit: 5,
    });

    if (response && response.leads && response.leads.length > 0) {
      const statsSection = document.getElementById("stats-section");
      const recentSection = document.getElementById("recent-section");
      const recentList = document.getElementById("recent-list");

      statsSection.style.display = "flex";
      recentSection.style.display = "block";

      // Update stats
      document.getElementById("stat-total").textContent = response.total || 0;

      // Render recent leads
      recentList.innerHTML = "";
      response.leads.slice(0, 5).forEach((lead) => {
        const li = document.createElement("li");
        li.className = "recent-item";
        li.innerHTML = `
          <div class="recent-name">${escapeHtml(lead.business_name)}</div>
          <div class="recent-meta">
            ${lead.phone ? `📞 ${escapeHtml(lead.phone)}` : ""}
            ${lead.city ? ` · 📍 ${escapeHtml(lead.city)}` : ""}
          </div>
        `;
        recentList.appendChild(li);
      });
    }
  } catch (error) {
    console.error("Failed to load recent leads:", error);
  }
}

/**
 * Escape HTML to prevent XSS.
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}
