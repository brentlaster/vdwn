#!/bin/bash
set -e

echo "=== Starting VidTool Backend (Docker) ==="
echo ""

# ─── Stop existing container if running ──────────────────────────────────────

if docker ps -a --format '{{.Names}}' | grep -q "^vidtool$"; then
    echo "Stopping existing VidTool container..."
    docker stop vidtool 2>/dev/null || true
    docker rm vidtool 2>/dev/null || true
fi

# ─── Build if image doesn't exist ───────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if ! docker image inspect vidtool > /dev/null 2>&1; then
    echo "Building VidTool image..."
    docker build -t vidtool -f "$SCRIPT_DIR/Dockerfile" "$PROJECT_DIR"
    echo ""
fi

# ─── Determine download directory ───────────────────────────────────────────

DOWNLOAD_DIR="${VIDTOOL_DOWNLOAD_DIR:-$HOME/Downloads/VidTool}"
mkdir -p "$DOWNLOAD_DIR"

# ─── Start the container ────────────────────────────────────────────────────

echo "Download directory: $DOWNLOAD_DIR"
echo ""

docker run -d \
    --name vidtool \
    --restart unless-stopped \
    -p 9160:9160 \
    -v "$DOWNLOAD_DIR:/downloads" \
    vidtool

# ─── Show connection info ───────────────────────────────────────────────────

sleep 2

# Get the machine's LAN IP
LAN_IP=""
if command -v hostname &> /dev/null; then
    LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
fi
if [ -z "$LAN_IP" ] && command -v ipconfig &> /dev/null; then
    # macOS
    LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)
fi
if [ -z "$LAN_IP" ]; then
    LAN_IP=$(ifconfig 2>/dev/null | grep 'inet ' | grep -v '127.0.0.1' | head -1 | awk '{print $2}' || true)
fi

echo "=== VidTool backend is running ==="
echo ""
echo "Local:   http://localhost:9160"
if [ -n "$LAN_IP" ]; then
    echo "Network: http://$LAN_IP:9160"
    echo ""
    echo "To connect from another computer:"
    echo "  1. Open the VidTool extension"
    echo "  2. Click the gear icon"
    echo "  3. Enter: $LAN_IP:9160"
    echo "  4. Click Save"
fi
echo ""
echo "Downloads saved to: $DOWNLOAD_DIR"
echo "Stop with: bash $(cd "$(dirname "$0")" && pwd)/stop.sh"
echo ""
