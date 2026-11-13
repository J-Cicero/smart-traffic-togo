"""Configuration technique globale de l'application backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import os


class ErreurConfiguration(Exception):
    """Levée lorsque la configuration technique de l'application est invalide."""


class Environnement(str, Enum):
    """Environnements techniques d'exécution."""

    DEVELOPPEMENT = "developpement"
    TEST = "test"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class ConfigurationApplication:
    """
    Paramètres techniques globaux de l'application.
    Ne contient aucun paramètre métier de régulation.
    """

    nom_application: str = "Traffic Togo Backend"
    environnement: Environnement = Environnement.DEVELOPPEMENT
    mode_debug: bool = False
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://postgres:postgres@localhost:5432/traffic_togo",
        )
    )

    def valider(self) -> None:
        """Vérifie la validité des paramètres techniques globaux."""
        if not self.nom_application.strip():
            raise ErreurConfiguration(
                "Le paramètre technique 'nom_application' ne peut pas être vide."
            )
        if not self.database_url.strip():
            raise ErreurConfiguration(
                "Le paramètre technique 'database_url' ne peut pas être vide."
            )
