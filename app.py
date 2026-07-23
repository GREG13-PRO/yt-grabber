import os
import shutil
import subprocess
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


def _pick_h264_encoder():
    # Pick the fastest available H.264 encoder for re-encoding high-res
    # (AV1/VP9) downloads. Prefer a hardware encoder for the platform's GPU
    # (Apple VideoToolbox, NVIDIA NVENC, Intel QuickSync, AMD AMF); fall back
    # to software libx264. "Listed" doesn't guarantee "works" (e.g. nvenc with
    # no NVIDIA GPU), so _reencode_to_h264 retries with libx264 on failure.
    if not FFMPEG_PATH:
        return None
    try:
        out = subprocess.run(
            [FFMPEG_PATH, "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=15,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for enc in ("h264_videotoolbox", "h264_nvenc", "h264_qsv", "h264_amf", "libx264"):
        if enc in out:
            return enc
    return None


H264_ENCODER = _pick_h264_encoder()

ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}

def _compatible_format(max_height):
    # <=1080p: prefer H.264 (avc1) + AAC. These are hardware-decoded and play
    # smoothly everywhere (QuickTime included). Picking the raw "bestvideo"
    # would often grab VP9, which QuickTime renders as green/stuttering frames.
    return (
        f"bestvideo[height<={max_height}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
        f"bestvideo[height<={max_height}][vcodec^=av01]+bestaudio/"
        f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]"
    )


def _highres_format(max_height):
    # >1080p: no H.264 exists on YouTube, so prefer AV1 over VP9. VP9 muxed
    # into an mp4 container is what produces the green frames in QuickTime;
    # AV1-in-mp4 plays cleanly in VLC and modern QuickTime.
    return (
        f"bestvideo[height<={max_height}][vcodec^=av01]+bestaudio/"
        f"bestvideo[height<={max_height}][vcodec^=vp9]+bestaudio/"
        f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]"
    )


QUALITY_FORMAT_MAP = {
    "best": "bestvideo[vcodec^=av01]+bestaudio/bestvideo+bestaudio/best",
    "2160p": _highres_format(2160),
    "1440p": _highres_format(1440),
    "1080p": _compatible_format(1080),
    "720p": _compatible_format(720),
    "480p": _compatible_format(480),
    "360p": _compatible_format(360),
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
    for label, min_height in (
        ("2160p", 2160),
        ("1440p", 1440),
        ("1080p", 1080),
        ("720p", 720),
        ("480p", 480),
        ("360p", 360),
    ):
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


def _selected_vcodec(info):
    downloads = info.get("requested_downloads") or []
    if downloads and downloads[0].get("vcodec"):
        return downloads[0]["vcodec"]
    return info.get("vcodec") or ""


def _target_bitrate(height):
    if height and height >= 2160:
        return "40M"
    if height and height >= 1440:
        return "20M"
    return "12M"


def _encoder_args(encoder, height):
    if encoder == "libx264":
        # veryfast keeps software encoding as quick as possible (the user is on
        # a machine without a hardware H.264 encoder).
        return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21"]
    # Hardware encoders (videotoolbox / nvenc / qsv / amf) take a bitrate.
    return ["-c:v", encoder, "-b:v", _target_bitrate(height)]


def _run_encode(src_path, tmp_path, encoder, height, duration, download_id):
    # -hwaccel auto uses the GPU to DECODE the AV1/VP9 source when the machine
    # supports it (huge speedup on modern GPUs); it falls back to software
    # decode gracefully. -pix_fmt yuv420p forces 8-bit output so QuickTime can
    # play it (10-bit sources would otherwise green out).
    cmd = [FFMPEG_PATH, "-y", "-hwaccel", "auto", "-i", src_path,
           "-map", "0:v:0", "-map", "0:a:0?"]
    cmd += _encoder_args(encoder, height)
    cmd += [
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-progress", "pipe:1", "-nostats",
        tmp_path,
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    for line in proc.stdout:
        line = line.strip()
        if line.startswith("out_time=") and duration:
            stamp = line.split("=", 1)[1]
            try:
                h, m, s = stamp.split(":")
                seconds = int(h) * 3600 + int(m) * 60 + float(s)
                progress_state[download_id] = {
                    "status": "transcoding",
                    "percent": min(round(seconds / duration * 100, 1), 99.9),
                }
            except (ValueError, IndexError):
                pass
    proc.wait()
    if proc.returncode != 0:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise RuntimeError("Az átkódolás H.264-re nem sikerült.")


def _reencode_to_h264(src_path, info, download_id):
    """Re-encode an AV1/VP9 file to H.264 8-bit yuv420p mp4 so it plays smoothly
    in QuickTime. Tries the fast hardware encoder first; if that fails at
    runtime (e.g. nvenc listed but no NVIDIA GPU), retries with software
    libx264."""
    duration = info.get("duration") or 0
    height = info.get("height") or 0
    tmp_path = src_path + ".h264.mp4"

    encoders = [H264_ENCODER]
    if H264_ENCODER != "libx264":
        encoders.append("libx264")

    last_error = None
    for encoder in encoders:
        try:
            _run_encode(src_path, tmp_path, encoder, height, duration, download_id)
            os.replace(tmp_path, src_path)
            return
        except RuntimeError as e:
            last_error = e
    raise last_error or RuntimeError("Az átkódolás H.264-re nem sikerült.")


def run_download(download_id, url, quality, reencode=True):
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

        # High-res downloads are AV1/VP9 (no H.264 exists above 1080p on
        # YouTube). Re-encode those to H.264 so they play in QuickTime - unless
        # the user opted into fast mode (reencode=False) to skip the slow
        # transcode and play the original in e.g. VLC.
        vcodec = _selected_vcodec(info)
        if (
            reencode
            and quality != "audio"
            and H264_ENCODER
            and vcodec
            and vcodec != "none"
            and not vcodec.startswith("avc1")
        ):
            progress_state[download_id] = {"status": "transcoding", "percent": 0}
            _reencode_to_h264(final_path, info, download_id)

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
    reencode = data.get("reencode", True)

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Adj meg egy érvényes YouTube URL-t."}), 400
    if quality not in QUALITY_FORMAT_MAP:
        return jsonify({"error": "Érvénytelen minőség."}), 400

    download_id = uuid.uuid4().hex
    progress_state[download_id] = {"status": "starting"}
    thread = threading.Thread(
        target=run_download, args=(download_id, url, quality, bool(reencode)), daemon=True
    )
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
