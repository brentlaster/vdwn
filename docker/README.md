# VidTool Docker Setup (Network-Hosted Backend)

Run the VidTool backend in a Docker container on any modern computer on your
network. The Chrome extension runs on a separate machine (e.g., an older Mac)
and connects to the backend over the LAN. Downloaded files are transferred
to the extension machine via the browser.

## Quick Start

On the **server machine** (any computer with Docker):

```bash
# First time — build the image:
bash docker/setup.sh

# Start the backend:
bash docker/start.sh
```

The start script prints the server's LAN IP address.

On the **client machine** (where Chrome runs):

1. Install the extension: chrome://extensions/ → Developer mode → Load unpacked → select the `extension/` folder
2. Click the VidTool extension icon
3. Click the gear icon (settings)
4. Enter the server's address, e.g. `192.168.1.50:9160`
5. Click Save

Downloads are processed on the server. When complete, click **"Save to this computer"**
to transfer the file to your local machine.

## Commands

```bash
# Build / rebuild the image:
bash docker/setup.sh

# Update yt-dlp to latest version:
bash docker/setup.sh --update

# Start the backend:
bash docker/start.sh

# Stop the backend:
bash docker/stop.sh

# View logs:
docker logs -f vidtool
```

## Download Directory

On the server, downloads are saved to `~/Downloads/VidTool` by default.
Override with:

```bash
export VIDTOOL_DOWNLOAD_DIR="/path/to/videos"
bash docker/start.sh
```

## Troubleshooting

### Extension says "Backend not running"
- Verify the server is reachable: `curl http://SERVER_IP:9160/health`
- Check that port 9160 isn't blocked by a firewall
- Make sure you entered the correct address in the extension settings

### "Save to this computer" doesn't work
- The file is served from the backend over HTTP — if the server IP is
  unreachable or the port is blocked, the download link won't work
- Try opening `http://SERVER_IP:9160/health` directly in Chrome to confirm access

### Update yt-dlp
Sites frequently change their APIs. If downloads stop working:
```bash
bash docker/setup.sh --update
bash docker/start.sh
```
