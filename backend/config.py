import os
from pathlib import Path

DOWNLOAD_DIR = os.environ.get(
    "VIDTOOL_DOWNLOAD_DIR",
    str(Path.home() / "Downloads" / "VidTool")
)
HOST = "127.0.0.1"
PORT = 9160
