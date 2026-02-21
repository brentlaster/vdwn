import uuid
import threading
from pathlib import Path

import yt_dlp
import requests

from config import DOWNLOAD_DIR

# In-memory task state: task_id -> progress dict
tasks = {}

QUALITY_MAP = {
    "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
    "720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best",
    "480p": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]/best",
    "audio-only": "bestaudio[ext=m4a]/bestaudio",
}


def create_task(url, quality):
    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "percent": 0,
        "speed": "",
        "eta": "",
        "filename": "",
        "error": "",
    }
    t = threading.Thread(target=_run_download, args=(task_id, url, quality), daemon=True)
    t.start()
    return task_id


def _run_download(task_id, url, quality):
    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

    def progress_hook(d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            pct = (downloaded / total * 100) if total > 0 else 0
            tasks[task_id].update({
                "status": "downloading",
                "percent": round(pct, 1),
                "speed": d.get("_speed_str", ""),
                "eta": d.get("_eta_str", ""),
            })
        elif d.get("status") == "finished":
            tasks[task_id].update({
                "status": "processing",
                "percent": 100,
                "filename": Path(d.get("filename", "")).name,
            })

    fmt = QUALITY_MAP.get(quality, QUALITY_MAP["best"])
    ydl_opts = {
        "format": fmt,
        "outtmpl": str(Path(DOWNLOAD_DIR) / "%(title)s.%(ext)s"),
        "progress_hooks": [progress_hook],
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            tasks[task_id].update({
                "status": "finished",
                "percent": 100,
                "filename": Path(filename).name,
            })
    except Exception as e:
        if not _try_direct_download(task_id, url):
            tasks[task_id].update({
                "status": "error",
                "error": str(e),
            })


def _try_direct_download(task_id, url):
    """Fallback: download raw video file URLs that yt-dlp cannot handle."""
    try:
        video_exts = (".mp4", ".webm", ".mkv", ".avi", ".mov", ".flv", ".m4v")
        lower = url.lower().split("?")[0]
        if not any(lower.endswith(ext) for ext in video_exts):
            return False

        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        slug = url.split("/")[-1].split("?")[0] or "video.mp4"
        # Sanitize filename
        slug = "".join(c for c in slug if c.isalnum() or c in "._-")[:200]
        filepath = Path(DOWNLOAD_DIR) / slug

        downloaded = 0
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    tasks[task_id].update({
                        "status": "downloading",
                        "percent": round(downloaded / total * 100, 1),
                    })

        tasks[task_id].update({
            "status": "finished",
            "percent": 100,
            "filename": slug,
        })
        return True
    except Exception:
        return False


def get_task(task_id):
    return tasks.get(task_id)
