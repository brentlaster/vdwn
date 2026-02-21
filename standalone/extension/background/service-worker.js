/*
 * VidTool Service Worker (Manifest V3)
 *
 * Observes network requests to detect HLS (.m3u8) and DASH (.mpd) streams
 * that are invisible in the DOM. Caches observed URLs per tab.
 *
 * Compatibility: Chrome 88+ (MV3 service worker support).
 * Uses var instead of const/let where possible for maximum JS engine compat.
 * Avoids optional chaining (?.) for older Chrome versions.
 */

// tabId -> array of stream URL strings
var streamCache = {};

// Listen for network requests matching HLS/DASH patterns
chrome.webRequest.onBeforeRequest.addListener(
  function (details) {
    var url = details.url;
    var tabId = details.tabId;
    if (tabId < 0) return; // non-tab request (e.g., service worker fetch)

    // Match .m3u8 and .mpd URLs (HLS and DASH manifests)
    if (/\.(m3u8|mpd)(\?|#|$)/i.test(url)) {
      if (!streamCache[tabId]) {
        streamCache[tabId] = [];
      }
      // Avoid duplicates
      var existing = streamCache[tabId];
      var isDuplicate = false;
      for (var i = 0; i < existing.length; i++) {
        if (existing[i] === url) {
          isDuplicate = true;
          break;
        }
      }
      if (!isDuplicate) {
        existing.push(url);
      }
    }
  },
  { urls: ["<all_urls>"] }
);

// Clean up when tabs close
chrome.tabs.onRemoved.addListener(function (tabId) {
  delete streamCache[tabId];
});

// Clean up when tab navigates to a new page
chrome.tabs.onUpdated.addListener(function (tabId, changeInfo) {
  if (changeInfo.status === "loading") {
    delete streamCache[tabId];
  }
});

// Respond to messages from popup requesting cached streams
chrome.runtime.onMessage.addListener(function (msg, sender, sendResponse) {
  if (msg.action === "getStreams") {
    var urls = streamCache[msg.tabId] || [];
    var streams = [];
    for (var i = 0; i < urls.length; i++) {
      streams.push({
        type: "stream",
        url: urls[i],
        title: "HLS/DASH Stream",
        platform: null,
        thumbnail: null,
      });
    }
    sendResponse({ streams: streams });
  }
  return true; // keep message channel open
});
