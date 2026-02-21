# VidTool Setup on macOS High Sierra (10.13)

This guide covers running VidTool on an older Mac running macOS High Sierra
with Docker CE 17.06. The backend runs inside a Docker container with modern
yt-dlp and ffmpeg, while the Chrome extension runs natively on the Mac.

---

## Prerequisites

- macOS High Sierra (10.13)
- Docker CE 17.06 (already installed and running)
- Chrome 88+
- Internet connection (VPN if needed for geo-restricted content)

---

## Step 1: Get the VidTool Files

Copy the entire `vidtool` project to the Mac, e.g. to `~/Desktop/vidtool`.

---

## Step 2: Download the yt-dlp Binary

The container needs the standalone Linux binary of yt-dlp, which bundles its
own Python runtime. Download it **on the Mac** (not inside Docker):

```bash
cd ~/Desktop/vidtool
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux -o docker/yt-dlp
```

If `curl` can't resolve `github.com`, download `yt-dlp_linux` from a browser:

1. Go to https://github.com/yt-dlp/yt-dlp/releases
2. Under the latest release, find and download `yt-dlp_linux`
3. Save it as `docker/yt-dlp` in the project folder

---

## Step 3: Build the Docker Image

```bash
cd ~/Desktop/vidtool
docker build -t vidtool -f docker/Dockerfile.legacy .
```

### Important Notes

- **Use `Dockerfile.legacy`**, not `Dockerfile`. The legacy version is
  specifically designed for Docker CE 17.06 on High Sierra.
- The image uses `debian:buster-slim` (the newest image Docker 17.06 can
  pull without signature errors).
- Debian Buster's repos are archived, so the Dockerfile points apt at
  `archive.debian.org`.
- System Python (3.7) runs the VidTool server. The yt-dlp standalone binary
  bundles its own Python 3.10+ internally.

### If the build fails

| Error | Fix |
|-------|-----|
| Missing signature key on `docker pull` | Only `debian:buster-slim` and `alpine:3.14` are known to pull on Docker 17.06. The Dockerfile.legacy uses buster. |
| `could not resolve host` during build | DNS isn't working inside Docker. Download files on the host and COPY them in (which is what the Dockerfile.legacy already does for yt-dlp). |
| `apt-get` 404 / "does not have a Release file" | The Dockerfile must point apt at `archive.debian.org`. This is already configured in Dockerfile.legacy. |
| `unsupported version of Python` from yt-dlp | You downloaded the plain `yt-dlp` script instead of `yt-dlp_linux`. The `_linux` binary bundles its own Python. |

---

## Step 4: Run the Container

```bash
docker run -d \
  --name vidtool \
  --restart unless-stopped \
  -p 9160:9160 \
  -v "$HOME/Downloads/VidTool:/downloads" \
  vidtool
```

Verify it's running:

```bash
curl http://localhost:9160/health
```

### VPN Note

If you need to download from geo-restricted sites through a VPN, the VPN
must be active on the Mac **before** starting the container. Docker for Mac
routes container traffic through the host's network, so the container
inherits the VPN connection.

---

## Step 5: Install the Chrome Extension

1. Open `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right)
3. Click **Load unpacked**
4. Select the `extension/` folder from the project (the main one, not `standalone/extension/`)

### Extension Features

- **Settings**: Click the gear icon to configure the backend server address.
  For local use, leave it as the default (`localhost:9160`).
- **Custom filename**: Type a name in the "Save as" field before downloading.
  Files are saved hidden (dot-prefixed) on the server.
- **Save to this computer**: After a download finishes, click the "Save to
  this computer" link to transfer the file via the browser.

---

## Managing the Container

```bash
# View logs (useful for debugging download errors):
docker logs -f vidtool

# Stop the container:
docker stop vidtool && docker rm vidtool

# Restart (after reboot or Docker restart):
docker run -d \
  --name vidtool \
  --restart unless-stopped \
  -p 9160:9160 \
  -v "$HOME/Downloads/VidTool:/downloads" \
  vidtool
```

---

## Updating yt-dlp

yt-dlp needs regular updates as sites change their APIs. To update:

```bash
cd ~/Desktop/vidtool

# Download the latest binary:
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux -o docker/yt-dlp

# Rebuild the image:
docker build -t vidtool -f docker/Dockerfile.legacy .

# Restart the container:
docker stop vidtool && docker rm vidtool
docker run -d \
  --name vidtool \
  --restart unless-stopped \
  -p 9160:9160 \
  -v "$HOME/Downloads/VidTool:/downloads" \
  vidtool
```

---

## Adding Custom yt-dlp Extractors

You can add custom or updated extractors from the yt-dlp source:

1. Create the plugin directory (already done in the project):
   ```
   docker/plugins/yt_dlp_plugins/extractor/
   ```

2. Download an extractor from
   `https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/yt_dlp/extractor/FILENAME.py`
   and save it in the plugin directory with an underscore prefix:
   ```bash
   curl -L https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/yt_dlp/extractor/SITE.py \
     -o docker/plugins/yt_dlp_plugins/extractor/_SITE.py
   ```

3. Edit the file and fix relative imports:
   - Change `from .common import InfoExtractor`
     to `from yt_dlp.extractor.common import InfoExtractor`
   - Change `from ..utils import ...`
     to `from yt_dlp.utils import ...`

4. Rebuild the image:
   ```bash
   docker build -t vidtool -f docker/Dockerfile.legacy .
   ```

---

## Download Directory

Videos are saved to `~/Downloads/VidTool` on the Mac by default. This is
volume-mounted into the container.

To change it, set the environment variable when running the container:

```bash
docker run -d \
  --name vidtool \
  --restart unless-stopped \
  -p 9160:9160 \
  -v "/path/to/your/folder:/downloads" \
  vidtool
```

---

## Architecture

```
macOS High Sierra
┌──────────────────────────────────────────────────┐
│                                                  │
│  Chrome + VidTool Extension                      │
│  (connects to localhost:9160)                    │
│       │                                          │
│       ▼                                          │
│  Docker CE 17.06                                 │
│  ┌────────────────────────────────────────────┐  │
│  │  Container (debian:buster-slim)            │  │
│  │                                            │  │
│  │  server.py ──► yt-dlp_linux ──► ffmpeg     │  │
│  │  (Python 3.7)   (bundled Python 3.10+)     │  │
│  │                                            │  │
│  │  Port 9160    Volume: ~/Downloads/VidTool  │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  VPN (if needed for geo-restricted content)      │
└──────────────────────────────────────────────────┘
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Build image | `docker build -t vidtool -f docker/Dockerfile.legacy .` |
| Start container | `docker run -d --name vidtool --restart unless-stopped -p 9160:9160 -v "$HOME/Downloads/VidTool:/downloads" vidtool` |
| Stop container | `docker stop vidtool && docker rm vidtool` |
| View logs | `docker logs -f vidtool` |
| Update yt-dlp | Download new `yt-dlp_linux` → rebuild → restart |
| Test backend | `curl http://localhost:9160/health` |
