#!/usr/bin/env python3
"""Minimal OTLP/HTTP dump server for smoke-testing devin-cli telemetry."""
import http.server, pathlib, time, sys

OUT = pathlib.Path("/tmp/otlp_dump")
OUT.mkdir(exist_ok=True)

class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n)
        ts = time.strftime("%H%M%S")
        p = OUT / f"{ts}_{self.path.strip('/').replace('/','_')}_{n}b.bin"
        p.write_bytes(body)
        print(f"[{ts}] POST {self.path} {n}B ct={self.headers.get('Content-Type')} -> {p.name}", flush=True)
        self.send_response(200)
        self.send_header("Content-Type", "application/x-protobuf")
        self.end_headers()
        self.wfile.write(b"\x00\x00")  # empty ExportXxxServiceResponse-ish
    def log_message(self, *a): pass

http.server.HTTPServer(("127.0.0.1", 4318), H).serve_forever()
