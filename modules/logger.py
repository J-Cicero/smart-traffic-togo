# modules/logger.py - Persistance et journalisation des evenements du carrefour

import json
import os
import time
from config import SERVER_CONFIG


class TrafficLogger:
    """
    Gestionnaire de logs d'evenements au format JSON Lines (JSONL)
    pour la tracabilite et l'audit du carrefour.
    """

    def __init__(self, log_filepath: str | None = None):
        self.filepath = log_filepath or SERVER_CONFIG.get("LOG_FILE", "traffic_events.jsonl")

    def log_event(self, event_type: str, data: dict) -> None:
        """
        Enregistre un evenement horodate dans le fichier log.
        """
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "epoch": time.time(),
            "event_type": event_type,
            "data": data,
        }

        try:
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            print(f"[WARN LOGGER] Impossible d'ecrire dans les logs: {exc}")

    def get_recent_events(self, limit: int = 20) -> list[dict]:
        """
        Lit les N derniers evenements enregistres.
        """
        if not os.path.exists(self.filepath):
            return []

        events = []
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    if line.strip():
                        events.append(json.loads(line.strip()))
        except Exception:
            pass

        return events
