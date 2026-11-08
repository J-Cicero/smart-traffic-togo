"""
Module Intersection : gestion de la topologie, persistance et API REST.

Organisation interne :
- entities.py : entités métier pures (Intersection, Branche, Voie).
- models.py : modèles de tables SQLAlchemy ORM.
- schemas.py : contrats DTO Pydantic d'entrée/sortie.
- repository.py : accès aux données et requêtes SQL.
- service.py : orchestration métier et intégrité CRUD.
- validator.py : règles de validation topologique.
- controller.py : contrôleur HTTP FastAPI.
- exceptions.py : exceptions métier du domaine.
"""

from app.intersection.controller import router
from app.intersection.entities import (
    Branche,
    DirectionVoie,
    Intersection,
    Voie,
)
from app.intersection.exceptions import (
    ConflitDonneesErreur,
    EntiteNonTrouveeErreur,
    ErreurIntersectionBase,
    ErreurValidationIntersection,
    SuppressionImpossibleErreur,
)
from app.intersection.models import (
    BrancheModel,
    IntersectionModel,
    VoieModel,
)
from app.intersection.repository import (
    BrancheRepository,
    IntersectionRepository,
    VoieRepository,
)
from app.intersection.schemas import (
    BrancheCreate,
    BrancheResponse,
    BrancheUpdate,
    IntersectionCreate,
    IntersectionResponse,
    IntersectionUpdate,
    VoieCreate,
    VoieResponse,
    VoieUpdate,
)
from app.intersection.service import IntersectionService
from app.intersection.validator import (
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
    "BrancheCreate",
    "BrancheModel",
    "BrancheRepository",
    "BrancheResponse",
    "BrancheUpdate",
    "ConflitDonneesErreur",
    "DirectionVoie",
    "EntiteNonTrouveeErreur",
    "ErreurIntersectionBase",
    "ErreurValidationIntersection",
    "GraviteValidation",
    "Intersection",
    "IntersectionCreate",
    "IntersectionModel",
    "IntersectionRepository",
    "IntersectionResponse",
    "IntersectionUpdate",
    "IntersectionService",
    "RapportValidationIntersection",
    "SuppressionImpossibleErreur",
    "ValidateurIntersection",
    "Voie",
    "VoieCreate",
    "VoieModel",
    "VoieRepository",
    "VoieResponse",
    "VoieUpdate",
    "obtenir_voies_entrantes",
    "obtenir_voies_sortantes",
    "router",
    "valider_intersection",
]
