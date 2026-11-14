"""
Entités métier du domaine Intersection.

Règles de conception :
- Dataclasses figées (frozen=True, slots=True).
- Identifiants exclusivement sous forme de chaînes de caractères (id_intersection, id_branche, id_voie).
- Aucune dépendance externe (ni FastAPI, ni SQLAlchemy, ni Pydantic).
- Aucune collection d'entités imbriquée : relations établies par identifiants explicites.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DirectionVoie(str, Enum):
    """Sens de circulation d'une voie par rapport au centre de l'intersection."""

    ENTRANTE = "ENTRANTE"
    SORTANTE = "SORTANTE"


@dataclass(frozen=True, slots=True)
class Intersection:
    """
    Représentation métier autonome d'une intersection routière.
    Identifiant fonctionnel str, ne contient aucune collection de branches.
    """

    id_intersection: str
    nom: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class Branche:
    """
    Représente une branche d'accès rattachée à une intersection.
    Identifiant fonctionnel str, reliée à son intersection par id_intersection.
    Angle en degrés obligatoire (azimut horaire 0..360°).
    Ne contient aucune collection de voies.
    """

    id_branche: str
    id_intersection: str
    nom: str
    angle_degres: float


@dataclass(frozen=True, slots=True)
class Voie:
    """
    Représente une voie physique de circulation.
    Identifiant fonctionnel str, reliée à sa branche par id_branche.
    Ne contient aucune référence directe à l'objet Branche.
    """

    id_voie: str
    id_branche: str
    nom: str
    direction: DirectionVoie = DirectionVoie.ENTRANTE
    position: int = 1
