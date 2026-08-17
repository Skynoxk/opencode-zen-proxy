#!/usr/bin/env python3
"""OpenCode-mimicking streaming reverse proxy for the OpenCode Zen free tier.

Forwards requests to https://opencode.ai/zen/v1 while injecting the same
x-opencode-* identity headers the real OpenCode CLI sends, so the zen API
attributes traffic to a real client instead of an anonymous IP (which gets
throttled). Streams SSE responses chunk-by-chunk. Self-contained.
"""

import http.client
import random
import string
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 1787
UPSTREAM_HOST = "opencode.ai"
UPSTREAM_PORT = 443
UPSTREAM_BASE = "/zen/v1"
CHUNK = 8192

DROP_HEADERS = {
    "host", "content-length", "connection", "authorization",
    "proxy-authenticate", "proxy-authorization", "proxy-connection",
    "keep-alive", "te", "trailer", "upgrade",
    "transfer-encoding", "date",
}

# Stable fake identity so every request looks like the same real opencode client.
CLIENT_ID = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))


def _rand(n=10):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def mimic_headers():
    return {
        "User-Agent": "opencode-1.18.15",
        "x-opencode-client": "opencode",
        "x-opencode-directory": "/tmp",
        "x-opencode-session": f"{CLIENT_ID}-{_rand(8)}",
        "x-opencode-request": _rand(10),
    }


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _proxy(self):
        upstream = None
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(length) if length else None

            headers = {
                k: v for k, v in self.headers.items() if k.lower() not in DROP_HEADERS
            }
            headers.update(mimic_headers())

            path = self.path
            if path == "/v1" or path.startswith("/v1/"):
                path = path[3:] or "/"

            upstream = http.client.HTTPSConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=180)
            upstream.request(self.command, UPSTREAM_BASE + path, body=body, headers=headers)
            resp = upstream.getresponse()

            content_type = (resp.getheader("Content-Type") or "").lower()
            enc = (resp.getheader("Transfer-Encoding") or "").lower()
            is_stream = enc == "chunked" or content_type.startswith("text/event-stream")

            self.send_response(resp.status, resp.reason)
            seen = set()
            for k, v in resp.getheaders():
                kl = k.lower()
                if kl in DROP_HEADERS or kl in seen:
                    continue
                seen.add(kl)
                self.send_header(k, v)

            if is_stream:
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                while True:
                    chunk = resp.read(CHUNK)
                    if not chunk:
                        break
                    self.wfile.write(("%x\r\n" % len(chunk)).encode("ascii"))
                    self.wfile.write(chunk)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            else:
                payload = resp.read()
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                self.wfile.flush()
        except Exception as exc:
            try:
                msg = f"opencode-zen-proxy upstream error: {exc}".encode("utf-8", "replace")
                self.send_response(502)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(msg)))
                self.end_headers()
                self.wfile.write(msg)
            except Exception:
                pass
        finally:
            if upstream is not None:
                try:
                    upstream.close()
                except Exception:
                    pass

    do_GET = _proxy
    do_POST = _proxy
    do_PUT = _proxy
    do_DELETE = _proxy
    do_OPTIONS = _proxy
    do_PATCH = _proxy

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print(
        f"opencode-zen-proxy listening on http://{LISTEN_HOST}:{LISTEN_PORT}/v1 "
        f"-> https://{UPSTREAM_HOST}{UPSTREAM_BASE} (streaming enabled)"
    )
    ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Proxy).serve_forever()
