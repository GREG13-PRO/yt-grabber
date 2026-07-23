import os
import shutil
import threading
import uuid
from urllib.parse import urlparse

import certifi

# Some Python installs (notably Homebrew's on macOS) don't wire up the system
# CA bundle, causing SSL verification failures on every request. Point at
# certifi's bundle unless the environment already overrides this.
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

import yt_dlp
from flask import Flask, jsonify, render_template, request, send_from_directory

from paths import bundled_binary, resource_path, user_data_dir

app = Flask(
    __name__,
    template_folder=resource_path("templates"),
    static_folder=resource_path("static"),
)

DOWNLOAD_DIR = os.path.join(user_data_dir(), "downloads")

FFMPEG_PATH = bundled_binary("ffmpeg", "ffmpeg") or shutil.which("ffmpeg")

ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}

QUALITY_FORMAT_MAP = {
    "best": "bestvideo+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
    "audio": "bestaudio/best",
}

# Friss yt-dlp (>=2025.11, ami Python 3.10+-at igényel) jó eséllyel magától
# az "android_vr" klienst választja, ami PO Token nélkül is teljes DASH
# formátumlistát ad (akár 1080p+). Régebbi yt-dlp / Python 3.9 esetén ez
# nem garantált - lásd README "Minőség" szakasz.
EXTRACTOR_ARGS = {}

# In-memory progress tracking: download_id -> {"status": ..., ...}
progress_state = {}


def is_valid_youtube_url(url):
    if not isinstance(url, str) or not url.strip():
        return False
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname.lower() if parsed.hostname else ""
    return host in ALLOWED_HOSTS


def probe_video(url):
    probe_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "extractor_args": EXTRACTOR_ARGS,
    }
    with yt_dlp.YoutubeDL(probe_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    heights = sorted(
        {
            f["height"]
            for f in info.get("formats", [])
            if f.get("vcodec") not in (None, "none") and f.get("height")
        },
        reverse=True,
    )
    max_height = heights[0] if heights else 0

    available = ["best"]
    for label, min_height in (("1080p", 1080), ("720p", 720), ("480p", 480), ("360p", 360)):
        if max_height >= min_height:
            available.append(label)
    available.append("audio")

    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "available": available,
    }


def run_download(download_id, url, quality):
    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            percent = round(downloaded / total * 100, 1) if total else None
            progress_state[download_id] = {
                "status": "downloading",
                "percent": percent,
                "eta": d.get("eta"),
            }
        elif d["status"] == "finished":
            progress_state[download_id] = {"status": "processing"}

    ydl_opts = {
        "format": QUALITY_FORMAT_MAP[quality],
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title).200B [%(id)s].%(ext)s"),
        "noplaylist": True,
        "merge_output_format": "mp4",
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
        "extractor_args": EXTRACTOR_ARGS,
    }
    if FFMPEG_PATH:
        ydl_opts["ffmpeg_location"] = FFMPEG_PATH
    if quality == "audio":
        ydl_opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        final_path = info["requested_downloads"][0]["filepath"]
        progress_state[download_id] = {
            "status": "finished",
            "filename": os.path.basename(final_path),
        }
    except Exception as e:
        progress_state[download_id] = {"status": "error", "error": str(e)}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/formats", methods=["POST"])
def api_formats():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "")

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Adj meg egy érvényes YouTube URL-t."}), 400

    try:
        info = probe_video(url)
    except Exception as e:
        return jsonify({"error": f"Nem sikerült lekérni a videó adatait: {e}"}), 400

    return jsonify(info)


@app.route("/api/download", methods=["POST"])
def api_download():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "")
    quality = data.get("quality", "")

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Adj meg egy érvényes YouTube URL-t."}), 400
    if quality not in QUALITY_FORMAT_MAP:
        return jsonify({"error": "Érvénytelen minőség."}), 400

    download_id = uuid.uuid4().hex
    progress_state[download_id] = {"status": "starting"}
    thread = threading.Thread(target=run_download, args=(download_id, url, quality), daemon=True)
    thread.start()

    return jsonify({"download_id": download_id})


@app.route("/api/progress/<download_id>")
def api_progress(download_id):
    return jsonify(progress_state.get(download_id, {"status": "unknown"}))


@app.route("/downloads/<path:filename>")
def download_file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)


def bootstrap():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    if FFMPEG_PATH is None:
        print("FIGYELEM: ffmpeg nem található. A minőség-egyesítés és MP3 konverzió nem fog működni. Lásd README.md.")


if __name__ == "__main__":
    bootstrap()
    app.run(host="127.0.0.1", port=5000, threaded=True, debug=True, use_reloader=False)
