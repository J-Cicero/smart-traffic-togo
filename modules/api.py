# modules/api.py - Serveur API REST embarque pour la supervision et le controle a distance

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import time
from config import PCU_WEIGHTS, SERVER_CONFIG, TIME_LIMITS


class IntersectionStateStore:
    """
    Entrepot de donnees thread-safe de l'etat courant du carrefour.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.active_axis = "Axe Nord-Sud"
        self.phase = "VERT"
        self.remaining_seconds = 0
        self.observed_counts = {}
        self.lane_camera_ok = {}
        self.last_cycle_metadata = {}
        self.manual_override = None

    def update_state(self, **kwargs):
        with self._lock:
            for key, val in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, val)

    def get_state_snapshot(self) -> dict:
        with self._lock:
            return {
                "active_axis": self.active_axis,
                "phase": self.phase,
                "remaining_seconds": self.remaining_seconds,
                "observed_counts": self.observed_counts,
                "lane_camera_ok": self.lane_camera_ok,
                "last_cycle_metadata": self.last_cycle_metadata,
                "manual_override": self.manual_override,
                "timestamp": time.time(),
            }

    def set_override(self, override_command: dict | None):
        with self._lock:
            self.manual_override = override_command

    def pop_override(self) -> dict | None:
        with self._lock:
            override = self.manual_override
            self.manual_override = None
            return override



GLOBAL_STATE = IntersectionStateStore()


class APIRequestHandler(BaseHTTPRequestHandler):
    """
    Handler HTTP REST pour la consultation et la commande du carrefour.
    """

    def _send_json(self, data: dict, status_code: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/api/status":
            self._send_json(GLOBAL_STATE.get_state_snapshot())
        elif path == "/api/config":
            self._send_json({
                "time_limits": TIME_LIMITS,
                "pcu_weights": PCU_WEIGHTS,
            })
        elif path == "/":
            self._send_json({
                "service": "Smart Traffic Lome Backend API",
                "endpoints": ["/api/status", "/api/config", "/api/override"],
            })
        else:
            self._send_json({"error": "Route introuvable"}, status_code=404)

    def do_POST(self):
        if self.path == "/api/override":
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            try:
                payload = json.loads(body_bytes.decode("utf-8"))
                GLOBAL_STATE.set_override(payload)
                self._send_json({"status": "ok", "message": "Commande de debrayage enregistree", "payload": payload})
            except Exception as e:
                self._send_json({"error": f"Payload invalide: {e}"}, status_code=400)
        else:
            self._send_json({"error": "Route introuvable"}, status_code=404)

    def log_message(self, format, *args):
        # Silencer les logs serveur HTTP par defaut dans la console pour eviter la pollution de terminal
        pass


def start_api_server_background(host: str = "0.0.0.0", port: int = 8080) -> HTTPServer | None:
    """
    Lance le serveur HTTP API en arriere-plan dans un thread dedie.
    """
    try:
        server = HTTPServer((host, port), APIRequestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(f"[INFO API] Serveur HTTP REST demarre sur http://{host}:{port}")
        return server
    except Exception as exc:
        print(f"[WARN API] Impossible de demarrer le serveur API sur le port {port}: {exc}")
        return None
