/*
 * VidTool Content Script - Video Detector
 *
 * Runs on every page at document_idle. Scans the DOM for videos
 * when requested by the popup via chrome.runtime message.
 *
 * Detection layers:
 *   1. Known platform URL matching (YouTube, Vimeo, Twitter, etc.)
 *   2. HTML5 <video> element scanning
 *   3. Embedded iframe detection (YouTube/Vimeo embeds)
 *
 * Compatibility: Uses ES5-compatible syntax (var, function expressions,
 * no arrow functions, no optional chaining) for Chrome 88+.
 */

(function () {
  "use strict";

  // Platform URL patterns - when matched, we pass the page URL to yt-dlp
  var PLATFORM_PATTERNS = [
    { pattern: /youtube\.com\/watch/, platform: "youtube" },
    { pattern: /youtube\.com\/shorts\//, platform: "youtube" },
    { pattern: /youtu\.be\//, platform: "youtube" },
    { pattern: /vimeo\.com\/\d+/, platform: "vimeo" },
    { pattern: /twitter\.com\/.*\/status/, platform: "twitter" },
    { pattern: /x\.com\/.*\/status/, platform: "twitter" },
    { pattern: /tiktok\.com\/.+\/video/, platform: "tiktok" },
    { pattern: /tiktok\.com\/@[^\/]+$/, platform: "tiktok" },
    { pattern: /instagram\.com\/(p|reel|tv)\//, platform: "instagram" },
    { pattern: /dailymotion\.com\/video/, platform: "dailymotion" },
    { pattern: /twitch\.tv\/videos\//, platform: "twitch" },
    { pattern: /reddit\.com\/.*\/comments/, platform: "reddit" },
    { pattern: /facebook\.com\/.*\/videos/, platform: "facebook" },
    { pattern: /fb\.watch\//, platform: "facebook" },
    { pattern: /bilibili\.com\/video\//, platform: "bilibili" },
    { pattern: /nicovideo\.jp\/watch\//, platform: "niconico" },
    { pattern: /soundcloud\.com\//, platform: "soundcloud" },
    { pattern: /bandcamp\.com\/track\//, platform: "bandcamp" },
    { pattern: /rumble\.com\//, platform: "rumble" },
  ];

  // Embed URL patterns for iframe detection
  var EMBED_PATTERNS = [
    /youtube\.com\/embed/,
    /youtube-nocookie\.com\/embed/,
    /player\.vimeo\.com/,
    /dailymotion\.com\/embed/,
    /facebook\.com\/plugins\/video/,
  ];

  /**
   * Layer 1: Match the current page URL against known platforms.
   */
  function detectPlatformURL() {
    var url = window.location.href;
    for (var i = 0; i < PLATFORM_PATTERNS.length; i++) {
      if (PLATFORM_PATTERNS[i].pattern.test(url)) {
        return {
          type: "platform",
          platform: PLATFORM_PATTERNS[i].platform,
          url: url,
          title: document.title || url,
          thumbnail: getMetaThumbnail(),
        };
      }
    }
    return null;
  }

  /**
   * Layer 2: Scan all <video> elements and their <source> children.
   */
  function scanVideoElements() {
    var results = [];
    var videos = document.querySelectorAll("video");
    for (var i = 0; i < videos.length; i++) {
      var el = videos[i];
      var src = el.src || "";

      // Check <source> children if video has no direct src
      if (!src) {
        var sources = el.querySelectorAll("source");
        for (var j = 0; j < sources.length; j++) {
          if (sources[j].src) {
            src = sources[j].src;
            break;
          }
        }
      }

      // Also check currentSrc (set after the browser resolves the source)
      if (!src && el.currentSrc) {
        src = el.currentSrc;
      }

      if (!src) continue;

      // Skip blob: URLs - these are typically from MSE (Media Source Extensions)
      // and can't be downloaded directly. The network observer catches the
      // underlying HLS/DASH stream instead.
      if (src.indexOf("blob:") === 0) continue;

      results.push({
        type: "direct",
        url: src,
        title: document.title || "Video",
        thumbnail: el.poster || null,
        duration: isFinite(el.duration) ? Math.round(el.duration) : null,
        width: el.videoWidth || null,
        height: el.videoHeight || null,
      });
    }
    return results;
  }

  /**
   * Layer 3: Scan iframes for embedded video players.
   */
  function scanEmbeds() {
    var results = [];
    var iframes = document.querySelectorAll("iframe");
    for (var i = 0; i < iframes.length; i++) {
      var src = iframes[i].src || "";
      if (!src) continue;

      for (var j = 0; j < EMBED_PATTERNS.length; j++) {
        if (EMBED_PATTERNS[j].test(src)) {
          results.push({
            type: "platform",
            platform: "embed",
            url: src,
            title: iframes[i].title || document.title || "Embedded Video",
            thumbnail: null,
          });
          break; // Only match first pattern per iframe
        }
      }
    }
    return results;
  }

  /**
   * Try to get a thumbnail from Open Graph / Twitter Card meta tags.
   */
  function getMetaThumbnail() {
    var selectors = [
      'meta[property="og:image"]',
      'meta[name="twitter:image"]',
      'meta[property="og:image:url"]',
    ];
    for (var i = 0; i < selectors.length; i++) {
      var el = document.querySelector(selectors[i]);
      if (el) {
        var content = el.getAttribute("content");
        if (content) return content;
      }
    }
    return null;
  }

  /**
   * Deduplicate results by URL.
   */
  function dedup(items) {
    var seen = {};
    var unique = [];
    for (var i = 0; i < items.length; i++) {
      if (!seen[items[i].url]) {
        seen[items[i].url] = true;
        unique.push(items[i]);
      }
    }
    return unique;
  }

  /**
   * Handle scan request from popup.
   */
  chrome.runtime.onMessage.addListener(function (msg, sender, sendResponse) {
    if (msg.action === "scan") {
      var results = [];

      // Layer 1: platform URL
      var platform = detectPlatformURL();
      if (platform) {
        results.push(platform);
      }

      // Layer 2: <video> elements
      var directVideos = scanVideoElements();
      for (var i = 0; i < directVideos.length; i++) {
        results.push(directVideos[i]);
      }

      // Layer 3: embedded iframes
      var embeds = scanEmbeds();
      for (var j = 0; j < embeds.length; j++) {
        results.push(embeds[j]);
      }

      sendResponse({ videos: dedup(results) });
    }
    return true; // keep channel open for async
  });
})();
