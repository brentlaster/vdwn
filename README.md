# VidTool - Video Downloader

A Chrome extension + local Python backend that downloads videos from any website. Powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp), supporting **1000+ platforms** including YouTube, Vimeo, TikTok, Twitter/X, Instagram, Reddit, and more — plus any site with standard HTML5 video or HLS/DASH streams.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
  - [Quick Install (Recommended)](#quick-install-recommended)
  - [Manual Install](#manual-install)
- [Loading the Chrome Extension](#loading-the-chrome-extension)
- [Usage](#usage)
  - [Starting the Backend](#starting-the-backend)
  - [Downloading a Video](#downloading-a-video)
  - [Quality Options](#quality-options)
- [Network Setup (Remote Backend)](#network-setup-remote-backend)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Supported Sites](#supported-sites)
- [Troubleshooting](#troubleshooting)
- [Uninstalling](#uninstalling)
- [Project Structure](#project-structure)

---

## Requirements

| Requirement | Minimum Version | How to Install |
|-------------|----------------|----------------|
| **macOS**   | 10.13+ (High Sierra) | — |
| **Python**  | 3.6+           | `brew install python3` |
| **Chrome**  | 88+            | [Download](https://www.google.com/chrome/) |
| **ffmpeg**  | Any recent     | `brew install ffmpeg` |

> **Note:** ffmpeg is strongly recommended. Without it, yt-dlp cannot merge separate video and audio streams (used by YouTube and many other sites for HD quality). Downloads will still work, but quality may be limited.

---

## Installation

### Quick Install (Recommended)

```bash
# 1. Clone or download the project
cd /path/to/vidtool

# 2. Run the install script
bash scripts/install.sh
```

This will:
- Check that Python 3 and ffmpeg are available
- Create a Python virtual environment in `backend/.venv`
- Install all Python dependencies (FastAPI, yt-dlp, etc.)

### Manual Install

If you prefer to set things up yourself:

```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Loading the Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** using the toggle in the top-right corner
3. Click **Load unpacked**
4. Select the `extension/` folder from this project
5. The VidTool icon (blue play button) will appear in your toolbar

> **Tip:** Pin the extension to your toolbar by clicking the puzzle piece icon next to the address bar, then clicking the pin icon next to VidTool.

---

## Usage

### Starting the Backend

The backend server must be running for downloads to work. Start it in a terminal:

```bash
cd backend
source .venv/bin/activate
python server.py
```

You should see:

```
VidTool backend starting on http://127.0.0.1:9160
Downloads will be saved to: /Users/yourname/Downloads/VidTool
```

> **Keep this terminal open** while using VidTool. You can stop the server anytime with `Ctrl+C`.

### Downloading a Video

1. Navigate to any webpage containing a video
2. Click the **VidTool** extension icon in the toolbar
3. The popup will show detected videos with thumbnails and metadata
4. Select your preferred **quality** from the dropdown
5. Click **Download**
6. Watch the progress bar — when complete, the file is in your downloads folder

### Quality Options

| Option       | Description |
|-------------|-------------|
| **Best quality** | Highest available video + audio (default) |
| **720p**    | HD video, capped at 720p resolution |
| **480p**    | Standard definition, smaller file size |
| **Audio only** | Extracts just the audio track (M4A format) |

---

## Network Setup (Remote Backend)

You can run the backend on a different machine and connect to it over your local
network. This is useful when the machine running Chrome can't run the backend
natively (e.g., an older Mac stuck on Python 3.6).

### How It Works

The backend runs inside a Docker container on any modern computer on your LAN.
The Chrome extension on the client machine connects to it over the network.
When a download finishes, you can click **"Save to this computer"** to transfer
the file from the server to the client machine through the browser.

```
  Client (old Mac)                        Server (any modern machine)
┌──────────────────┐                   ┌──────────────────────────────┐
│  Chrome Extension │                   │  Docker Container            │
│                  │                   │  ┌────────────────────────┐  │
│  Settings:       │   HTTP over LAN   │  │  Python 3.11           │  │
│  192.168.1.50    ├──────────────────►│  │  yt-dlp (latest)       │  │
│  :9160           │                   │  │  ffmpeg                │  │
│                  │◄──────────────────│  │  VidTool server        │  │
│  "Save to this   │   file transfer   │  └────────────────────────┘  │
│   computer"      │                   │  Port 9160                   │
└──────────────────┘                   └──────────────────────────────┘
```

### Prerequisites

- **Server machine**: Any computer with [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS 10.15+, Windows 10+, or Linux)
- **Client machine**: Chrome 88+ with the VidTool extension
- Both machines must be on the **same local network** (LAN)

### Server Setup

On the machine that will run the backend:

```bash
cd /path/to/vidtool

# Build the Docker image (first time only):
bash docker/setup.sh

# Start the backend:
bash docker/start.sh
```

The start script prints the server's LAN IP address and port. Note this for the
next step.

### Client Setup

On the machine running Chrome:

1. Install the extension (see [Loading the Chrome Extension](#loading-the-chrome-extension))
2. Click the **VidTool** extension icon in the toolbar
3. Click the **gear icon** in the top-right corner
4. Enter the server address (e.g., `192.168.1.50:9160`)
5. Click **Save**

The status dot should turn green if the connection is successful.

### Downloading to the Client Machine

Videos are downloaded and stored on the server. To get the file on the client:

1. Start a download as usual from the extension popup
2. When the progress bar shows **Done**, a **"Save to this computer"** link appears
3. Click the link — the file transfers from the server to the client via the browser

### Managing the Server

```bash
# Stop the backend:
bash docker/stop.sh

# Update yt-dlp to the latest version:
bash docker/setup.sh --update
bash docker/start.sh

# View server logs:
docker logs -f vidtool
```

### Network Requirements

- Both machines must be on the same LAN subnet
- Port **9160** must not be blocked by a firewall on the server
  - macOS: allow the connection when prompted, or check System Preferences > Security & Privacy > Firewall
  - Linux: `sudo ufw allow 9160` if using ufw
- Some routers enable **AP/client isolation** on Wi-Fi, which prevents devices from seeing each other. If the extension can't connect, try wired ethernet or check your router settings
- Traffic is **unencrypted HTTP** — fine for a home network, but do not expose port 9160 to the internet

---

## How It Works

VidTool uses a three-layer detection system:

### 1. Platform Detection
When you visit a known platform (YouTube, Vimeo, TikTok, etc.), the extension recognizes the URL pattern and passes the page URL directly to yt-dlp on the backend. yt-dlp has specialized extractors for 1000+ sites.

### 2. DOM Scanning
The content script scans the page for:
- `<video>` elements with direct `src` attributes
- `<source>` tags inside video elements
- `<iframe>` embeds from known video platforms (YouTube embeds, Vimeo player, etc.)

### 3. Network Stream Detection
The background service worker monitors all network requests for HLS (`.m3u8`) and DASH (`.mpd`) manifest URLs. These streaming formats are used by many modern video players but are invisible in the page DOM.

### Fallback
If no videos are detected through the above methods, VidTool offers to send the current page URL to yt-dlp anyway — it may still be able to extract the video.

### Architecture Diagram

```
 Chrome Extension                         Python Backend
┌──────────────────┐                   ┌──────────────────┐
│  Content Script   │  scan results    │                  │
│  (detector.js)   ├──────────┐       │  FastAPI Server   │
├──────────────────┤          │       │  (server.py)      │
│  Service Worker   │  streams │       │  Port 9160        │
│  (service-worker) ├─────┐   │       │                   │
├──────────────────┤     │   │       │  ┌──────────────┐ │
│  Popup UI         │◄────┘   │       │  │ downloader.py│ │
│  (popup.js)      ◄─────────┘       │  │  (yt-dlp)    │ │
│                  ├──── POST ───────►│  └──────┬───────┘ │
│                  ◄──── SSE  ────────│         │         │
└──────────────────┘  progress        └─────────┼─────────┘
                                                │
                                                ▼
                                      ~/Downloads/VidTool/
```

---

## Configuration

### Download Directory

By default, videos are saved to `~/Downloads/VidTool/`. To change this, set the environment variable before starting the server:

```bash
export VIDTOOL_DOWNLOAD_DIR="/path/to/your/folder"
python server.py
```

### Server Port

The backend runs on port **9160** by default. To change it, edit `backend/config.py`:

```python
PORT = 9160  # Change to your preferred port
```

> **Note:** If you change the port, update the server address in the extension settings (gear icon) to match.

### Backend Server Address (Extension)

By default the extension connects to `localhost:9160`. To connect to a remote backend:

1. Click the **gear icon** in the extension popup
2. Enter the server address (e.g., `192.168.1.50:9160`)
3. Click **Save**

The setting is saved in Chrome and persists across sessions. Clear the field and click Save to reset to the default.

---

## Supported Sites

VidTool supports any site that yt-dlp supports. Some popular ones:

| Platform | Status |
|----------|--------|
| YouTube | Fully supported |
| YouTube Shorts | Fully supported |
| Vimeo | Fully supported |
| Twitter / X | Fully supported |
| TikTok | Fully supported |
| Instagram (posts, reels) | Fully supported |
| Reddit | Fully supported |
| Facebook | Supported (public videos) |
| Twitch (VODs) | Fully supported |
| Dailymotion | Fully supported |
| Bilibili | Fully supported |
| SoundCloud | Audio supported |
| Bandcamp | Audio supported |
| Generic HTML5 `<video>` | Supported via DOM scanning |
| HLS streams (.m3u8) | Supported via network detection |
| DASH streams (.mpd) | Supported via network detection |
| **1000+ others** | Via yt-dlp extractors |

For the full list, see the [yt-dlp supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> **Note:** DRM-protected content (Netflix, Disney+, Amazon Prime Video, etc.) **cannot** be downloaded. These services use Widevine DRM which prevents extraction.

---

## Troubleshooting

### "Backend is not running"

The popup shows this when it can't connect to the local server.

**Fix:** Start the backend server:
```bash
cd backend
source .venv/bin/activate
python server.py
```

### "No videos detected on this page"

The extension couldn't find videos through DOM scanning or platform URL matching.

**Fixes:**
- Click **"Try with yt-dlp"** — the backend may still be able to extract the video
- Ensure the video has actually loaded/played on the page (some sites lazy-load videos)
- Close and reopen the popup to re-scan after the video loads

### Download starts but fails with an error

**Common causes:**
- **ffmpeg not installed:** Required for merging video+audio. Install with `brew install ffmpeg`
- **Rate limiting:** Some sites limit download speed or frequency. Try again after a few minutes
- **Geo-restricted content:** The video may not be available in your region
- **Site changes:** yt-dlp extractors may need updating. Run: `pip install -U yt-dlp`

### Progress bar stuck at 0%

This usually means yt-dlp is extracting video metadata (which can take a few seconds) before the actual download begins. Wait a moment.

If it stays stuck for over 30 seconds, the URL may be unsupported or the site may be blocking the request.

### Extension not appearing in Chrome

- Make sure **Developer mode** is enabled at `chrome://extensions/`
- Make sure you selected the `extension/` folder (not the project root)
- Check for errors on the extensions page — click "Errors" on the VidTool card

### Port 9160 already in use

Another process is using the port. Either:
- Kill the existing process: `lsof -ti:9160 | xargs kill`
- Or change the port in `backend/config.py` (and update the extension — see [Configuration](#configuration))

### Updating yt-dlp

yt-dlp receives frequent updates to keep up with site changes. To update:

```bash
cd backend
source .venv/bin/activate
pip install -U yt-dlp
```

---

## Uninstalling

### Remove the Chrome extension
1. Go to `chrome://extensions/`
2. Find VidTool and click **Remove**

### Remove the backend
```bash
# Delete the project folder
rm -rf /path/to/vidtool
```

### Remove downloaded videos
```bash
rm -rf ~/Downloads/VidTool
```

---

## Project Structure

```
vidtool/
├── backend/                          # Python backend server (FastAPI)
│   ├── config.py                     # Server configuration (port, download dir)
│   ├── downloader.py                 # yt-dlp download engine + fallback downloader
│   ├── server.py                     # FastAPI HTTP server (endpoints + SSE)
│   └── requirements.txt             # Python dependencies
│
├── standalone/                       # Zero-dependency backend (Python 2.7+)
│   ├── backend/
│   │   └── server.py                 # Standalone HTTP server (stdlib only)
│   ├── extension/                    # Copy of Chrome extension
│   └── scripts/
│       └── install.sh
│
├── docker/                           # Docker setup for network-hosted backend
│   ├── Dockerfile                    # Container image (Python 3.11 + yt-dlp + ffmpeg)
│   ├── setup.sh                      # Build the Docker image
│   ├── start.sh                      # Start the container
│   ├── stop.sh                       # Stop the container
│   └── README.md                     # Docker-specific documentation
│
├── extension/                        # Chrome Extension (Manifest V3)
│   ├── manifest.json                 # Extension manifest (Chrome 88+)
│   ├── background/
│   │   └── service-worker.js         # Network observer for HLS/DASH streams
│   ├── content/
│   │   └── detector.js               # Page scanner (video elements, platforms, embeds)
│   ├── popup/
│   │   ├── popup.html                # Extension popup UI (with settings panel)
│   │   ├── popup.css                 # Popup styles
│   │   └── popup.js                  # Popup logic (scan, download, progress, settings)
│   └── icons/
│       ├── icon16.png                # Toolbar icon
│       ├── icon48.png                # Extensions page icon
│       └── icon128.png               # Chrome Web Store icon
│
├── scripts/
│   └── install.sh                    # One-step setup script
│
└── README.md                         # This file
```

---

## Security Notes

- **Local mode**: The backend binds to `127.0.0.1` (localhost only) — not accessible from the network
- **Network mode (Docker)**: The backend binds to `0.0.0.0` inside the container and is accessible to other machines on the LAN via port 9160. Traffic is unencrypted HTTP. Do not expose this port to the internet
- No authentication is used — in local mode this is safe; in network mode, anyone on your LAN can use the backend
- The extension requires `<all_urls>` host permission for network stream detection — this is the same permission model used by ad blockers
- No data is sent to any external server — all processing happens on your machines
- The `/file/` endpoint includes path traversal protection and only serves files from the download directory

---

## License

This project is for personal use. It relies on yt-dlp which is released under the Unlicense.
Video downloading may be subject to the terms of service of individual websites.
Always respect copyright and only download content you have the right to access.
