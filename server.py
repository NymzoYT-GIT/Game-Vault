from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import json
import uuid
import time
import threading


sessions = {}
sessions_lock = threading.Lock()


class GameVaultHandler(BaseHTTPRequestHandler):

    def send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, DELETE, OPTIONS"
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, DELETE, OPTIONS"
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/status":
            with sessions_lock:
                active_sessions = sum(
                    1 for session in sessions.values()
                    if session["status"] == "starting"
                )

            self.send_json(200, {
                "service": "Game Vault",
                "status": "online",
                "streaming": False,
                "active_sessions": active_sessions,
                "message": (
                    "Session management is available. "
                    "Game streaming is not connected yet."
                )
            })
            return

        if path.startswith("/api/sessions/"):
            session_id = path.split("/")[-1]

            with sessions_lock:
                session = sessions.get(session_id)

                if session is not None:
                    session = dict(session)

            if session is None:
                self.send_json(404, {
                    "error": "Session not found"
                })
                return

            self.send_json(200, session)
            return

        self.send_json(404, {
            "error": "Not found",
            "path": path
        })

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/api/sessions":
            self.send_json(404, {
                "error": "Not found",
                "path": path
            })
            return

        session_id = str(uuid.uuid4())

        session = {
            "id": session_id,
            "status": "starting",
            "created_at": int(time.time()),
            "streaming": False,
            "message": (
                "Session created. Waiting for a streaming worker."
            )
        }

        with sessions_lock:
            sessions[session_id] = session

        self.send_json(201, session)

    def do_DELETE(self):
        path = urlparse(self.path).path

        if not path.startswith("/api/sessions/"):
            self.send_json(404, {
                "error": "Not found",
                "path": path
            })
            return

        session_id = path.split("/")[-1]

        with sessions_lock:
            session = sessions.pop(session_id, None)

        if session is None:
            self.send_json(404, {
                "error": "Session not found"
            })
            return

        self.send_json(200, {
            "id": session_id,
            "status": "stopped",
            "message": "Session ended."
        })

    def log_message(self, format, *args):
        print("%s - %s" % (
            self.address_string(),
            format % args
        ))


if __name__ == "__main__":
    server = ThreadingHTTPServer(
        ("0.0.0.0", 8001),
        GameVaultHandler
    )

    print("Game Vault backend listening on port 8001")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nGame Vault backend stopped.")
    finally:
        server.server_close()