#!/usr/bin/env python3
"""
Simple HTTP server to serve the UI files.
"""

import http.server
import socketserver
import os
import webbrowser
import sys

DEFAULT_PORT = 3000


def find_free_port(start: int, attempts: int = 10) -> int:
    import socket
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    raise OSError(f"No free port found in range {start}–{start + attempts - 1}")


os.chdir(os.path.dirname(os.path.abspath(__file__)))

Handler = http.server.SimpleHTTPRequestHandler

try:
    PORT = find_free_port(DEFAULT_PORT)
except OSError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

print(f"Serving UI at http://localhost:{PORT}/frontend/index.html")
print("Press Ctrl+C to stop")

webbrowser.open(f"http://localhost:{PORT}/frontend/index.html")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()
