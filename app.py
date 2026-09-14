"""BlueTune 0.1 preview: standard-library web app, loopback only."""
import argparse
import json
import os
import re
import secrets
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from analysis import parse_stats, assess
from collector import Collector

ROOT = Path(__file__).resolve().parent


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, status, data, kind="application/json"):
        body = json.dumps(data, allow_nan=False).encode() if kind == "application/json" else data
        self.send_response(status)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def trusted(self):
        host = self.headers.get("Host", "")
        match = re.fullmatch(r"(127\.0\.0\.1|localhost):(\d{1,5})", host)
        if not match or not 1 <= int(match[2]) <= 65535:
            self.send(403, {"error": "Open BlueTune through its localhost address."})
            return False
        origin = self.headers.get("Origin")
        if origin and origin != "http://" + host:
            self.send(403, {"error": "This request came from another website."})
            return False
        return True

    def do_GET(self):
        if not self.trusted():
            return
        files = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}
        if self.path in files:
            name, kind = files[self.path]
            return self.send(200, (ROOT / "web" / name).read_bytes(), kind)
        if self.path == "/api/status":
            return self.send(200, dict(mode="live" if self.server.collector else "demo", device=self.server.device,
                                      token=self.server.token, version="0.1.1-preview"))
        self.send(404, {"error": "Page not found."})

    def do_POST(self):
        if not self.trusted():
            return
        if self.headers.get("X-BlueTune-Token") != self.server.token:
            return self.send(403, {"error": "Reload BlueTune before trying again."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 70000:
                return self.send(413, {"error": "This sample is too large."})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Expected a sample object.")
            if self.path == "/api/analyze":
                samples = parse_stats(data.get("text"))
                return self.send(200, dict(samples=samples, result=assess(samples, data.get("speech_confirmed") is True)))
            if self.path == "/api/sample":
                if not self.server.collector:
                    return self.send(409, {"error": "Live collection is unavailable in demo mode."})
                sample = self.server.collector.sample()
                return self.send(200, dict(sample=sample, collected_at=time.time(), device=self.server.device))
            if self.path == "/api/settings":
                if not self.server.collector:
                    return self.send(409, {"error": "Connect to ASL3 to export current settings."})
                return self.send(200, dict(device=self.server.device, settings=self.server.collector.settings(),
                                          note="Read-only settings snapshot, not a restorable configuration backup."))
            self.send(404, {"error": "Action not found."})
        except (ValueError, UnicodeError) as exc:
            self.send(400, {"error": str(exc)})


def make_server(port=8091, collector=None):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.collector = collector
    server.device = collector.device if collector else None
    server.token = secrets.token_urlsafe(32)
    return server


def serve(port=8091, collector=None):
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise ValueError("Start BlueTune as your normal login account, without sudo.")
    server = make_server(port, collector)
    print(f"BlueTune {'LIVE / SimpleUSB ' + collector.device if collector else 'DEMO'} - http://127.0.0.1:{server.server_port}", flush=True)
    print("Keep this terminal open. Press Ctrl+C to stop BlueTune.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BlueTune receive-audio checkup")
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--live", action="store_true", help="Enable read-only SimpleUSB measurements")
    parser.add_argument("--device", help="Expected active SimpleUSB device name")
    parser.add_argument("--sudo", action="store_true", help="Use existing noninteractive sudo permission for the fixed read-only commands")
    args = parser.parse_args()
    try:
        collector = Collector(device=args.device, use_sudo=args.sudo) if args.live else None
        if collector:
            collector.sample()
        serve(args.port, collector)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
