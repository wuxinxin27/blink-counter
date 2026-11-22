"""Zero-dependency local HTTP server for launching the Browser Web App (`--web`)."""

from __future__ import annotations

import functools
import http.server
import socketserver
import webbrowser
from pathlib import Path
from typing import Optional

from .i18n import Translator


def locate_web_dir() -> Path:
    """Locate the bundled `web/` directory in source checkouts or installed packages."""
    package_dir = Path(__file__).resolve().parent
    candidates = [
        package_dir.parent / "web",
        package_dir / "web",
    ]
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    raise FileNotFoundError(
        "Could not locate the `web/` frontend directory (index.html not found)."
    )


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


class _ReusableTCPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def create_web_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    web_dir: Optional[Path] = None,
) -> http.server.HTTPServer:
    """Create a threaded HTTP server serving the static browser app."""
    directory = web_dir or locate_web_dir()
    handler = functools.partial(_QuietHandler, directory=str(directory))
    return _ReusableTCPServer((host, port), handler)


def serve_web_app(
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    web_dir: Optional[Path] = None,
    lang: str = "auto",
) -> int:
    """Serve the browser-based Blink Counter locally until interrupted."""
    tr = Translator(lang)
    server = create_web_server(host=host, port=port, web_dir=web_dir)
    actual_port = server.server_address[1]
    query = f"?lang={tr.lang}" if lang != "auto" else ""
    url = f"http://{host}:{actual_port}/{query}"
    print(tr.t("web_running", url=url))
    print(tr.t("web_privacy"))
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n" + tr.t("web_stopped"))
    finally:
        server.server_close()
    return 0
