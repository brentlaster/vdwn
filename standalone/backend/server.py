#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VidTool Standalone Backend Server

A zero-dependency HTTP server that uses yt-dlp CLI for video downloads.
Compatible with Python 2.7+ and all Python 3.x versions.

Usage:
    python server.py
    python server.py --port 9160
    python server.py --download-dir ~/Videos
"""

from __future__ import print_function, unicode_literals

import json
import os
import re
import subprocess
import sys
import threading
import uuid
import time

# Python 2/3 compatibility
PY2 = sys.version_info[0] == 2

if PY2:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from urlparse import urlparse, parse_qs
    text_type = unicode
    string_types = (str, unicode)
else:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs
    text_type = str
    string_types = (str,)

# ─── Configuration ───────────────────────────────────────────────────────────

DEFAULT_PORT = 9160
DEFAULT_HOST = "127.0.0.1"
DEFAULT_DOWNLOAD_DIR = os.path.join(
    os.path.expanduser("~"), "Downloads", "VidTool"
)

# Read from environment or use defaults
HOST = os.environ.get("VIDTOOL_HOST", DEFAULT_HOST)
PORT = int(os.environ.get("VIDTOOL_PORT", DEFAULT_PORT))
DOWNLOAD_DIR = os.environ.get("VIDTOOL_DOWNLOAD_DIR", DEFAULT_DOWNLOAD_DIR)

# ─── Quality presets (yt-dlp format strings) ─────────────────────────────────

QUALITY_MAP = {
    "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
    "720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best",
    "480p": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]/best",
    "audio-only": "bestaudio[ext=m4a]/bestaudio",
}

# ─── Task tracking ───────────────────────────────────────────────────────────

tasks = {}       # task_id -> dict with status, percent, speed, etc.
tasks_lock = threading.Lock()


def new_task_id():
    """Generate a short unique task ID."""
    return str(uuid.uuid4()).replace("-", "")[:8]


def update_task(task_id, **kwargs):
    """Thread-safe task state update."""
    with tasks_lock:
        if task_id in tasks:
            tasks[task_id].update(kwargs)


def get_task(task_id):
    """Thread-safe task state read."""
    with tasks_lock:
        t = tasks.get(task_id)
        if t is not None:
            return dict(t)  # return a copy
        return None

# ─── yt-dlp CLI wrapper ─────────────────────────────────────────────────────

def find_ytdlp():
    """Locate the yt-dlp binary. Returns path or None."""
    # Check common locations
    candidates = ["yt-dlp", "yt_dlp"]

    # Also check Homebrew paths (macOS)
    brew_paths = [
        "/usr/local/bin/yt-dlp",
        "/opt/homebrew/bin/yt-dlp",
    ]
    for bp in brew_paths:
        if os.path.isfile(bp):
            return bp

    # Try PATH
    for name in candidates:
        try:
            with open(os.devnull, "w") as devnull:
                subprocess.check_call(
                    [name, "--version"],
                    stdout=devnull, stderr=devnull
                )
            return name
        except (OSError, subprocess.CalledProcessError):
            continue

    return None


YTDLP_BIN = find_ytdlp()


def run_download(task_id, url, quality, custom_filename=""):
    """
    Run yt-dlp as a subprocess, parsing its stdout for progress updates.
    This runs in a background thread.
    """
    if not YTDLP_BIN:
        update_task(task_id, status="error",
                    error="yt-dlp not found. Install via: brew install yt-dlp")
        return

    # Ensure download directory exists
    if not os.path.isdir(DOWNLOAD_DIR):
        try:
            os.makedirs(DOWNLOAD_DIR)
        except OSError:
            pass

    fmt = QUALITY_MAP.get(quality, QUALITY_MAP["best"])

    # Files are saved hidden (dot-prefix) on the server.
    # The display_name (without dot) is used when serving to remote clients.
    if custom_filename:
        # Use custom name; yt-dlp will add the extension
        output_template = os.path.join(DOWNLOAD_DIR, "." + custom_filename + ".%(ext)s")
    else:
        output_template = os.path.join(DOWNLOAD_DIR, ".%(title)s.%(ext)s")

    cmd = [
        YTDLP_BIN,
        "--newline",                # one progress line per update (crucial for parsing)
        "-f", fmt,
        "-o", output_template,
        "--merge-output-format", "mp4",
        "--no-playlist",            # download single video, not entire playlist
        "--encoding", "utf-8",
        url,
    ]

    update_task(task_id, status="downloading", percent=0)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )

        filename = ""
        for raw_line in iter(proc.stdout.readline, b""):
            try:
                line = raw_line.decode("utf-8", errors="replace").strip()
            except Exception:
                continue

            if not line:
                continue

            # Log all yt-dlp output for debugging
            sys.stderr.write("[yt-dlp] %s\n" % line)
            sys.stderr.flush()

            # Parse yt-dlp progress lines like:
            #   [download]  42.3% of ~50.00MiB at 2.10MiB/s ETA 00:14
            #   [download]  42.3% of 50.00MiB at 2.10MiB/s ETA 00:14
            progress_match = re.search(
                r'\[download\]\s+([\d.]+)%\s+of\s+~?([\d.]+\S+)\s+at\s+(\S+)\s+ETA\s+(\S+)',
                line
            )
            if progress_match:
                pct = float(progress_match.group(1))
                speed = progress_match.group(3)
                eta = progress_match.group(4)
                update_task(task_id,
                            status="downloading",
                            percent=round(pct, 1),
                            speed=speed,
                            eta=eta)
                continue

            # Detect "100%" line (no ETA)
            done_match = re.search(
                r'\[download\]\s+100%\s+of\s+',
                line
            )
            if done_match:
                update_task(task_id, status="processing", percent=100)
                continue

            # Detect "Destination:" line for filename
            dest_match = re.search(r'\[download\]\s+Destination:\s+(.+)', line)
            if dest_match:
                filename = os.path.basename(dest_match.group(1).strip())
                continue

            # Detect "[Merger]" or "[ExtractAudio]" lines (post-processing)
            if "[Merger]" in line or "[ExtractAudio]" in line:
                update_task(task_id, status="processing", percent=100)
                continue

            # Detect "has already been downloaded" line
            if "has already been downloaded" in line:
                already_match = re.search(
                    r'\[download\]\s+(.+?)\s+has already been downloaded',
                    line
                )
                if already_match:
                    filename = os.path.basename(already_match.group(1).strip())
                display = _display_name(filename) if filename else "already downloaded"
                update_task(task_id,
                            status="finished",
                            percent=100,
                            filename=filename or "already downloaded",
                            display_name=display)
                break

        proc.stdout.close()
        ret = proc.wait()

        if ret == 0:
            # Try to find the actual output filename if we didn't capture it
            if not filename:
                filename = find_latest_file(DOWNLOAD_DIR)
            display = _display_name(filename) if filename else "download complete"
            update_task(task_id,
                        status="finished",
                        percent=100,
                        filename=filename or "download complete",
                        display_name=display)
        else:
            task = get_task(task_id)
            if task and task.get("status") != "finished":
                update_task(task_id,
                            status="error",
                            error="yt-dlp exited with code %d" % ret)

    except Exception as e:
        update_task(task_id, status="error", error=str(e))


def _display_name(filename):
    """Strip the leading dot from hidden filenames for display/download."""
    if filename.startswith("."):
        return filename[1:]
    return filename


def find_latest_file(directory):
    """Find the most recently modified file in the download directory."""
    try:
        files = []
        for f in os.listdir(directory):
            fp = os.path.join(directory, f)
            if os.path.isfile(fp):
                files.append((os.path.getmtime(fp), f))
        if files:
            files.sort(reverse=True)
            return files[0][1]
    except OSError:
        pass
    return ""

# ─── HTTP Request Handler ────────────────────────────────────────────────────

class VidToolHandler(BaseHTTPRequestHandler):
    """
    Simple HTTP handler with the following endpoints:
        GET  /health              - Backend health check
        POST /download            - Start a download (JSON body: {url, quality})
        GET  /progress/<task_id>  - SSE stream of download progress
    """

    def log_message(self, format, *args):
        msg = format % args
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), msg))
        sys.stderr.flush()

    def _set_cors_headers(self):
        """Allow requests from Chrome extensions and localhost."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status, data):
        """Send a JSON response."""
        body = json.dumps(data)
        if PY2:
            body = body.encode("utf-8")
        else:
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        """Read the request body as a string."""
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return ""
        raw = self.rfile.read(length)
        if PY2:
            return raw.decode("utf-8")
        return raw.decode("utf-8")

    # ── OPTIONS (CORS preflight) ──

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ── GET endpoints ──

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/health":
            self._handle_health()
        elif path.startswith("/progress/"):
            task_id = path.split("/progress/", 1)[1]
            self._handle_progress(task_id)
        elif path.startswith("/file/"):
            task_id = path.split("/file/", 1)[1]
            self._handle_file(task_id)
        else:
            self._send_json(404, {"detail": "Not found"})

    # ── POST endpoints ──

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/download":
            self._handle_download()
        else:
            self._send_json(404, {"detail": "Not found"})

    # ── Endpoint handlers ──

    def _handle_health(self):
        self._send_json(200, {
            "status": "ok",
            "download_dir": DOWNLOAD_DIR,
            "ytdlp": YTDLP_BIN or "not found",
            "python": sys.version,
        })

    def _handle_download(self):
        try:
            body = self._read_body()
            data = json.loads(body)
        except (ValueError, TypeError):
            self._send_json(400, {"detail": "Invalid JSON body"})
            return

        url = data.get("url", "").strip()
        quality = data.get("quality", "best").strip()
        custom_filename = data.get("filename", "").strip()

        if not url or not url.startswith(("http://", "https://")):
            self._send_json(400, {"detail": "Invalid URL"})
            return

        # Sanitize custom filename (keep only safe characters)
        if custom_filename:
            custom_filename = re.sub(r'[^\w\s\-.]', '_', custom_filename)
            custom_filename = custom_filename.strip('. ')

        task_id = new_task_id()
        with tasks_lock:
            tasks[task_id] = {
                "task_id": task_id,
                "status": "queued",
                "percent": 0,
                "speed": "",
                "eta": "",
                "filename": "",
                "display_name": "",
                "error": "",
            }

        t = threading.Thread(target=run_download,
                             args=(task_id, url, quality, custom_filename))
        t.daemon = True
        t.start()

        self._send_json(200, {"task_id": task_id, "status": "queued"})

    def _handle_progress(self, task_id):
        """
        Server-Sent Events stream for download progress.
        Sends JSON updates every 0.5 seconds until the task finishes or errors.
        """
        task = get_task(task_id)
        if task is None:
            self._send_json(404, {"detail": "Task not found"})
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._set_cors_headers()
        self.end_headers()

        try:
            while True:
                task = get_task(task_id)
                if task is None:
                    break

                line = "data: " + json.dumps(task) + "\n\n"
                if PY2:
                    self.wfile.write(line.encode("utf-8"))
                else:
                    self.wfile.write(line.encode("utf-8"))
                self.wfile.flush()

                if task["status"] in ("finished", "error"):
                    break

                time.sleep(0.5)
        except IOError:
            pass  # Client disconnected (covers BrokenPipeError on Py3 too)
        except Exception:
            pass

    def _handle_file(self, task_id):
        """Serve a completed download file so remote clients can save it."""
        task = get_task(task_id)
        if task is None:
            self._send_json(404, {"detail": "Task not found"})
            return

        if task.get("status") != "finished":
            self._send_json(400, {"detail": "Download not finished"})
            return

        filename = task.get("filename", "")
        if not filename:
            self._send_json(404, {"detail": "No filename recorded"})
            return

        filepath = os.path.join(DOWNLOAD_DIR, filename)
        if not os.path.isfile(filepath):
            self._send_json(404, {"detail": "File not found on disk"})
            return

        # Prevent path traversal
        real_dir = os.path.realpath(DOWNLOAD_DIR)
        real_file = os.path.realpath(filepath)
        if not real_file.startswith(real_dir + os.sep) and real_file != real_dir:
            self._send_json(403, {"detail": "Access denied"})
            return

        file_size = os.path.getsize(filepath)

        # Guess content type
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            ".mp4": "video/mp4", ".webm": "video/webm",
            ".mkv": "video/x-matroska", ".avi": "video/x-msvideo",
            ".mov": "video/quicktime", ".m4a": "audio/mp4",
            ".mp3": "audio/mpeg", ".flv": "video/x-flv",
        }
        ctype = content_types.get(ext, "application/octet-stream")

        # Use display_name (without dot prefix) for the downloaded filename
        display_name = task.get("display_name", "") or _display_name(filename)

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(file_size))
        # Encode filename for Content-Disposition (ASCII-safe fallback)
        safe_name = display_name.encode("ascii", errors="replace").decode("ascii")
        self.send_header(
            "Content-Disposition",
            'attachment; filename="%s"' % safe_name.replace('"', '_')
        )
        self._set_cors_headers()
        self.end_headers()

        try:
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except IOError:
            pass  # Client disconnected

# ─── Server startup ──────────────────────────────────────────────────────────

class ThreadedHTTPServer(HTTPServer):
    """Handle each request in a separate thread (for SSE concurrency)."""
    allow_reuse_address = True

    def process_request(self, request, client_address):
        t = threading.Thread(target=self._handle_in_thread,
                             args=(request, client_address))
        t.daemon = True
        t.start()

    def _handle_in_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


def main():
    """Parse CLI arguments and start the server."""
    global DOWNLOAD_DIR  # must be declared before any reference

    # Simple argument parsing without argparse (Python 2.6 compat)
    port = PORT
    download_dir = DOWNLOAD_DIR

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ("--port", "-p") and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        elif args[i] in ("--download-dir", "-d") and i + 1 < len(args):
            download_dir = os.path.expanduser(args[i + 1])
            i += 2
        elif args[i] in ("--help", "-h"):
            print("VidTool Standalone Backend")
            print("")
            print("Usage: python server.py [options]")
            print("")
            print("Options:")
            print("  --port, -p PORT          Server port (default: %d)" % DEFAULT_PORT)
            print("  --download-dir, -d DIR   Download directory")
            print("                           (default: %s)" % DEFAULT_DOWNLOAD_DIR)
            print("  --help, -h               Show this help")
            sys.exit(0)
        else:
            print("Unknown argument: %s" % args[i])
            print("Use --help for usage information.")
            sys.exit(1)

    # Update globals if overridden by CLI
    DOWNLOAD_DIR = download_dir

    # Create download directory
    if not os.path.isdir(DOWNLOAD_DIR):
        try:
            os.makedirs(DOWNLOAD_DIR)
        except OSError as e:
            print("Warning: Could not create download dir: %s" % e)

    # Check yt-dlp
    if not YTDLP_BIN:
        print("=" * 60)
        print("WARNING: yt-dlp not found!")
        print("")
        print("Install it with one of:")
        print("  brew install yt-dlp")
        print("  pip install yt-dlp")
        print("  pip3 install yt-dlp")
        print("")
        print("The server will start, but downloads will fail.")
        print("=" * 60)
        print("")
    else:
        # Print yt-dlp version
        try:
            ver = subprocess.check_output(
                [YTDLP_BIN, "--version"],
                stderr=subprocess.STDOUT
            ).decode("utf-8", errors="replace").strip()
            print("yt-dlp version: %s" % ver)
        except Exception:
            print("yt-dlp found at: %s" % YTDLP_BIN)

    print("Python version: %s" % sys.version.split()[0])
    print("Download directory: %s" % DOWNLOAD_DIR)
    print("")

    server = ThreadedHTTPServer((HOST, port), VidToolHandler)
    print("VidTool backend running on http://%s:%d" % (HOST, port))
    print("Press Ctrl+C to stop.")
    print("")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
