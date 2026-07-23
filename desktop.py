import threading

import webview

import pot_server
from app import app, bootstrap

HOST = "127.0.0.1"
PORT = 5000


def _run_flask():
    app.run(host=HOST, port=PORT, threaded=True, debug=False, use_reloader=False)


def main():
    bootstrap()

    flask_thread = threading.Thread(target=_run_flask, daemon=True)
    flask_thread.start()

    window = webview.create_window(
        "YT Grabber",
        f"http://{HOST}:{PORT}",
        width=980,
        height=760,
        min_size=(560, 640),
        background_color="#0b0c10",
    )
    webview.start()

    pot_server.stop()


if __name__ == "__main__":
    main()
