from __future__ import annotations

from typing import Any, Dict
from fastapi import FastAPI

from app.core.config import Settings, charger_configuration


def creer_application(settings: Settings | None = None) -> FastAPI:
    """Crée et configure l'instance de l'application FastAPI."""
    cfg = settings if settings is not None else charger_configuration()
    application = FastAPI(title=cfg.nom_application)

    @application.get("/health")
    def health() -> Dict[str, Any]:
        return {
            "status": "ok",
            "application": cfg.nom_application,
        }

    return application


app = creer_application()
