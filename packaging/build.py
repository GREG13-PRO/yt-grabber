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


def stage_ffmpeg(staging_dir):
    plat = platform_dir_name()
    exe_suffix = ".exe" if sys.platform.startswith("win") else ""

    ffmpeg_src = find_binary("ffmpeg")
    ffmpeg_dest_dir = os.path.join(staging_dir, "vendor", "ffmpeg", plat)
    os.makedirs(ffmpeg_dest_dir, exist_ok=True)
    shutil.copy2(ffmpeg_src, os.path.join(ffmpeg_dest_dir, "ffmpeg" + exe_suffix))

    return ffmpeg_dest_dir


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
    # .app bundle (wrapped into a .dmg afterwards). Windows/Linux get a single
    # portable executable, matching what users expect there.
    if plat != "macos":
        args.append("--onefile")
    args.append(os.path.join(ROOT, "desktop.py"))

    print("Futtatás:", " ".join(args))
    subprocess.run(args, check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
