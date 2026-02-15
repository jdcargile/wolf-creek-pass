#!/usr/bin/env python3
"""
Local dev server for the Reolink API Lambda handler.

Wraps handler.handler() in a minimal HTTP server so the Vue frontend
can fetch cabin camera data during development.

Usage:
    python reolink_api/serve_local.py          # default port 8787
    python reolink_api/serve_local.py 9000     # custom port

Then set VITE_REOLINK_API_URL=http://localhost:8787 in frontend/.env
"""

from __future__ import annotations

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from handler import handler

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8787


class ReolinkHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        # Build a Lambda Function URL event
        event = {
            "requestContext": {"http": {"method": "GET"}},
            "queryStringParameters": {k: v[0] for k, v in qs.items()},
        }

        result = handler(event, None)

        self.send_response(result.get("statusCode", 200))
        for key, val in result.get("headers", {}).items():
            self.send_header(key, val)
        self.end_headers()
        self.wfile.write(result.get("body", "").encode())

    def do_OPTIONS(self) -> None:
        event = {"requestContext": {"http": {"method": "OPTIONS"}}}
        result = handler(event, None)

        self.send_response(result.get("statusCode", 204))
        for key, val in result.get("headers", {}).items():
            self.send_header(key, val)
        self.end_headers()


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), ReolinkHandler)
    print(f"Reolink API listening on http://localhost:{PORT}")
    print(f"  Example: http://localhost:{PORT}/?date=2026-02-15")
    print("  Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
