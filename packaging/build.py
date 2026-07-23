"""Cross-platform PyInstaller build driver.

Locates the ffmpeg binary the CI runner already has installed (via the OS
package manager) and bundles it into the app, so the packaged app works
standalone without the end user installing anything else.

Usage: python packaging/build.py
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_NAME = "YT Grabber"


def platform_dir_name():
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    return "linux"


def find_binary(name):
    path = shutil.which(name)
    if not path:
        print(f"HIBA: '{name}' nem található a PATH-on. Telepítsd a build előtt.", file=sys.stderr)
        sys.exit(1)
    return path


def _copy_binary(src, dest):
    shutil.copy2(src, dest)
    if not sys.platform.startswith("win"):
        os.chmod(dest, 0o755)


def stage_ffmpeg(staging_dir):
    plat = platform_dir_name()
    exe_suffix = ".exe" if sys.platform.startswith("win") else ""
    dest_dir = os.path.join(staging_dir, "vendor", "ffmpeg", plat)
    os.makedirs(dest_dir, exist_ok=True)

    # Prefer a STATIC binary passed explicitly via FFMPEG_BINARY. A binary
    # taken from `shutil.which` (Homebrew on macOS, a chocolatey shim on
    # Windows) depends on its original install location and breaks on the end
    # user's machine - hence the CI downloads a self-contained static build and
    # points these env vars at it.
    ffmpeg_src = os.environ.get("FFMPEG_BINARY") or find_binary("ffmpeg")
    _copy_binary(ffmpeg_src, os.path.join(dest_dir, "ffmpeg" + exe_suffix))

    # yt-dlp also looks for ffprobe next to ffmpeg; bundle it when available.
    ffprobe_src = os.environ.get("FFPROBE_BINARY") or shutil.which("ffprobe")
    if ffprobe_src and os.path.isfile(ffprobe_src):
        _copy_binary(ffprobe_src, os.path.join(dest_dir, "ffprobe" + exe_suffix))

    return dest_dir


def add_data_arg(src, dest_in_bundle):
    sep = ";" if sys.platform.startswith("win") else ":"
    return f"--add-data={src}{sep}{dest_in_bundle}"


def main():
    staging_dir = os.path.join(ROOT, "build_staging")
    if os.path.isdir(staging_dir):
        shutil.rmtree(staging_dir)
    os.makedirs(staging_dir)

    plat = platform_dir_name()
    ffmpeg_dir = stage_ffmpeg(staging_dir)

    args = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        f"--name={APP_NAME}",
        add_data_arg(os.path.join(ROOT, "templates"), "templates"),
        add_data_arg(os.path.join(ROOT, "static"), "static"),
        add_data_arg(ffmpeg_dir, os.path.join("vendor", "ffmpeg", plat)),
    ]
    # macOS keeps the default onedir output so PyInstaller produces a proper
    # .app bundle (wrapped into a .dmg afterwards). Windows also uses onedir so
    # the Inno Setup installer can package the folder into a real installer
    # (Start Menu + uninstaller). Only Linux ships a single portable binary.
    if plat == "linux":
        args.append("--onefile")
    args.append(os.path.join(ROOT, "desktop.py"))

    print("Futtatás:", " ".join(args))
    subprocess.run(args, check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
