"""
Domaine métier : intersection.

Encapsule la modélisation des intersections (entités indépendantes) et les règles
de validation de leur cohérence.
"""

from app.intersection.exceptions import ErreurValidationIntersection
from app.intersection.models.topology import (
    Branche,
    DirectionVoie,
    Intersection,
    Voie,
)
from app.intersection.services.intersection_validator import (
    AnomalieValidationIntersection,
    GraviteValidation,
    RapportValidationIntersection,
    ValidateurIntersection,
    obtenir_voies_entrantes,
    obtenir_voies_sortantes,
    valider_intersection,
)

__all__ = [
    "AnomalieValidationIntersection",
    "Branche",
    "DirectionVoie",
    "ErreurValidationIntersection",
    "GraviteValidation",
    "Intersection",
    "RapportValidationIntersection",
    "ValidateurIntersection",
    "Voie",
    "obtenir_voies_entrantes",
    "obtenir_voies_sortantes",
    "valider_intersection",
]
