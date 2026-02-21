#!/bin/bash
set -e

echo "=== VidTool Setup ==="
echo ""

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not found."
    echo "Install via: brew install python3"
    exit 1
fi

PYTHON_VER=$(python3 --version 2>&1)
echo "Found: $PYTHON_VER"

# Check ffmpeg (needed by yt-dlp to merge video+audio)
if command -v ffmpeg &> /dev/null; then
    echo "Found: ffmpeg $(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')"
else
    echo ""
    echo "WARNING: ffmpeg not found."
    echo "Some downloads (e.g., YouTube best quality) require ffmpeg to merge"
    echo "separate video and audio streams."
    echo "Install via: brew install ffmpeg"
    echo ""
fi

# Navigate to backend directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"
cd "$BACKEND_DIR"

echo ""
echo "Setting up Python virtual environment..."

# Create venv (compatible with older Python 3.6+)
python3 -m venv .venv

# Activate and install
source .venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

echo ""
echo "=== Setup complete! ==="
echo ""
echo "To start the backend server:"
echo "  cd $(cd "$BACKEND_DIR" && pwd)"
echo "  source .venv/bin/activate"
echo "  python server.py"
echo ""
echo "To install the Chrome extension:"
echo "  1. Open chrome://extensions/"
echo "  2. Enable 'Developer mode' (toggle in top-right)"
echo "  3. Click 'Load unpacked'"
echo "  4. Select: $(cd "$SCRIPT_DIR/../extension" && pwd)"
echo ""
echo "The backend must be running for downloads to work."
