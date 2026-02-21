#!/bin/bash
set -e

echo "=== VidTool Docker Setup ==="
echo ""

if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed."
    echo "Install Docker Desktop from: https://www.docker.com/products/docker-desktop/"
    exit 1
fi
echo "Found: $(docker --version)"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo "Building VidTool Docker image..."

if [ "$1" = "--update" ]; then
    echo "(Rebuilding with --no-cache to get latest yt-dlp)"
    docker build --no-cache -t vidtool -f "$SCRIPT_DIR/Dockerfile" "$PROJECT_DIR"
else
    docker build -t vidtool -f "$SCRIPT_DIR/Dockerfile" "$PROJECT_DIR"
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "To start:  bash $SCRIPT_DIR/start.sh"
echo "To stop:   bash $SCRIPT_DIR/stop.sh"
echo "To update: bash $SCRIPT_DIR/setup.sh --update"
echo ""
