"""
Dépôts de persistance pour les entités du module Intersection.

Gère l'accès aux données et les opérations de persistance pour :
- Intersection
- Branche
- Voie

Toutes les requêtes SQL sont directes et optimisées, sans filtrage naïf en mémoire.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.intersection.entities import (
    Branche,
    DirectionVoie,
    Intersection,
    Voie,
)
from app.intersection.models import (
    BrancheModel,
    IntersectionModel,
    VoieModel,
)


class IntersectionRepository:
    """Accès aux données persistées pour l'entité Intersection."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def creer(self, intersection: Intersection) -> Intersection:
        """Enregistre une nouvelle intersection en base de données."""
        modele = IntersectionModel.from_domain(intersection)
        self._session.add(modele)
        self._session.flush()
        return modele.to_domain()

    def trouver_par_tracking_id(self, tracking_id: UUID) -> Intersection | None:
        """Recherche une intersection par son tracking_id UUID."""
        stmt = select(IntersectionModel).where(
            IntersectionModel.tracking_id == str(tracking_id)
        )
        modele = self._session.execute(stmt).scalar_one_or_none()
        return modele.to_domain() if modele else None

    def trouver_modele_par_tracking_id(
        self, tracking_id: UUID
    ) -> IntersectionModel | None:
        """Usage interne : retourne le modèle ORM par tracking_id."""
        stmt = select(IntersectionModel).where(
            IntersectionModel.tracking_id == str(tracking_id)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def trouver_par_id(self, id_technique: int) -> Intersection | None:
        """Usage interne : recherche une intersection par son identifiant technique."""
        stmt = select(IntersectionModel).where(IntersectionModel.id == id_technique)
        modele = self._session.execute(stmt).scalar_one_or_none()
        return modele.to_domain() if modele else None

    def lister(self) -> list[Intersection]:
        """Retourne toutes les intersections enregistrées."""
        stmt = select(IntersectionModel).order_by(IntersectionModel.nom.asc())
        modeles = self._session.execute(stmt).scalars().all()
        return [m.to_domain() for m in modeles]

    def mettre_a_jour(
        self,
        tracking_id: UUID,
        nom: str | None = None,
        description: str | None = None,
    ) -> Intersection | None:
        """Met à jour les attributs d'une intersection."""
        modele = self.trouver_modele_par_tracking_id(tracking_id)
        if not modele:
            return None
        if nom is not None:
            modele.nom = nom
        if description is not None:
            modele.description = description
        self._session.flush()
        return modele.to_domain()

    def supprimer(self, tracking_id: UUID) -> bool:
        """Supprime une intersection par son tracking_id."""
        modele = self.trouver_modele_par_tracking_id(tracking_id)
        if not modele:
            return False
        self._session.delete(modele)
        self._session.flush()
        return True


class BrancheRepository:
    """Accès aux données persistées pour l'entité Branche."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def creer(
        self, branche: Branche, intersection_id: int | None = None
    ) -> Branche:
        """Enregistre une nouvelle branche en base de données."""
        modele = BrancheModel.from_domain(branche, intersection_id=intersection_id)
        self._session.add(modele)
        self._session.flush()
        return modele.to_domain()

    def trouver_par_tracking_id(self, tracking_id: UUID) -> Branche | None:
        """Recherche une branche par son tracking_id UUID."""
        stmt = select(BrancheModel).where(
            BrancheModel.tracking_id == str(tracking_id)
        )
        modele = self._session.execute(stmt).scalar_one_or_none()
        return modele.to_domain() if modele else None

    def trouver_modele_par_tracking_id(
        self, tracking_id: UUID
    ) -> BrancheModel | None:
        """Usage interne : retourne le modèle ORM d'une branche."""
        stmt = select(BrancheModel).where(
            BrancheModel.tracking_id == str(tracking_id)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def trouver_par_id(self, id_technique: int) -> Branche | None:
        """Usage interne : recherche une branche par son identifiant technique."""
        stmt = select(BrancheModel).where(BrancheModel.id == id_technique)
        modele = self._session.execute(stmt).scalar_one_or_none()
        return modele.to_domain() if modele else None

    def lister(self) -> list[Branche]:
        """Retourne toutes les branches ordonnées par nom."""
        stmt = select(BrancheModel).order_by(BrancheModel.nom.asc())
        modeles = self._session.execute(stmt).scalars().all()
        return [m.to_domain() for m in modeles]

    def rechercher_par_intersection(
        self, intersection_tracking_id: UUID
    ) -> list[Branche]:
        """Recherche au niveau SQL toutes les branches rattachées à une intersection."""
        stmt = (
            select(BrancheModel)
            .where(
                BrancheModel.intersection_tracking_id == str(intersection_tracking_id)
            )
            .order_by(BrancheModel.nom.asc())
        )
        modeles = self._session.execute(stmt).scalars().all()
        return [m.to_domain() for m in modeles]

    def compter_par_intersection(self, intersection_tracking_id: UUID) -> int:
        """Compte le nombre de branches rattachées à une intersection directement en SQL."""
        stmt = select(func.count(BrancheModel.id)).where(
            BrancheModel.intersection_tracking_id == str(intersection_tracking_id)
        )
        return self._session.execute(stmt).scalar() or 0

    def mettre_a_jour(
        self,
        tracking_id: UUID,
        nom: str | None = None,
        angle_degres: float | None = None,
    ) -> Branche | None:
        """Met à jour les attributs d'une branche."""
        modele = self.trouver_modele_par_tracking_id(tracking_id)
        if not modele:
            return None
        if nom is not None:
            modele.nom = nom
        if angle_degres is not None:
            modele.angle_degres = angle_degres
        self._session.flush()
        return modele.to_domain()

    def supprimer(self, tracking_id: UUID) -> bool:
        """Supprime une branche par son tracking_id."""
        modele = self.trouver_modele_par_tracking_id(tracking_id)
        if not modele:
            return False
        self._session.delete(modele)
        self._session.flush()
        return True


class VoieRepository:
    """Accès aux données persistées pour l'entité Voie."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def creer(self, voie: Voie, branche_id: int | None = None) -> Voie:
        """Enregistre une nouvelle voie en base de données."""
        modele = VoieModel.from_domain(voie, branche_id=branche_id)
        self._session.add(modele)
        self._session.flush()
        return modele.to_domain()

    def trouver_par_tracking_id(self, tracking_id: UUID) -> Voie | None:
        """Recherche une voie par son tracking_id UUID."""
        stmt = select(VoieModel).where(VoieModel.tracking_id == str(tracking_id))
        modele = self._session.execute(stmt).scalar_one_or_none()
        return modele.to_domain() if modele else None

    def trouver_modele_par_tracking_id(self, tracking_id: UUID) -> VoieModel | None:
        """Usage interne : retourne le modèle ORM d'une voie."""
        stmt = select(VoieModel).where(VoieModel.tracking_id == str(tracking_id))
        return self._session.execute(stmt).scalar_one_or_none()

    def trouver_par_id(self, id_technique: int) -> Voie | None:
        """Usage interne : recherche une voie par son identifiant technique."""
        stmt = select(VoieModel).where(VoieModel.id == id_technique)
        modele = self._session.execute(stmt).scalar_one_or_none()
        return modele.to_domain() if modele else None

    def lister(self, direction: DirectionVoie | None = None) -> list[Voie]:
        """Retourne toutes les voies, filtrées optionnellement par direction au niveau SQL."""
        stmt = select(VoieModel)
        if direction is not None:
            stmt = stmt.where(VoieModel.direction == direction.value)
        stmt = stmt.order_by(VoieModel.position.asc(), VoieModel.nom.asc())
        modeles = self._session.execute(stmt).scalars().all()
        return [m.to_domain() for m in modeles]

    def rechercher_par_branche(
        self,
        branche_tracking_id: UUID,
        direction: DirectionVoie | None = None,
    ) -> list[Voie]:
        """Recherche en base les voies d'une branche, filtrées optionnellement par direction."""
        stmt = select(VoieModel).where(
            VoieModel.branche_tracking_id == str(branche_tracking_id)
        )
        if direction is not None:
            stmt = stmt.where(VoieModel.direction == direction.value)
        stmt = stmt.order_by(VoieModel.position.asc(), VoieModel.tracking_id.asc())
        modeles = self._session.execute(stmt).scalars().all()
        return [m.to_domain() for m in modeles]

    def rechercher_par_direction(self, direction: DirectionVoie) -> list[Voie]:
        """Recherche toutes les voies d'une direction donnée (ENTRANTE ou SORTANTE)."""
        return self.lister(direction=direction)

    def rechercher_voies_entrantes(
        self, branche_tracking_id: UUID | None = None
    ) -> list[Voie]:
        """Recherche ciblée SQL pour les voies entrantes."""
        if branche_tracking_id is not None:
            return self.rechercher_par_branche(
                branche_tracking_id, direction=DirectionVoie.ENTRANTE
            )
        return self.rechercher_par_direction(DirectionVoie.ENTRANTE)

    def rechercher_voies_sortantes(
        self, branche_tracking_id: UUID | None = None
    ) -> list[Voie]:
        """Recherche ciblée SQL pour les voies sortantes."""
        if branche_tracking_id is not None:
            return self.rechercher_par_branche(
                branche_tracking_id, direction=DirectionVoie.SORTANTE
            )
        return self.rechercher_par_direction(DirectionVoie.SORTANTE)

    def compter_par_branche(self, branche_tracking_id: UUID) -> int:
        """Compte le nombre de voies rattachées à une branche au niveau SQL."""
        stmt = select(func.count(VoieModel.id)).where(
            VoieModel.branche_tracking_id == str(branche_tracking_id)
        )
        return self._session.execute(stmt).scalar() or 0

    def existe_doublon_position(
        self,
        branche_tracking_id: UUID,
        direction: DirectionVoie,
        position: int,
        exclure_tracking_id: UUID | None = None,
    ) -> bool:
        """Vérifie au niveau SQL s'il existe déjà une voie à cette position et direction sur la branche."""
        stmt = select(func.count(VoieModel.id)).where(
            VoieModel.branche_tracking_id == str(branche_tracking_id),
            VoieModel.direction == direction.value,
            VoieModel.position == position,
        )
        if exclure_tracking_id is not None:
            stmt = stmt.where(VoieModel.tracking_id != str(exclure_tracking_id))
        compte = self._session.execute(stmt).scalar() or 0
        return compte > 0

    def mettre_a_jour(
        self,
        tracking_id: UUID,
        nom: str | None = None,
        direction: DirectionVoie | None = None,
        position: int | None = None,
    ) -> Voie | None:
        """Met à jour les attributs d'une voie."""
        modele = self.trouver_modele_par_tracking_id(tracking_id)
        if not modele:
            return None
        if nom is not None:
            modele.nom = nom
        if direction is not None:
            modele.direction = direction.value
        if position is not None:
            modele.position = position
        self._session.flush()
        return modele.to_domain()

    def supprimer(self, tracking_id: UUID) -> bool:
        """Supprime une voie par son tracking_id."""
        modele = self.trouver_modele_par_tracking_id(tracking_id)
        if not modele:
            return False
        self._session.delete(modele)
        self._session.flush()
        return True
