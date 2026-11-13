"""
Contrôleur HTTP FastAPI pour le module Intersection.

Règles fondamentales :
- Utilisation exclusive des tracking_id (UUID) dans les routes et les DTOs.
- Zéro exposition ou réception des identifiants techniques `id`.
- Reçoit les requêtes HTTP, appelle les services et retourne les réponses.
- Ne contient pas de logique métier directe.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.intersection.entities import DirectionVoie
from app.intersection.exceptions import (
    ConflitDonneesErreur,
    EntiteNonTrouveeErreur,
    ErreurValidationIntersection,
    SuppressionImpossibleErreur,
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

router = APIRouter(prefix="/api/v1", tags=["Intersections"])


def _gerer_exception_metier(exc: Exception) -> None:
    """Traduit une exception métier en HTTPException appropriée."""
    if isinstance(exc, EntiteNonTrouveeErreur):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ConflitDonneesErreur):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, SuppressionImpossibleErreur):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, ErreurValidationIntersection):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(exc), "anomalies": [a.message for a in exc.anomalies]},
        )
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ===========================================================================
# Endpoints : Intersections
# ===========================================================================


@router.post(
    "/intersections",
    response_model=IntersectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une intersection",
)
def creer_intersection(
    payload: IntersectionCreate,
    db: Session = Depends(get_db),
) -> IntersectionResponse:
    """Crée une nouvelle intersection avec génération automatique d'un tracking_id."""
    service = IntersectionService(db)
    try:
        nouvelle = service.creer_intersection(
            nom=payload.nom,
            description=payload.description,
        )
        db.commit()
        return IntersectionResponse(
            tracking_id=nouvelle.tracking_id,
            nom=nouvelle.nom,
            description=nouvelle.description,
        )
    except Exception as exc:
        db.rollback()
        _gerer_exception_metier(exc)
        raise


@router.get(
    "/intersections",
    response_model=list[IntersectionResponse],
    summary="Lister toutes les intersections",
)
def lister_intersections(
    db: Session = Depends(get_db),
) -> list[IntersectionResponse]:
    """Retourne l'ensemble des intersections enregistrées."""
    service = IntersectionService(db)
    intersections = service.lister_intersections()
    return [
        IntersectionResponse(
            tracking_id=i.tracking_id,
            nom=i.nom,
            description=i.description,
        )
        for i in intersections
    ]


@router.get(
    "/intersections/{tracking_id}",
    response_model=IntersectionResponse,
    summary="Consulter une intersection par tracking_id",
)
def obtenir_intersection(
    tracking_id: UUID,
    db: Session = Depends(get_db),
) -> IntersectionResponse:
    """Recherche une intersection spécifique par son UUID tracking_id."""
    service = IntersectionService(db)
    try:
        inter = service.obtenir_intersection(tracking_id)
        return IntersectionResponse(
            tracking_id=inter.tracking_id,
            nom=inter.nom,
            description=inter.description,
        )
    except Exception as exc:
        _gerer_exception_metier(exc)
        raise


@router.put(
    "/intersections/{tracking_id}",
    response_model=IntersectionResponse,
    summary="Modifier une intersection",
)
def modifier_intersection(
    tracking_id: UUID,
    payload: IntersectionUpdate,
    db: Session = Depends(get_db),
) -> IntersectionResponse:
    """Met à jour le nom ou la description d'une intersection."""
    service = IntersectionService(db)
    try:
        inter_maj = service.modifier_intersection(
            tracking_id=tracking_id,
            nom=payload.nom,
            description=payload.description,
        )
        db.commit()
        return IntersectionResponse(
            tracking_id=inter_maj.tracking_id,
            nom=inter_maj.nom,
            description=inter_maj.description,
        )
    except Exception as exc:
        db.rollback()
        _gerer_exception_metier(exc)
        raise


@router.delete(
    "/intersections/{tracking_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une intersection",
)
def supprimer_intersection(
    tracking_id: UUID,
    forcer_cascade: bool = Query(
        default=False,
        description="Si True, supprime les branches et voies filles en cascade",
    ),
    db: Session = Depends(get_db),
) -> None:
    """Supprime une intersection par son tracking_id en protégeant contre les orphelins."""
    service = IntersectionService(db)
    try:
        service.supprimer_intersection(tracking_id, forcer_cascade=forcer_cascade)
        db.commit()
    except Exception as exc:
        db.rollback()
        _gerer_exception_metier(exc)
        raise


@router.get(
    "/intersections/{tracking_id}/branches",
    response_model=list[BrancheResponse],
    summary="Rechercher les branches d'une intersection",
)
def lister_branches_d_une_intersection(
    tracking_id: UUID,
    db: Session = Depends(get_db),
) -> list[BrancheResponse]:
    """Retourne toutes les branches rattachées à une intersection donnée."""
    service = IntersectionService(db)
    try:
        branches = service.rechercher_branches_intersection(tracking_id)
        return [
            BrancheResponse(
                tracking_id=b.tracking_id,
                intersection_tracking_id=b.intersection_tracking_id,
                nom=b.nom,
                angle_degres=b.angle_degres,
            )
            for b in branches
        ]
    except Exception as exc:
        _gerer_exception_metier(exc)
        raise


# ===========================================================================
# Endpoints : Branches
# ===========================================================================


@router.post(
    "/branches",
    response_model=BrancheResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une branche",
)
def creer_branche(
    payload: BrancheCreate,
    db: Session = Depends(get_db),
) -> BrancheResponse:
    """Crée une branche rattachée à une intersection existante via son tracking_id."""
    service = IntersectionService(db)
    try:
        branche = service.creer_branche(
            nom=payload.nom,
            intersection_tracking_id=payload.intersection_tracking_id,
            angle_degres=payload.angle_degres,
        )
        db.commit()
        return BrancheResponse(
            tracking_id=branche.tracking_id,
            intersection_tracking_id=branche.intersection_tracking_id,
            nom=branche.nom,
            angle_degres=branche.angle_degres,
        )
    except Exception as exc:
        db.rollback()
        _gerer_exception_metier(exc)
        raise


@router.get(
    "/branches",
    response_model=list[BrancheResponse],
    summary="Lister toutes les branches",
)
def lister_branches(
    db: Session = Depends(get_db),
) -> list[BrancheResponse]:
    """Retourne l'ensemble des branches."""
    service = IntersectionService(db)
    branches = service.lister_branches()
    return [
        BrancheResponse(
            tracking_id=b.tracking_id,
            intersection_tracking_id=b.intersection_tracking_id,
            nom=b.nom,
            angle_degres=b.angle_degres,
        )
        for b in branches
    ]


@router.get(
    "/branches/{tracking_id}",
    response_model=BrancheResponse,
    summary="Consulter une branche par tracking_id",
)
def obtenir_branche(
    tracking_id: UUID,
    db: Session = Depends(get_db),
) -> BrancheResponse:
    """Recherche une branche par son tracking_id UUID."""
    service = IntersectionService(db)
    try:
        branche = service.obtenir_branche(tracking_id)
        return BrancheResponse(
            tracking_id=branche.tracking_id,
            intersection_tracking_id=branche.intersection_tracking_id,
            nom=branche.nom,
            angle_degres=branche.angle_degres,
        )
    except Exception as exc:
        _gerer_exception_metier(exc)
        raise


@router.put(
    "/branches/{tracking_id}",
    response_model=BrancheResponse,
    summary="Modifier une branche",
)
def modifier_branche(
    tracking_id: UUID,
    payload: BrancheUpdate,
    db: Session = Depends(get_db),
) -> BrancheResponse:
    """Modifie le nom ou l'angle d'une branche."""
    service = IntersectionService(db)
    try:
        branche_maj = service.modifier_branche(
            tracking_id=tracking_id,
            nom=payload.nom,
            angle_degres=payload.angle_degres,
        )
        db.commit()
        return BrancheResponse(
            tracking_id=branche_maj.tracking_id,
            intersection_tracking_id=branche_maj.intersection_tracking_id,
            nom=branche_maj.nom,
            angle_degres=branche_maj.angle_degres,
        )
    except Exception as exc:
        db.rollback()
        _gerer_exception_metier(exc)
        raise


@router.delete(
    "/branches/{tracking_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une branche",
)
def supprimer_branche(
    tracking_id: UUID,
    forcer_cascade: bool = Query(
        default=False,
        description="Si True, supprime les voies filles en cascade",
    ),
    db: Session = Depends(get_db),
) -> None:
    """Supprime une branche en empêchant les voies orphelines."""
    service = IntersectionService(db)
    try:
        service.supprimer_branche(tracking_id, forcer_cascade=forcer_cascade)
        db.commit()
    except Exception as exc:
        db.rollback()
        _gerer_exception_metier(exc)
        raise


@router.get(
    "/branches/{tracking_id}/voies",
    response_model=list[VoieResponse],
    summary="Rechercher les voies d'une branche",
)
def lister_voies_d_une_branche(
    tracking_id: UUID,
    direction: DirectionVoie | None = Query(
        default=None, description="Filtre optionnel par direction"
    ),
    db: Session = Depends(get_db),
) -> list[VoieResponse]:
    """Retourne toutes les voies d'une branche ordonnées par position."""
    service = IntersectionService(db)
    try:
        voies = service.rechercher_voies_branche(tracking_id, direction=direction)
        return [
            VoieResponse(
                tracking_id=v.tracking_id,
                branche_tracking_id=v.branche_tracking_id,
                nom=v.nom,
                direction=v.direction,
                position=v.position,
            )
            for v in voies
        ]
    except Exception as exc:
        _gerer_exception_metier(exc)
        raise


# ===========================================================================
# Endpoints : Voies
# ===========================================================================


@router.post(
    "/voies",
    response_model=VoieResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une voie",
)
def creer_voie(
    payload: VoieCreate,
    db: Session = Depends(get_db),
) -> VoieResponse:
    """Crée une voie rattachée à une branche via son tracking_id."""
    service = IntersectionService(db)
    try:
        voie = service.creer_voie(
            nom=payload.nom,
            branche_tracking_id=payload.branche_tracking_id,
            direction=payload.direction,
            position=payload.position,
        )
        db.commit()
        return VoieResponse(
            tracking_id=voie.tracking_id,
            branche_tracking_id=voie.branche_tracking_id,
            nom=voie.nom,
            direction=voie.direction,
            position=voie.position,
        )
    except Exception as exc:
        db.rollback()
        _gerer_exception_metier(exc)
        raise


@router.get(
    "/voies",
    response_model=list[VoieResponse],
    summary="Lister toutes les voies avec filtres de direction",
)
def lister_voies(
    direction: DirectionVoie | None = Query(
        default=None, description="Filtrer selon la direction (ENTRANTE ou SORTANTE)"
    ),
    db: Session = Depends(get_db),
) -> list[VoieResponse]:
    """Retourne les voies enregistrées, avec filtrage optionnel par direction au niveau SQL."""
    service = IntersectionService(db)
    voies = service.lister_voies(direction=direction)
    return [
        VoieResponse(
            tracking_id=v.tracking_id,
            branche_tracking_id=v.branche_tracking_id,
            nom=v.nom,
            direction=v.direction,
            position=v.position,
        )
        for v in voies
    ]


@router.get(
    "/voies/{tracking_id}",
    response_model=VoieResponse,
    summary="Consulter une voie par tracking_id",
)
def obtenir_voie(
    tracking_id: UUID,
    db: Session = Depends(get_db),
) -> VoieResponse:
    """Recherche une voie par son UUID tracking_id."""
    service = IntersectionService(db)
    try:
        voie = service.obtenir_voie(tracking_id)
        return VoieResponse(
            tracking_id=voie.tracking_id,
            branche_tracking_id=voie.branche_tracking_id,
            nom=voie.nom,
            direction=voie.direction,
            position=voie.position,
        )
    except Exception as exc:
        _gerer_exception_metier(exc)
        raise


@router.put(
    "/voies/{tracking_id}",
    response_model=VoieResponse,
    summary="Modifier une voie",
)
def modifier_voie(
    tracking_id: UUID,
    payload: VoieUpdate,
    db: Session = Depends(get_db),
) -> VoieResponse:
    """Modifie le nom, la direction ou la position d'une voie."""
    service = IntersectionService(db)
    try:
        voie_maj = service.modifier_voie(
            tracking_id=tracking_id,
            nom=payload.nom,
            direction=payload.direction,
            position=payload.position,
        )
        db.commit()
        return VoieResponse(
            tracking_id=voie_maj.tracking_id,
            branche_tracking_id=voie_maj.branche_tracking_id,
            nom=voie_maj.nom,
            direction=voie_maj.direction,
            position=voie_maj.position,
        )
    except Exception as exc:
        db.rollback()
        _gerer_exception_metier(exc)
        raise


@router.delete(
    "/voies/{tracking_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une voie",
)
def supprimer_voie(
    tracking_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    """Supprime une voie par son tracking_id."""
    service = IntersectionService(db)
    try:
        service.supprimer_voie(tracking_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        _gerer_exception_metier(exc)
        raise
