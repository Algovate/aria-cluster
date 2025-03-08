#!/usr/bin/env python3
"""
Simple HTTP server for testing the Aria2c Cluster Manager Web UI locally.
"""
import http.server
import socketserver
import os
import webbrowser
from urllib.parse import urlparse

# Configuration
PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler with CORS support."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'X-API-Key, Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.end_headers()


def run_server():
    """Run the HTTP server and open a browser."""
    with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"Serving at: {url}")
        print("Press Ctrl+C to stop the server")

        # Open browser
        webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    run_server()