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


def _ffmpeg_source():
    # A binary from `shutil.which` (Homebrew on macOS, a chocolatey shim on
    # Windows) depends on its original install location and breaks on the end
    # user's machine. imageio-ffmpeg ships a self-contained STATIC ffmpeg per
    # platform via pip (includes libx264 for the H.264 re-encode), so it just
    # works when bundled. FFMPEG_BINARY overrides it if ever needed.
    env = os.environ.get("FFMPEG_BINARY")
    if env and os.path.isfile(env):
        return env
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return find_binary("ffmpeg")


def stage_ffmpeg(staging_dir):
    plat = platform_dir_name()
    exe_suffix = ".exe" if sys.platform.startswith("win") else ""
    dest_dir = os.path.join(staging_dir, "vendor", "ffmpeg", plat)
    os.makedirs(dest_dir, exist_ok=True)

    _copy_binary(_ffmpeg_source(), os.path.join(dest_dir, "ffmpeg" + exe_suffix))
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

    # App icon (macOS .icns, Windows .ico). Linux ELF binaries carry no icon.
    icon = {"macos": "icon.icns", "windows": "icon.ico"}.get(plat)
    if icon:
        icon_path = os.path.join(ROOT, "assets", icon)
        if os.path.isfile(icon_path):
            args.append(f"--icon={icon_path}")
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
