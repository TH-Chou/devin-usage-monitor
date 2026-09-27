"""Local web dashboard for Devin token usage.

Serves a self-contained HTML dashboard plus a JSON API.  Uses only the
standard library — the HTTP handler reads :meth:`UsageAggregator.snapshot`
while whoever owns the aggregator drives polling.

Run standalone:  .venv/bin/python -m devin_token_monitor.web
Embedded: the menu bar app starts this on a daemon thread.
"""

from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from urllib.parse import parse_qs, urlparse

from . import __version__
from .aggregator import UsageAggregator
from .dashboard import PAGE
from .db import db_path
from .exporter import export_csv
from .pricing import PriceTable, default_prices_path

HOST = os.environ.get("DTM_HOST", "127.0.0.1")
PORT = int(os.environ.get("DTM_PORT", "7878"))

class _Handler(BaseHTTPRequestHandler):
    server_version = f"DevinTokenMonitor/{__version__}"

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 - stdlib naming
        agg: UsageAggregator = self.server.agg  # type: ignore[attr-defined]
        url = urlparse(self.path)
        path = url.path
        if path in ("/", "/index.html"):
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif path == "/api/usage":
            self._send(
                200,
                json.dumps(agg.snapshot()).encode(),
                "application/json",
            )
        elif path == "/api/refresh":
            try:
                agg.prices = PriceTable.load()
                agg.meta["prices_path"] = str(default_prices_path())
                agg.poll()
            except Exception as e:
                self._send(
                    500, json.dumps({"error": str(e)}).encode(),
                    "application/json",
                )
                return
            self._send(
                200,
                json.dumps(agg.snapshot()).encode(),
                "application/json",
            )
        elif path == "/api/export.csv":
            what = parse_qs(url.query).get("what", ["requests"])[0]
            try:
                csv_text = export_csv(agg.snapshot(), what)
            except ValueError as e:
                self._send(400, str(e).encode(), "text/plain")
                return
            body = csv_text.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="devin-usage-{what}.csv"',
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/body":
            qs = parse_qs(url.query)
            body = agg.request_body(
                qs.get("rid", [""])[0], qs.get("mid", [""])[0]
            )
            self._send(
                200,
                json.dumps({"body": body}, ensure_ascii=False).encode(),
                "application/json",
            )
        elif path == "/api/health":
            summary = agg.status_summary()
            poll_error = summary["meta"].get("poll_error")
            last_success = summary["meta"].get("poll_last_ok")
            healthy = bool(last_success) and not poll_error
            self._send(
                200 if healthy else 503,
                json.dumps({
                    "ok": healthy,
                    "last_success": last_success,
                    "error": poll_error,
                }).encode(),
                "application/json",
            )
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):  # noqa: N802 - stdlib naming
        agg: UsageAggregator = self.server.agg  # type: ignore[attr-defined]
        url = urlparse(self.path)
        if url.path == "/api/settings":
            try:
                n = int(self.headers.get("Content-Length", 0))
                if not 0 <= n <= 65536:
                    raise ValueError("Invalid settings request size")
                body = json.loads(self.rfile.read(n) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("Settings request must be a JSON object")
                patch = {}
                if "daily_budget" in body:
                    patch["daily_budget"] = body["daily_budget"]
                if "language" in body:
                    patch["language"] = body["language"]
                if "theme" in body:
                    patch["theme"] = body["theme"]
                path = agg.prices.update_settings(patch)
                agg.prices = PriceTable.load()
                agg.meta["prices_path"] = str(path)
            except ValueError as e:
                self._send(400, json.dumps({"error": str(e)}).encode(), "application/json")
                return
            except OSError as e:
                self._send(500, json.dumps({"error": str(e)}).encode(), "application/json")
                return
            self._send(200, json.dumps(agg.snapshot()).encode(), "application/json")
        else:
            self._send(404, b"not found", "text/plain")

    def log_message(self, *args):  # quiet
        pass


def start_server(agg: UsageAggregator, host: str = HOST, port: int = PORT) -> tuple[ThreadingHTTPServer, str]:
    """Start the dashboard on a daemon thread. Returns (server, url)."""
    srv = ThreadingHTTPServer((host, port), _Handler)
    srv.agg = agg  # type: ignore[attr-defined]
    t = threading.Thread(target=srv.serve_forever, name="dtm-web", daemon=True)
    t.start()
    return srv, f"http://{host}:{srv.server_address[1]}"


def main() -> int:
    agg = UsageAggregator(PriceTable.load())
    agg.meta = {
        "db_path": str(db_path()),
        "prices_path": str(default_prices_path()),
        "version": __version__,
        "login_item": None,
    }
    try:
        agg.poll()
    except FileNotFoundError as e:
        print(f"error: {e}")
        return 1

    def poll_loop():
        last_error = None
        while True:
            time.sleep(15)
            try:
                agg.poll()
                last_error = None
            except Exception as e:
                message = str(e)
                if message != last_error:
                    print(f"poll error: {message}")
                last_error = message

    threading.Thread(target=poll_loop, name="dtm-poll", daemon=True).start()
    srv, url = start_server(agg)
    print(f"Devin Token Monitor dashboard: {url}")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        srv.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
