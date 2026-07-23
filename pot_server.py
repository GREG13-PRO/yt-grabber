import shutil
import subprocess
import time
import urllib.error
import urllib.request

from paths import bundled_binary, is_frozen, resource_path

POT_SERVER_URL = "http://127.0.0.1:4416"

_process = None


def _dev_server_script():
    path = resource_path("vendor", "bgutil-server", "build", "main.js")
    import os

    return path if os.path.isfile(path) else None


def _resolve_node_and_script():
    """Returns (node_path, script_path) or (None, None) if unavailable."""
    if is_frozen():
        node = bundled_binary("node", "node")
        import os

        script = resource_path("vendor", "bgutil-server", "build", "main.js")
        script = script if os.path.isfile(script) else None
        return node, script

    node = shutil.which("node")
    script = _dev_server_script()
    return node, script


def _is_up():
    try:
        with urllib.request.urlopen(f"{POT_SERVER_URL}/ping", timeout=1) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def start(timeout=10):
    """Start the bundled bgutil PO-token server so yt-dlp can fetch
    higher-quality formats that YouTube gates behind a PO token. If Node
    or the server script isn't available, the app still works, just capped
    to whatever quality YouTube allows without a token."""
    global _process

    if _is_up():
        return True

    node_path, script_path = _resolve_node_and_script()
    if not node_path or not script_path:
        print("INFO: PO-token szerver nem elérhető (node vagy a szerver szkript hiányzik). "
              "A letöltés működik, de a minőség YouTube-oldali korlátozás alá eshet. "
              "Lásd README 'Legjobb minőség' szakaszát.")
        return False

    try:
        _process = subprocess.Popen(
            [node_path, script_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as e:
        print(f"FIGYELEM: nem sikerült elindítani a PO-token szervert: {e}")
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_up():
            print("PO-token szerver elindult (jobb minőségű letöltés elérhető).")
            return True
        time.sleep(0.3)

    print("FIGYELEM: a PO-token szerver nem válaszolt időben, folytatás nélküle.")
    return False


def stop():
    global _process
    if _process is not None:
        _process.terminate()
        try:
            _process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _process.kill()
        _process = None
