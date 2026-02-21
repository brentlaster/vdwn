#!/bin/bash

echo "=== Stopping VidTool Backend (Docker) ==="

if docker ps -a --format '{{.Names}}' | grep -q "^vidtool$"; then
    docker stop vidtool
    docker rm vidtool
    echo "VidTool container stopped and removed."
else
    echo "No VidTool container found."
fi
