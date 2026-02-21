/*
 * VidTool Popup Script
 *
 * Orchestrates video detection and download initiation.
 * Uses ES5-compatible syntax for older Chrome versions (88+).
 * Avoids: arrow functions, const/let, template literals, optional chaining,
 *         async/await (uses Promises instead), for...of, destructuring.
 */

(function () {
  "use strict";

  var API_BASE = "http://localhost:9160";
  var statusMsg = document.getElementById("status-msg");
  var videoList = document.getElementById("video-list");
  var emptyState = document.getElementById("empty-state");
  var backendOffline = document.getElementById("backend-offline");
  var backendDot = document.getElementById("backend-status");
  var tryPageBtn = document.getElementById("try-page-btn");
  var settingsBtn = document.getElementById("settings-btn");
  var settingsPanel = document.getElementById("settings-panel");
  var serverInput = document.getElementById("server-input");
  var saveServerBtn = document.getElementById("save-server-btn");
  var settingsHint = document.getElementById("settings-hint");

  // ---- Settings ----

  settingsBtn.addEventListener("click", function () {
    var visible = settingsPanel.style.display !== "none";
    settingsPanel.style.display = visible ? "none" : "block";
  });

  saveServerBtn.addEventListener("click", function () {
    var val = serverInput.value.trim();
    if (!val) {
      // Reset to default
      chrome.storage.local.remove("serverAddress");
      API_BASE = "http://localhost:9160";
      settingsHint.textContent = "Reset to default. Reconnecting\u2026";
    } else {
      // Add http:// if missing
      if (val.indexOf("://") === -1) {
        val = "http://" + val;
      }
      // Remove trailing slash
      val = val.replace(/\/+$/, "");
      chrome.storage.local.set({ serverAddress: val });
      API_BASE = val;
      settingsHint.textContent = "Saved. Reconnecting\u2026";
    }
    settingsPanel.style.display = "none";
    // Re-check backend with new address
    backendDot.className = "status-dot";
    checkBackend().then(function (online) {
      if (online) {
        backendDot.className = "status-dot online";
        settingsHint.textContent = "Connected!";
        backendOffline.style.display = "none";
        scanPage();
      } else {
        backendDot.className = "status-dot offline";
        settingsHint.textContent = "Could not connect to " + API_BASE;
        settingsPanel.style.display = "block";
      }
    });
  });

  // ---- Startup: load saved server address, then connect ----

  function startup() {
    chrome.storage.local.get("serverAddress", function (result) {
      if (result && result.serverAddress) {
        API_BASE = result.serverAddress;
        serverInput.value = API_BASE;
      }
      checkBackend().then(function (online) {
        if (!online) {
          statusMsg.style.display = "none";
          backendOffline.style.display = "block";
          backendDot.className = "status-dot offline";
          return;
        }
        backendDot.className = "status-dot online";
        scanPage();
      });
    });
  }

  startup();

  // ---- Backend health check ----

  function checkBackend() {
    return fetch(API_BASE + "/health", { method: "GET" })
      .then(function (resp) {
        return resp.ok;
      })
      .catch(function () {
        return false;
      });
  }

  // ---- Page scanning ----

  function scanPage() {
    statusMsg.textContent = "Scanning page\u2026";

    // Get the active tab
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      if (!tabs || tabs.length === 0) {
        showEmpty(null);
        return;
      }
      var tab = tabs[0];

      // Collect results from content script and service worker in parallel
      var domPromise = sendTabMessage(tab.id, { action: "scan" });
      var streamPromise = sendRuntimeMessage({
        action: "getStreams",
        tabId: tab.id,
      });

      Promise.all([domPromise, streamPromise]).then(function (results) {
        var domResult = results[0];
        var streamResult = results[1];

        var domVideos =
          domResult && domResult.videos ? domResult.videos : [];
        var streamVideos =
          streamResult && streamResult.streams ? streamResult.streams : [];

        var all = domVideos.concat(streamVideos);
        var unique = dedup(all);

        if (unique.length === 0) {
          showEmpty(tab);
        } else {
          statusMsg.style.display = "none";
          renderVideos(unique);
        }
      });
    });
  }

  // ---- Messaging helpers (Promise-wrapped for older Chrome) ----

  function sendTabMessage(tabId, msg) {
    return new Promise(function (resolve) {
      try {
        chrome.tabs.sendMessage(tabId, msg, function (response) {
          // Suppress chrome.runtime.lastError for tabs where content script
          // isn't injected (e.g., chrome:// pages)
          if (chrome.runtime.lastError) {
            resolve(null);
            return;
          }
          resolve(response || null);
        });
      } catch (e) {
        resolve(null);
      }
    });
  }

  function sendRuntimeMessage(msg) {
    return new Promise(function (resolve) {
      try {
        chrome.runtime.sendMessage(msg, function (response) {
          if (chrome.runtime.lastError) {
            resolve(null);
            return;
          }
          resolve(response || null);
        });
      } catch (e) {
        resolve(null);
      }
    });
  }

  // ---- Dedup by URL ----

  function dedup(items) {
    var seen = {};
    var result = [];
    for (var i = 0; i < items.length; i++) {
      var url = items[i].url;
      if (url && !seen[url]) {
        seen[url] = true;
        result.push(items[i]);
      }
    }
    return result;
  }

  // ---- Empty state ----

  function showEmpty(tab) {
    statusMsg.style.display = "none";
    emptyState.style.display = "block";

    if (tab && tab.url) {
      tryPageBtn.style.display = "inline-block";
      tryPageBtn.onclick = function () {
        emptyState.style.display = "none";
        renderVideos([
          {
            type: "platform",
            url: tab.url,
            title: tab.title || "Current page",
            platform: "unknown",
            thumbnail: null,
          },
        ]);
      };
    } else {
      tryPageBtn.style.display = "none";
    }
  }

  // ---- Render video cards ----

  function renderVideos(videos) {
    videoList.innerHTML = "";
    for (var i = 0; i < videos.length; i++) {
      videoList.appendChild(createVideoCard(videos[i], i));
    }
  }

  function createVideoCard(video, index) {
    var card = document.createElement("div");
    card.className = "video-card";

    // Info row: thumbnail + title
    var info = document.createElement("div");
    info.className = "video-info";

    if (video.thumbnail) {
      var thumb = document.createElement("img");
      thumb.className = "video-thumb";
      thumb.src = video.thumbnail;
      thumb.alt = "";
      thumb.onerror = function () {
        this.style.display = "none";
      };
      info.appendChild(thumb);
    } else {
      var placeholder = document.createElement("div");
      placeholder.className = "video-thumb-placeholder";
      placeholder.textContent = "\u25B6";
      info.appendChild(placeholder);
    }

    var details = document.createElement("div");
    details.className = "video-details";

    var title = document.createElement("div");
    title.className = "video-title";
    title.textContent = truncate(video.title || video.url, 60);
    title.title = video.title || video.url;
    details.appendChild(title);

    var meta = document.createElement("div");
    meta.className = "video-meta";
    var metaParts = [];
    if (video.platform && video.platform !== "unknown") {
      metaParts.push(capitalize(video.platform));
    }
    if (video.type === "stream") {
      metaParts.push("HLS/DASH stream");
    }
    if (video.type === "direct") {
      metaParts.push("Direct video");
    }
    if (video.width && video.height) {
      metaParts.push(video.width + "x" + video.height);
    }
    if (video.duration) {
      metaParts.push(formatDuration(video.duration));
    }
    meta.textContent = metaParts.join(" \u00B7 ");
    details.appendChild(meta);

    info.appendChild(details);
    card.appendChild(info);

    // Filename input row
    var fnRow = document.createElement("div");
    fnRow.className = "filename-row";
    var fnInput = document.createElement("input");
    fnInput.type = "text";
    fnInput.className = "filename-input";
    fnInput.id = "fname-" + index;
    fnInput.placeholder = "Save as\u2026 (optional, leave blank for original name)";
    fnRow.appendChild(fnInput);
    card.appendChild(fnRow);

    // Controls row: quality select + download button
    var controls = document.createElement("div");
    controls.className = "video-controls";

    var select = document.createElement("select");
    select.className = "quality-select";
    var options = [
      { value: "best", label: "Best quality" },
      { value: "720p", label: "720p" },
      { value: "480p", label: "480p" },
      { value: "audio-only", label: "Audio only" },
    ];
    for (var j = 0; j < options.length; j++) {
      var opt = document.createElement("option");
      opt.value = options[j].value;
      opt.textContent = options[j].label;
      select.appendChild(opt);
    }
    controls.appendChild(select);

    var dlBtn = document.createElement("button");
    dlBtn.className = "btn btn-primary";
    dlBtn.textContent = "Download";
    dlBtn.setAttribute("data-url", video.url);
    dlBtn.setAttribute("data-index", index);
    controls.appendChild(dlBtn);

    card.appendChild(controls);

    // Progress area (hidden until download starts)
    var progressWrap = document.createElement("div");
    progressWrap.className = "progress-wrap";
    progressWrap.id = "progress-wrap-" + index;

    var barBg = document.createElement("div");
    barBg.className = "progress-bar-bg";
    var barFill = document.createElement("div");
    barFill.className = "progress-bar-fill";
    barFill.id = "bar-" + index;
    barBg.appendChild(barFill);
    progressWrap.appendChild(barBg);

    var progressText = document.createElement("div");
    progressText.className = "progress-text";
    progressText.id = "ptext-" + index;
    progressWrap.appendChild(progressText);

    card.appendChild(progressWrap);

    // Download click handler
    dlBtn.addEventListener("click", function () {
      var url = this.getAttribute("data-url");
      var idx = this.getAttribute("data-index");
      var quality = this.parentNode.querySelector(".quality-select").value;
      var saveName = document.getElementById("fname-" + idx).value.trim();
      this.disabled = true;
      this.textContent = "Starting\u2026";
      startDownload(url, quality, idx, saveName);
    });

    return card;
  }

  // ---- Download + SSE progress ----

  function startDownload(url, quality, index, saveName) {
    var wrap = document.getElementById("progress-wrap-" + index);
    var bar = document.getElementById("bar-" + index);
    var text = document.getElementById("ptext-" + index);
    wrap.className = "progress-wrap active";
    text.textContent = "Connecting\u2026";

    var payload = { url: url, quality: quality };
    if (saveName) {
      payload.filename = saveName;
    }

    fetch(API_BASE + "/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (resp) {
        if (!resp.ok) {
          return resp.json().then(function (data) {
            throw new Error(data.detail || "Request failed");
          });
        }
        return resp.json();
      })
      .then(function (data) {
        trackProgress(data.task_id, bar, text);
      })
      .catch(function (err) {
        text.textContent = "Error: " + err.message;
        text.className = "progress-text error";
      });
  }

  function trackProgress(taskId, bar, text) {
    // Use EventSource (SSE) for real-time progress
    var evtSource;
    try {
      evtSource = new EventSource(API_BASE + "/progress/" + taskId);
    } catch (e) {
      // Fallback to polling if EventSource not supported
      pollProgress(taskId, bar, text);
      return;
    }

    evtSource.onmessage = function (event) {
      var data;
      try {
        data = JSON.parse(event.data);
      } catch (e) {
        return;
      }

      if (data.status === "downloading") {
        bar.style.width = data.percent + "%";
        var parts = [Math.round(data.percent) + "%"];
        if (data.speed) parts.push(data.speed);
        if (data.eta) parts.push("ETA: " + data.eta);
        text.textContent = parts.join(" \u00B7 ");
        text.className = "progress-text";
      } else if (data.status === "processing") {
        bar.style.width = "100%";
        text.textContent = "Processing (merging formats)\u2026";
        text.className = "progress-text";
      } else if (data.status === "finished") {
        bar.style.width = "100%";
        var dname = data.display_name || data.filename || "download complete";
        text.textContent = "Done: " + dname;
        text.className = "progress-text done";
        addSaveLink(text, data.task_id, dname);
        evtSource.close();
      } else if (data.status === "error") {
        text.textContent = "Error: " + (data.error || "Unknown error");
        text.className = "progress-text error";
        evtSource.close();
      }
    };

    evtSource.onerror = function () {
      evtSource.close();
      // Check final state via a single fetch
      fetch(API_BASE + "/progress/" + taskId)
        .then(function () {
          // SSE reconnect not needed, the stream ended
        })
        .catch(function () {
          text.textContent = "Connection lost";
          text.className = "progress-text error";
        });
    };
  }

  // Polling fallback for very old browsers without EventSource
  function pollProgress(taskId, bar, text) {
    var interval = setInterval(function () {
      fetch(API_BASE + "/progress/" + taskId)
        .then(function (resp) {
          return resp.text();
        })
        .then(function (body) {
          // Parse the last SSE data line
          var lines = body.split("\n");
          var lastData = null;
          for (var i = lines.length - 1; i >= 0; i--) {
            if (lines[i].indexOf("data: ") === 0) {
              lastData = lines[i].substring(6);
              break;
            }
          }
          if (!lastData) return;
          var data = JSON.parse(lastData);
          bar.style.width = data.percent + "%";
          if (data.status === "finished" || data.status === "error") {
            clearInterval(interval);
            if (data.status === "finished") {
              var dname = data.display_name || data.filename || "complete";
              text.textContent = "Done: " + dname;
              text.className = "progress-text done";
              addSaveLink(text, data.task_id, dname);
            } else {
              text.textContent = "Error: " + (data.error || "Unknown");
              text.className = "progress-text error";
            }
          } else {
            text.textContent = Math.round(data.percent) + "%";
          }
        })
        .catch(function () {
          clearInterval(interval);
          text.textContent = "Connection lost";
          text.className = "progress-text error";
        });
    }, 1000);
  }

  // ---- Save to this computer ----

  function addSaveLink(parentEl, taskId, filename) {
    var link = document.createElement("a");
    link.className = "save-link";
    link.textContent = "Save to this computer";
    link.href = API_BASE + "/file/" + taskId;
    link.download = filename || "download";
    link.target = "_blank";
    parentEl.parentNode.appendChild(link);
  }

  // ---- Utilities ----

  function truncate(str, max) {
    if (!str) return "";
    return str.length > max ? str.substring(0, max - 1) + "\u2026" : str;
  }

  function capitalize(str) {
    if (!str) return "";
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  function formatDuration(seconds) {
    var h = Math.floor(seconds / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    var s = seconds % 60;
    if (h > 0) {
      return h + ":" + pad(m) + ":" + pad(s);
    }
    return m + ":" + pad(s);
  }

  function pad(n) {
    return n < 10 ? "0" + n : "" + n;
  }
})();
