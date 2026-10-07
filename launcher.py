"""Entry point for the packaged app (pdf-tools.exe): double-click and go.

Serves the same Flask app as `python app.py` with waitress, on this machine
only, and opens it in the default browser. Closing the console window stops it.
If the port is taken, any free one is used instead.

Build it with `pyinstaller pdf-tools.spec`; see "Windows app" in the README.
"""

from __future__ import annotations

import argparse
import socket
import sys
import traceback
import webbrowser

from waitress.server import create_server

import config
from app import app


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="pdf-tools: upload files, get one compressed PDF")
    parser.add_argument("--port", "-p", type=int, default=config.PORT,
                        help=f"port to listen on (default {config.PORT}, or any free one)")
    parser.add_argument("--host", default=config.HOST,
                        help=f"address to bind (default {config.HOST}; 0.0.0.0 for the network)")
    parser.add_argument("--no-browser", action="store_true",
                        help="don't open the page in a browser")
    return parser.parse_args(argv)


def port_free(host: str, port: int) -> bool:
    """Can we listen here? Asked up front because waitress sets SO_REUSEADDR,
    which on Windows lets a second server bind a port that is already taken -
    opening the exe twice would quietly leave two servers sharing one port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):  # Windows
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:  # elsewhere this still refuses a live listener
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def serve(options: argparse.Namespace) -> None:
    # Port in use: let the OS pick one rather than refuse to start.
    port = options.port if port_free(options.host, options.port) else 0
    server = create_server(app, host=options.host, port=port)

    shown = "127.0.0.1" if options.host in ("0.0.0.0", "") else options.host
    url = f"http://{shown}:{server.effective_port}/"
    print(f"pdf-tools is running at {url}", flush=True)
    print("Close this window (or press Ctrl+C) to stop it.", flush=True)
    if not options.no_browser:
        webbrowser.open(url)
    try:
        server.run()
    except KeyboardInterrupt:
        pass


def main() -> None:
    options = parse_args()
    try:
        serve(options)
    except Exception:  # noqa: BLE001 - show the reason before the window vanishes
        traceback.print_exc()
        if getattr(sys, "frozen", False):
            input("\npdf-tools could not start. Press Enter to close.")
        sys.exit(1)


if __name__ == "__main__":
    main()
