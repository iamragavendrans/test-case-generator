#!/usr/bin/env python3
"""
Simple HTTP server to serve the UI files.
"""

import http.server
import socketserver
import os
import webbrowser

PORT = 3000

os.chdir(os.path.dirname(os.path.abspath(__file__)))

Handler = http.server.SimpleHTTPRequestHandler

print(f"Serving UI at http://localhost:{PORT}")
print("Press Ctrl+C to stop")

# Open browser automatically
webbrowser.open(f"http://localhost:{PORT}/frontend/index.html")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()
