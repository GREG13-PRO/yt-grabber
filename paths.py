import os
import sys


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def app_root():
    """Directory containing bundled resources (templates/, static/, vendor/)."""
    if is_frozen():
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(*parts):
    return os.path.join(app_root(), *parts)


def user_data_dir():
    """Writable directory for downloads. A packaged app's own folder may be
    read-only (e.g. inside /Applications), so downloads go under the user's
    home directory instead. In dev mode we keep using the project folder."""
    if is_frozen():
        return os.path.join(os.path.expanduser("~"), "Downloads", "YT Grabber")
    return os.path.dirname(os.path.abspath(__file__))


def platform_dir_name():
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    return "linux"


def bundled_binary(vendor_subdir, binary_name):
    """Path to a vendored binary (node, ffmpeg) for the current platform,
    or None if it isn't bundled (e.g. running from source in dev mode)."""
    exe = binary_name + (".exe" if sys.platform.startswith("win") else "")
    path = resource_path("vendor", vendor_subdir, platform_dir_name(), exe)
    return path if os.path.isfile(path) else None
