"""Point d'entrée principal du backend Traffic Togo avec FastAPI."""

from __future__ import annotations

from fastapi import FastAPI
import uvicorn

from app.core.config import ConfigurationApplication
from app.intersection.controller import router as intersection_router


def charger_configuration(
    configuration: ConfigurationApplication | None = None,
) -> ConfigurationApplication:
    """Charge et valide la configuration technique globale de l'application."""
    config_active = (
        configuration if configuration is not None else ConfigurationApplication()
    )
    config_active.valider()
    return config_active


def creer_application() -> FastAPI:
    """Initialise et configure l'application FastAPI."""
    configuration = charger_configuration()
    application = FastAPI(
        title=configuration.nom_application,
        version="1.0.0",
        description="Système intelligent de gestion et de régulation du trafic routier — Togo",
    )
    application.include_router(intersection_router)
    return application


app = creer_application()


def main() -> None:
    """Exécution directe du serveur backend."""
    configuration = charger_configuration()
    print(
        f"[OK] {configuration.nom_application} démarré "
        f"(env={configuration.environnement.value})"
    )
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=configuration.mode_debug)


if __name__ == "__main__":
    main()
