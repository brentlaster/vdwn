# VidTool Standalone - Video Downloader (Legacy Python Compatible)

A Chrome extension + local Python backend that downloads videos from any website.
This is the **standalone version** — it has **zero Python package dependencies** and works
with **Python 2.7+** and **all Python 3.x versions**, making it compatible with older
macOS systems that ship with an older Python.

For the standard version (using FastAPI + yt-dlp Python library), see the parent `../` directory.

---

## Table of Contents

- [Key Differences from Standard Version](#key-differences-from-standard-version)
- [Requirements](#requirements)
- [Installation](#installation)
- [Loading the Chrome Extension](#loading-the-chrome-extension)
- [Usage](#usage)
  - [Starting the Backend](#starting-the-backend)
  - [Command-Line Options](#command-line-options)
  - [Downloading a Video](#downloading-a-video)
  - [Quality Options](#quality-options)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [macOS Compatibility Notes](#macos-compatibility-notes)
- [Supported Sites](#supported-sites)
- [Troubleshooting](#troubleshooting)
- [Uninstalling](#uninstalling)
- [Project Structure](#project-structure)

---

## Key Differences from Standard Version

| Feature | Standard Version (`../`) | Standalone Version (this) |
|---------|-------------------------|--------------------------|
| **Python version** | 3.8+ | **2.7+** or any 3.x |
| **pip dependencies** | FastAPI, uvicorn, yt-dlp, requests | **None** |
| **Virtual environment** | Required | Not needed |
| **yt-dlp** | Python library (imported) | **CLI binary** (called via subprocess) |
| **HTTP server** | FastAPI + uvicorn | Python stdlib `BaseHTTPServer` / `http.server` |
| **Setup time** | ~30 seconds (pip install) | Instant (no install step) |
| **Best for** | Modern Macs, latest Python | **Older Macs, legacy systems, minimal installs** |

Both versions use the same Chrome extension and produce identical results.

---

## Requirements

| Requirement | Minimum Version | How to Install |
|-------------|----------------|----------------|
| **macOS**   | 10.9+ (Mavericks) | — |
| **Python**  | 2.7 or 3.x    | Pre-installed on macOS, or `brew install python3` |
| **Chrome**  | 88+            | [Download](https://www.google.com/chrome/) |
| **yt-dlp**  | Any            | See below |
| **ffmpeg**  | Any (recommended) | `brew install ffmpeg` |

### Installing yt-dlp

yt-dlp must be installed as a **command-line tool** (not a Python library). Choose one method:

```bash
# Option 1: Homebrew (recommended on macOS)
brew install yt-dlp

# Option 2: pip (if you have pip available)
pip install yt-dlp
# or
pip3 install yt-dlp

# Option 3: Direct binary download (no package manager needed)
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
chmod +x /usr/local/bin/yt-dlp

# Option 4: For very old systems, use the standalone binary
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos -o /usr/local/bin/yt-dlp
chmod +x /usr/local/bin/yt-dlp
```

> **Note on ffmpeg:** ffmpeg is strongly recommended. Without it, yt-dlp cannot merge
> separate video and audio streams (which is how YouTube and many sites serve HD content).
> Install via `brew install ffmpeg`.

---

## Installation

### Quick Setup

```bash
cd /path/to/vidtool/standalone
bash scripts/install.sh
```

The install script simply:
- Checks that Python is available (2.7+ or 3.x)
- Checks that yt-dlp is installed
- Checks for ffmpeg
- Prints startup instructions

**There are no packages to install.** The backend is a single Python file using only the standard library.

### Manual Setup

No setup is needed. Just ensure `python` (or `python3`) and `yt-dlp` are available on your PATH.

---

## Loading the Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** using the toggle in the top-right corner
3. Click **Load unpacked**
4. Select the `extension/` folder from this project
5. The VidTool icon will appear in your toolbar

> **Tip:** Pin the extension by clicking the puzzle piece icon next to the address bar,
> then click the pin next to VidTool.

---

## Usage

### Starting the Backend

Open a terminal and run:

```bash
# Using Python 3
python3 standalone/backend/server.py

# Using Python 2
python standalone/backend/server.py

# Or if you made it executable
./standalone/backend/server.py
```

You should see:

```
yt-dlp version: 2026.2.4
Python version: 3.12.8
Download directory: /Users/yourname/Downloads/VidTool

VidTool backend running on http://127.0.0.1:9160
Press Ctrl+C to stop.
```

Keep this terminal open while using VidTool. Stop with `Ctrl+C`.

### Command-Line Options

```
python server.py [options]

Options:
  --port, -p PORT          Server port (default: 9160)
  --download-dir, -d DIR   Download directory (default: ~/Downloads/VidTool)
  --help, -h               Show help
```

Examples:

```bash
# Use a different port
python3 server.py --port 8080

# Save downloads to a custom folder
python3 server.py --download-dir ~/Videos/Downloads

# Combine options
python3 server.py -p 8080 -d ~/Videos
```

### Downloading a Video

1. Make sure the backend server is running (see above)
2. Navigate to any webpage containing a video
3. Click the **VidTool** extension icon in the Chrome toolbar
4. The popup shows detected videos with thumbnails and metadata
5. Select your preferred **quality** from the dropdown
6. Click **Download**
7. Watch the progress bar update in real-time
8. When complete, the file is saved to your downloads folder

### Quality Options

| Option       | Description |
|-------------|-------------|
| **Best quality** | Highest available video + audio (default) |
| **720p**    | HD video, capped at 720p |
| **480p**    | Standard definition, smaller files |
| **Audio only** | Audio track only (M4A format) |

---

## How It Works

### Architecture

```
 Chrome Extension                       Python Backend (stdlib only)
┌──────────────────┐                   ┌──────────────────────────┐
│  Content Script   │  scan results    │                          │
│  (detector.js)   ├──────────┐       │  BaseHTTPServer          │
├──────────────────┤          │       │  (ThreadedHTTPServer)    │
│  Service Worker   │  streams │       │  Port 9160               │
│  (service-worker) ├─────┐   │       │                          │
├──────────────────┤     │   │       │  ┌──────────────────────┐ │
│  Popup UI         │◄────┘   │       │  │ subprocess.Popen     │ │
│  (popup.js)      ◄─────────┘       │  │   -> yt-dlp CLI      │ │
│                  ├──── POST ───────►│  │   (parses stdout     │ │
│                  ◄──── SSE  ────────│  │    for progress)     │ │
└──────────────────┘  progress        │  └──────────┬───────────┘ │
                                      └─────────────┼─────────────┘
                                                    │
                                                    ▼
                                          ~/Downloads/VidTool/
```

### Detection Layers

1. **Platform URL matching** — Recognizes YouTube, Vimeo, TikTok, Twitter/X, Instagram, etc. by URL pattern. Passes the page URL directly to yt-dlp.

2. **DOM scanning** — Content script scans for `<video>` elements, `<source>` tags, and known iframe embeds (YouTube/Vimeo players embedded on blogs).

3. **Network stream detection** — Background service worker monitors network traffic for HLS (`.m3u8`) and DASH (`.mpd`) manifest URLs that are invisible in the DOM.

4. **Fallback** — If nothing is detected, offers to send the page URL to yt-dlp anyway (it supports 1000+ sites via built-in extractors).

### How Progress Tracking Works

Unlike the standard version (which uses yt-dlp's Python API), the standalone version:

1. Launches `yt-dlp` as a subprocess with `--newline` flag
2. Reads `stdout` line by line in a background thread
3. Parses progress lines using regex (e.g., `[download]  42.3% of 50.00MiB at 2.10MiB/s ETA 00:14`)
4. Updates an in-memory task dict
5. The popup polls for updates via Server-Sent Events (SSE)

---

## Configuration

### Download Directory

Default: `~/Downloads/VidTool`

Change via CLI flag:
```bash
python3 server.py --download-dir ~/Videos
```

Or via environment variable:
```bash
export VIDTOOL_DOWNLOAD_DIR="/path/to/folder"
python3 server.py
```

### Server Port

Default: `9160`

Change via CLI flag:
```bash
python3 server.py --port 8080
```

Or via environment variable:
```bash
export VIDTOOL_PORT=8080
python3 server.py
```

> **Important:** If you change the port, also update `API_BASE` in
> `extension/popup/popup.js` and the `host_permissions` URL in
> `extension/manifest.json` to match.

---

## macOS Compatibility Notes

### macOS 10.9 – 10.14 (Mavericks through Mojave)
- Ships with Python 2.7. This standalone version supports it.
- Install yt-dlp via the direct binary download method (Option 3 or 4 in [Installing yt-dlp](#installing-yt-dlp)).
- Chrome 88+ should still work on these versions.

### macOS 10.15 (Catalina)
- Python 2.7 is still available but deprecated.
- `python3` may need to be installed via Xcode Command Line Tools (`xcode-select --install`) or Homebrew.

### macOS 11+ (Big Sur and later)
- Python 2.7 is removed. Use `python3` (install via `brew install python3` or Xcode CLT).
- Everything works out of the box.

### Apple Silicon (M1/M2/M3/M4)
- Fully supported. Use Homebrew to install yt-dlp and ffmpeg: `brew install yt-dlp ffmpeg`.

---

## Supported Sites

VidTool supports any site that yt-dlp supports. Some popular platforms:

| Platform | Status |
|----------|--------|
| YouTube / YouTube Shorts | Fully supported |
| Vimeo | Fully supported |
| Twitter / X | Fully supported |
| TikTok | Fully supported |
| Instagram (posts, reels) | Fully supported |
| Reddit | Fully supported |
| Facebook (public videos) | Supported |
| Twitch VODs | Fully supported |
| Dailymotion | Fully supported |
| Bilibili | Fully supported |
| SoundCloud | Audio supported |
| Bandcamp | Audio supported |
| Generic HTML5 `<video>` | Supported via DOM scanning |
| HLS streams (.m3u8) | Supported via network detection |
| DASH streams (.mpd) | Supported via network detection |
| **1000+ others** | Via yt-dlp extractors |

> **Note:** DRM-protected content (Netflix, Disney+, Amazon Prime Video, etc.) **cannot**
> be downloaded. These services use Widevine DRM which prevents extraction.

---

## Troubleshooting

### "Backend is not running" in popup

The extension can't connect to the local server.

**Fix:** Start the backend:
```bash
python3 standalone/backend/server.py
```

### "yt-dlp not found" when starting the server

The server can't locate the yt-dlp binary.

**Fixes:**
```bash
# Install yt-dlp
brew install yt-dlp

# Or verify it's on your PATH
which yt-dlp

# If installed but not on PATH, create a symlink
ln -s /path/to/yt-dlp /usr/local/bin/yt-dlp
```

### "No videos detected on this page"

**Fixes:**
- Click **"Try with yt-dlp"** — the backend may still extract the video
- Make sure the video has loaded/played on the page
- Close and reopen the popup to re-scan

### Download fails with an error

**Common causes:**
- **ffmpeg not installed:** `brew install ffmpeg`
- **yt-dlp outdated:** `brew upgrade yt-dlp` or `pip install -U yt-dlp`
- **Geo-restricted content:** Video isn't available in your region
- **Rate limiting:** Wait a few minutes and try again

### Progress bar stuck at 0%

yt-dlp is extracting metadata before downloading. Wait 10-15 seconds.
If still stuck after 30 seconds, the URL may be unsupported.

### Server won't start — "Address already in use"

Another process is using port 9160.

```bash
# Find and kill the process
lsof -ti:9160 | xargs kill

# Or use a different port
python3 server.py --port 9161
```

### Python 2 specific issues

- Ensure you have Python 2.7 (not 2.6 or earlier)
- If `print` gives a syntax error, check you're running the file correctly: `python server.py`
- Unicode filenames may not display correctly in the terminal on Python 2, but downloads still work

### Extension not appearing in Chrome

- Ensure **Developer mode** is enabled at `chrome://extensions/`
- Select the `extension/` folder (not the project root or `standalone/`)
- Check for errors — click "Errors" on the VidTool card at `chrome://extensions/`

### Updating yt-dlp

yt-dlp is updated frequently to keep up with site changes:

```bash
# Via Homebrew
brew upgrade yt-dlp

# Via pip
pip install -U yt-dlp

# Via direct download
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
chmod +x /usr/local/bin/yt-dlp
```

---

## Uninstalling

### Remove the Chrome extension
1. Go to `chrome://extensions/`
2. Find VidTool and click **Remove**

### Remove the backend
```bash
rm -rf /path/to/vidtool/standalone
```

### Remove downloaded videos
```bash
rm -rf ~/Downloads/VidTool
```

---

## Project Structure

```
standalone/
├── backend/
│   └── server.py                     # Single-file backend (stdlib only)
│                                     #   - HTTP server (BaseHTTPServer)
│                                     #   - yt-dlp subprocess wrapper
│                                     #   - SSE progress streaming
│                                     #   - CLI argument parsing
│
├── extension/                        # Chrome Extension (Manifest V3)
│   ├── manifest.json                 # Extension manifest (Chrome 88+)
│   ├── background/
│   │   └── service-worker.js         # Network observer for HLS/DASH
│   ├── content/
│   │   └── detector.js               # Video element + platform scanner
│   ├── popup/
│   │   ├── popup.html                # Popup UI
│   │   ├── popup.css                 # Styles
│   │   └── popup.js                  # Scan, download, progress logic
│   └── icons/
│       ├── icon16.png
│       ├── icon48.png
│       └── icon128.png
│
├── scripts/
│   └── install.sh                    # Setup checker (no actual install needed)
│
└── README.md                         # This file
```

The entire backend is a **single 500-line Python file** with zero external dependencies.

---

## Security Notes

- The server binds to `127.0.0.1` only — it is **not accessible** from the network
- No authentication is needed because it's strictly local
- No data is sent to external servers — all processing happens on your machine
- The extension requires `<all_urls>` host permission for network stream detection (same as ad blockers)
- Downloaded files are saved only to your local filesystem

---

## License

This project is for personal use. It relies on yt-dlp (released under the Unlicense).
Video downloading may be subject to the terms of service of individual websites.
Always respect copyright and only download content you have the right to access.
