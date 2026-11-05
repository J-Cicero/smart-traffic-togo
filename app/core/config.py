"""Configuration technique globale de l'application backend."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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
    Ne contient aucun paramètre métier de régulation (qui appartiendra au domaine regulation).
    """

    nom_application: str = "Traffic Togo Backend"
    environnement: Environnement = Environnement.DEVELOPPEMENT
    mode_debug: bool = False

    def valider(self) -> None:
        """Vérifie la validité des paramètres techniques globaux."""
        if not self.nom_application.strip():
            raise ErreurConfiguration(
                "Le paramètre technique 'nom_application' ne peut pas être vide."
            )
