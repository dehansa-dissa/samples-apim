#!/usr/bin/env python3
"""
Sample backend that validates a custom Authorization token.

Mimics the JAX-RS backend from the WSO2 APIM "Passing a Custom Authorization
Token to the Backend" tutorial: it accepts requests only when the
Authorization header is exactly "Bearer 1234" and replies "Request Received".

It also echoes back all received headers in the JSON response so you can see
exactly what the gateway forwarded — useful for verifying that:
  - the original Authorization (application access token) was dropped
  - the Custom header value was moved into Authorization
  - the Custom header itself was removed

Usage:
    python3 server.py [port]      # default port 8080
"""

import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EXPECTED_TOKEN = "Bearer 1234"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080


class AuthValidationHandler(BaseHTTPRequestHandler):

    def _respond(self, status, body):
        payload = json.dumps(body, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle(self):
        auth = self.headers.get("Authorization")
        custom = self.headers.get("Custom")
        received_headers = dict(self.headers.items())

        print(f"\n--- {datetime.now().isoformat()} {self.command} {self.path}")
        for k, v in received_headers.items():
            print(f"    {k}: {v}")

        if auth == EXPECTED_TOKEN:
            self._respond(200, {
                "message": "Request Received.",
                "status": "authorized",
                "note": "Authorization header matched the expected custom token.",
                "received_headers": received_headers,
            })
        elif auth is None:
            self._respond(401, {
                "message": "Unauthorized",
                "status": "missing_token",
                "note": "No Authorization header reached the backend. "
                        "The gateway may have dropped it without applying the "
                        "TokenExchange policy.",
                "received_headers": received_headers,
            })
        else:
            self._respond(401, {
                "message": "Unauthorized",
                "status": "invalid_token",
                "note": f"Expected '{EXPECTED_TOKEN}' but got '{auth}'. "
                        "If this is the application access token, the "
                        "Custom->Authorization swap did not happen.",
                "custom_header_seen": custom,
                "received_headers": received_headers,
            })

    # Accept every method/path so any API resource mapping works
    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _handle


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), AuthValidationHandler)
    print(f"Custom auth validation backend listening on http://0.0.0.0:{PORT}")
    print(f"Expecting header ->  Authorization: {EXPECTED_TOKEN}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
