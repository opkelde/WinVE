"""
Prototype Implementation: Web Administration Dashboard Server
Stored in roadmap-temp/ for reference and future integration.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winve_web_admin")

class WebAdminHandler(BaseHTTPRequestHandler):
    """Handles REST requests and serves diagnostic stats for the local administration page."""
    
    # Store reference to main application state class-wide
    app_reference = None
    
    def log_message(self, format, *args):
        # Override to prevent spamming main console logs
        pass

    def do_GET(self):
        """Serve diagnostic HTML page or REST stats."""
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self._get_dashboard_html().encode("utf-8"))
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self._get_stats_json()).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def _get_stats_json(self) -> dict:
        """Collect diagnostic properties from the running WinVE instance."""
        # Simple fallback stats
        stats = {
            "app_name": "WinVE Desktop Voice Assistant",
            "version": "3.0.0",
            "status": "Healthy",
            "uptime_sec": int(threading.active_count()),
            "mic_active": True,
            "websocket_connected": False,
            "wake_word_running": True
        }
        
        # Pull live details if application reference is bound
        app = WebAdminHandler.app_reference
        if app:
            stats["websocket_connected"] = getattr(app.client, "is_connected", False) if hasattr(app, "client") else False
            stats["wake_word_running"] = getattr(app.wake_word_detector, "is_running", False) if hasattr(app, "wake_word_detector") else False
            
        return stats

    def _get_dashboard_html(self) -> str:
        """Returns the dashboard diagnostic web page markup."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>WinVE Admin Dashboard</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #121212; color: #e0e0e0; margin: 30px; }
                h1 { color: #00bcd4; }
                .card { background: #1e1e1e; padding: 20px; border-radius: 8px; border: 1px solid #333; max-width: 500px; }
                .status-val { font-weight: bold; color: #4caf50; }
                button { background: #00bcd4; border: none; color: white; padding: 10px 15px; border-radius: 4px; cursor: pointer; }
                button:hover { background: #00acc1; }
            </style>
            <script>
                async function refreshStats() {
                    const res = await fetch('/api/status');
                    const data = await res.json();
                    document.getElementById('ws-status').innerText = data.websocket_connected ? 'Connected' : 'Disconnected';
                    document.getElementById('ww-status').innerText = data.wake_word_running ? 'Active' : 'Paused';
                }
                setInterval(refreshStats, 3000);
            </script>
        </head>
        <body onload="refreshStats()">
            <h1>WinVE Admin Dashboard</h1>
            <div class="card">
                <h3>System Telemetry</h3>
                <p>HA Connection: <span id="ws-status" class="status-val">Checking...</span></p>
                <p>Wake Word Engine: <span id="ww-status" class="status-val">Checking...</span></p>
                <button onclick="refreshStats()">Manual Refresh</button>
            </div>
        </body>
        </html>
        """

class WebAdminServer:
    """WebServer hosting the local administration page."""
    
    def __init__(self, port: int = 18880, main_app=None):
        self.port = port
        self.server = None
        self.thread = None
        WebAdminHandler.app_reference = main_app

    def start(self):
        """Start local HTTP server in a daemon thread."""
        try:
            self.server = HTTPServer(("localhost", self.port), WebAdminHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            logger.info(f"Web Admin Dashboard hosted locally at http://localhost:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start local admin webserver: {e}")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("Web Admin Server stopped.")
stream = None
