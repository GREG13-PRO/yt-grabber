"""Cross-platform PyInstaller build driver.

Locates the Node.js and ffmpeg binaries the CI runner already has installed
(via actions/setup-node and the OS package manager) and bundles them into the
app, together with the pre-built bgutil PO-token server, so the packaged app
works standalone without the end user installing anything else.

Usage: python packaging/build.py
Expects to run from the repo root, with vendor/bgutil-server/{build,node_modules}
already built (see scripts/setup_pot_server.sh).
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


def stage_vendor_binaries(staging_dir):
    plat = platform_dir_name()
    exe_suffix = ".exe" if sys.platform.startswith("win") else ""

    node_src = find_binary("node")
    node_dest_dir = os.path.join(staging_dir, "vendor", "node", plat)
    os.makedirs(node_dest_dir, exist_ok=True)
    shutil.copy2(node_src, os.path.join(node_dest_dir, "node" + exe_suffix))

    ffmpeg_src = find_binary("ffmpeg")
    ffmpeg_dest_dir = os.path.join(staging_dir, "vendor", "ffmpeg", plat)
    os.makedirs(ffmpeg_dest_dir, exist_ok=True)
    shutil.copy2(ffmpeg_src, os.path.join(ffmpeg_dest_dir, "ffmpeg" + exe_suffix))

    bgutil_src = os.path.join(ROOT, "vendor", "bgutil-server")
    if not os.path.isdir(os.path.join(bgutil_src, "build")):
        print(
            "HIBA: vendor/bgutil-server nincs megépítve. "
            "Futtasd előbb: scripts/setup_pot_server.sh (vagy .ps1 Windows-on).",
            file=sys.stderr,
        )
        sys.exit(1)
    bgutil_dest = os.path.join(staging_dir, "vendor", "bgutil-server")
    shutil.copytree(bgutil_src, bgutil_dest)

    return node_dest_dir, ffmpeg_dest_dir, bgutil_dest


def add_data_arg(src, dest_in_bundle):
    sep = ";" if sys.platform.startswith("win") else ":"
    return f"--add-data={src}{sep}{dest_in_bundle}"


def main():
    staging_dir = os.path.join(ROOT, "build_staging")
    if os.path.isdir(staging_dir):
        shutil.rmtree(staging_dir)
    os.makedirs(staging_dir)

    plat = platform_dir_name()
    node_dir, ffmpeg_dir, bgutil_dir = stage_vendor_binaries(staging_dir)

    args = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        f"--name={APP_NAME}",
        add_data_arg(os.path.join(ROOT, "templates"), "templates"),
        add_data_arg(os.path.join(ROOT, "static"), "static"),
        add_data_arg(node_dir, os.path.join("vendor", "node", plat)),
        add_data_arg(ffmpeg_dir, os.path.join("vendor", "ffmpeg", plat)),
        add_data_arg(bgutil_dir, os.path.join("vendor", "bgutil-server")),
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
