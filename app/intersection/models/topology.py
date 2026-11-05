"""
Modèles métier de la structure topologique d'un carrefour.

Architecture à entités indépendantes avec double identification :
- `id`: identifiant technique (clé primaire de persistance BDD, typiquement int | None = None)
- `tracking_id`: identifiant fonctionnel UUID (génération automatique uuid4)
- Les associations métier entre entités sont représentées par des identifiants explicites :
  * Branche possède `intersection_tracking_id: UUID` (et `intersection_id: int | None = None`)
  * Voie possède `branche_tracking_id: UUID` (et `branche_id: int | None = None`)
- Aucune entité ne contient de collection d'autres entités (pas de @OneToMany, pas de @ManyToMany).
- Aucune entité n'embarque une référence d'objet directe vers une autre entité.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4


class DirectionVoie(str, Enum):
    """Sens de circulation d'une voie par rapport au cœur de l'intersection."""

    ENTRANTE = "ENTRANTE"
    SORTANTE = "SORTANTE"


@dataclass(frozen=True, slots=True)
class Intersection:
    """
    Représentation métier autonome d'une intersection routière.
    Possède un identifiant technique `id` et un UUID fonctionnel `tracking_id`.
    Ne contient aucune collection de branches.
    """

    nom: str
    description: str = ""
    id: int | None = None
    tracking_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class Branche:
    """
    Représente une chaussée (branche) qui rejoint une intersection.
    Possède son propre `id` technique et son UUID `tracking_id`.
    Rattachée à son intersection par `intersection_tracking_id` (UUID) et `intersection_id` (technique).
    Ne contient aucune collection de voies ni d'objet Intersection.
    """

    nom: str
    intersection_tracking_id: UUID
    intersection_id: int | None = None
    angle_degres: float | None = None
    id: int | None = None
    tracking_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class Voie:
    """
    Représente une voie physique de circulation.
    Possède son propre `id` technique et son UUID `tracking_id`.
    Rattachée à sa branche par `branche_tracking_id` (UUID) et `branche_id` (technique).
    Ne contient aucun objet Branche.
    """

    nom: str
    branche_tracking_id: UUID
    branche_id: int | None = None
    direction: DirectionVoie = DirectionVoie.ENTRANTE
    position: int = 1
    id: int | None = None
    tracking_id: UUID = field(default_factory=uuid4)
