#!/bin/bash
set -e

echo "=== VidTool Standalone Setup ==="
echo ""
echo "This version has NO Python package dependencies."
echo "It only requires Python (2.7+ or 3.x) and yt-dlp."
echo ""

# ─── Check Python ────────────────────────────────────────────────────────────

PYTHON_BIN=""

# Try python3 first, then python, then python2
for candidate in python3 python python2; do
    if command -v "$candidate" &> /dev/null; then
        VER=$("$candidate" --version 2>&1 | head -1)
        echo "Found: $VER ($(command -v $candidate))"
        PYTHON_BIN="$candidate"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "ERROR: Python not found."
    echo ""
    echo "Install Python via one of:"
    echo "  brew install python3"
    echo "  https://www.python.org/downloads/"
    exit 1
fi

# ─── Check yt-dlp ────────────────────────────────────────────────────────────

echo ""
YTDLP_BIN=""

for candidate in yt-dlp yt_dlp; do
    if command -v "$candidate" &> /dev/null; then
        VER=$("$candidate" --version 2>&1)
        echo "Found: yt-dlp $VER ($(command -v $candidate))"
        YTDLP_BIN="$candidate"
        break
    fi
done

if [ -z "$YTDLP_BIN" ]; then
    echo "WARNING: yt-dlp not found!"
    echo ""
    echo "yt-dlp is required for downloading videos."
    echo "Install it via one of:"
    echo "  brew install yt-dlp           (recommended on macOS)"
    echo "  pip install yt-dlp            (if using pip)"
    echo "  pip3 install yt-dlp"
    echo "  curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp && chmod +x /usr/local/bin/yt-dlp"
    echo ""
fi

# ─── Check ffmpeg ────────────────────────────────────────────────────────────

echo ""
if command -v ffmpeg &> /dev/null; then
    FFVER=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
    echo "Found: ffmpeg $FFVER"
else
    echo "WARNING: ffmpeg not found."
    echo "Some downloads require ffmpeg to merge video + audio streams."
    echo "Install via: brew install ffmpeg"
fi

# ─── Make server executable ──────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$SCRIPT_DIR/../backend/server.py"
chmod +x "$BACKEND"

echo ""
echo "=== Setup complete! ==="
echo ""
echo "No virtual environment needed - zero Python dependencies!"
echo ""
echo "To start the backend server:"
echo "  $PYTHON_BIN $BACKEND"
echo ""
echo "Optional flags:"
echo "  --port 9160              Change the server port"
echo "  --download-dir ~/Videos  Change download location"
echo ""
echo "To install the Chrome extension:"
echo "  1. Open chrome://extensions/"
echo "  2. Enable 'Developer mode' (toggle in top-right)"
echo "  3. Click 'Load unpacked'"
echo "  4. Select: $(cd "$SCRIPT_DIR/../extension" && pwd)"
echo ""
echo "The backend must be running for downloads to work."
