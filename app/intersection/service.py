"""
Service applicatif d'orchestration CRUD et métier pour le domaine Intersection.

Règles respectées :
- Utilisation exclusive des tracking_id pour toutes les opérations fonctionnelles.
- Pas d'exposition des id techniques.
- Contrôle d'intégrité avant persistance :
  * Interdiction de rattacher une branche à une intersection inexistante.
  * Interdiction de rattacher une voie à une branche inexistante.
  * Unicité des positions par branche et direction.
  * Protection contre les références orphelines à la suppression.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.intersection.entities import (
    Branche,
    DirectionVoie,
    Intersection,
    Voie,
)
from app.intersection.exceptions import (
    ConflitDonneesErreur,
    EntiteNonTrouveeErreur,
    ErreurValidationIntersection,
    SuppressionImpossibleErreur,
)
from app.intersection.repository import (
    BrancheRepository,
    IntersectionRepository,
    VoieRepository,
)
from app.intersection.validator import (
    AnomalieValidationIntersection,
    _est_angle_valide,
    _est_position_voie_valide,
    _normaliser_chaine,
)


class IntersectionService:
    """Orchestre les opérations métier et la persistance du module Intersection."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._intersection_repo = IntersectionRepository(session)
        self._branche_repo = BrancheRepository(session)
        self._voie_repo = VoieRepository(session)

    # -----------------------------------------------------------------------
    # CRUD & Recherches : Intersection
    # -----------------------------------------------------------------------

    def creer_intersection(
        self,
        nom: str,
        description: str = "",
        tracking_id: UUID | None = None,
    ) -> Intersection:
        """Crée et persiste une nouvelle intersection."""
        nom_nettoye = _normaliser_chaine(nom)
        if not nom_nettoye:
            raise ErreurValidationIntersection(
                "Le nom de l'intersection ne peut pas être vide.",
                (
                    AnomalieValidationIntersection(
                        code="NOM_INTERSECTION_VIDE",
                        message="Le nom de l'intersection doit être une chaîne non vide.",
                        champ="nom",
                    ),
                ),
            )

        tid = tracking_id or uuid4()
        if self._intersection_repo.trouver_par_tracking_id(tid):
            raise ConflitDonneesErreur(
                f"Une intersection avec le tracking_id '{tid}' existe déjà."
            )

        intersection = Intersection(
            nom=nom_nettoye,
            description=description.strip() if isinstance(description, str) else "",
            tracking_id=tid,
        )
        return self._intersection_repo.creer(intersection)

    def obtenir_intersection(self, tracking_id: UUID) -> Intersection:
        """Retourne une intersection par son tracking_id ou lève une exception."""
        intersection = self._intersection_repo.trouver_par_tracking_id(tracking_id)
        if not intersection:
            raise EntiteNonTrouveeErreur(
                f"Intersection introuvable pour le tracking_id '{tracking_id}'."
            )
        return intersection

    def lister_intersections(self) -> list[Intersection]:
        """Retourne toutes les intersections enregistrées."""
        return self._intersection_repo.lister()

    def modifier_intersection(
        self,
        tracking_id: UUID,
        nom: str | None = None,
        description: str | None = None,
    ) -> Intersection:
        """Modifie les informations d'une intersection."""
        self.obtenir_intersection(tracking_id)
        nom_nettoye = None
        if nom is not None:
            nom_nettoye = _normaliser_chaine(nom)
            if not nom_nettoye:
                raise ErreurValidationIntersection(
                    "Le nom de l'intersection ne peut pas être vide.",
                    (
                        AnomalieValidationIntersection(
                            code="NOM_INTERSECTION_VIDE",
                            message="Le nom de l'intersection doit être une chaîne non vide.",
                            champ="nom",
                        ),
                    ),
                )

        intersection_maj = self._intersection_repo.mettre_a_jour(
            tracking_id=tracking_id,
            nom=nom_nettoye,
            description=description.strip() if description is not None else None,
        )
        if not intersection_maj:
            raise EntiteNonTrouveeErreur(
                f"Intersection introuvable pour le tracking_id '{tracking_id}'."
            )
        return intersection_maj

    def supprimer_intersection(
        self, tracking_id: UUID, forcer_cascade: bool = False
    ) -> None:
        """
        Supprime une intersection.
        Empêche la suppression si des branches sont associées, sauf si forcer_cascade=True.
        """
        self.obtenir_intersection(tracking_id)
        branches = self._branche_repo.rechercher_par_intersection(tracking_id)
        if branches:
            if not forcer_cascade:
                raise SuppressionImpossibleErreur(
                    f"Impossible de supprimer l'intersection '{tracking_id}' : "
                    f"{len(branches)} branche(s) lui sont encore rattachée(s)."
                )
            for branche in branches:
                self.supprimer_branche(branche.tracking_id, forcer_cascade=True)

        self._intersection_repo.supprimer(tracking_id)

    # -----------------------------------------------------------------------
    # CRUD & Recherches : Branche
    # -----------------------------------------------------------------------

    def creer_branche(
        self,
        nom: str,
        intersection_tracking_id: UUID,
        angle_degres: float | None = None,
        tracking_id: UUID | None = None,
    ) -> Branche:
        """Crée et persiste une branche rattachée à une intersection existante."""
        nom_nettoye = _normaliser_chaine(nom)
        if not nom_nettoye:
            raise ErreurValidationIntersection(
                "Le nom de la branche ne peut pas être vide.",
                (
                    AnomalieValidationIntersection(
                        code="NOM_BRANCHE_VIDE",
                        message="Le nom de la branche doit être une chaîne non vide.",
                        champ="nom",
                    ),
                ),
            )

        if angle_degres is not None and not _est_angle_valide(angle_degres):
            raise ErreurValidationIntersection(
                f"Angle de branche invalide : {angle_degres}.",
                (
                    AnomalieValidationIntersection(
                        code="ANGLE_BRANCHE_INVALIDE",
                        message=f"L'angle doit être compris entre 0.0 et 360.0 (reçu: {angle_degres}).",
                        champ="angle_degres",
                    ),
                ),
            )

        intersection = self._intersection_repo.trouver_par_tracking_id(
            intersection_tracking_id
        )
        if not intersection:
            raise EntiteNonTrouveeErreur(
                f"Impossible de créer la branche : l'intersection parente "
                f"'{intersection_tracking_id}' n'existe pas."
            )

        tid = tracking_id or uuid4()
        if self._branche_repo.trouver_par_tracking_id(tid):
            raise ConflitDonneesErreur(
                f"Une branche avec le tracking_id '{tid}' existe déjà."
            )

        branche = Branche(
            nom=nom_nettoye,
            intersection_tracking_id=intersection_tracking_id,
            intersection_id=intersection.id,
            angle_degres=angle_degres,
            tracking_id=tid,
        )
        return self._branche_repo.creer(branche, intersection_id=intersection.id)

    def obtenir_branche(self, tracking_id: UUID) -> Branche:
        """Retourne une branche par son tracking_id ou lève une exception."""
        branche = self._branche_repo.trouver_par_tracking_id(tracking_id)
        if not branche:
            raise EntiteNonTrouveeErreur(
                f"Branche introuvable pour le tracking_id '{tracking_id}'."
            )
        return branche

    def lister_branches(self) -> list[Branche]:
        """Retourne toutes les branches."""
        return self._branche_repo.lister()

    def rechercher_branches_intersection(
        self, intersection_tracking_id: UUID
    ) -> list[Branche]:
        """Retourne toutes les branches d'une intersection."""
        self.obtenir_intersection(intersection_tracking_id)
        return self._branche_repo.rechercher_par_intersection(
            intersection_tracking_id
        )

    def modifier_branche(
        self,
        tracking_id: UUID,
        nom: str | None = None,
        angle_degres: float | None = None,
    ) -> Branche:
        """Modifie les attributs d'une branche."""
        self.obtenir_branche(tracking_id)
        nom_nettoye = None
        if nom is not None:
            nom_nettoye = _normaliser_chaine(nom)
            if not nom_nettoye:
                raise ErreurValidationIntersection(
                    "Le nom de la branche ne peut pas être vide.",
                    (
                        AnomalieValidationIntersection(
                            code="NOM_BRANCHE_VIDE",
                            message="Le nom de la branche doit être une chaîne non vide.",
                            champ="nom",
                        ),
                    ),
                )

        if angle_degres is not None and not _est_angle_valide(angle_degres):
            raise ErreurValidationIntersection(
                f"Angle de branche invalide : {angle_degres}.",
                (
                    AnomalieValidationIntersection(
                        code="ANGLE_BRANCHE_INVALIDE",
                        message=f"L'angle doit être compris entre 0.0 et 360.0 (reçu: {angle_degres}).",
                        champ="angle_degres",
                    ),
                ),
            )

        branche_maj = self._branche_repo.mettre_a_jour(
            tracking_id=tracking_id,
            nom=nom_nettoye,
            angle_degres=angle_degres,
        )
        if not branche_maj:
            raise EntiteNonTrouveeErreur(
                f"Branche introuvable pour le tracking_id '{tracking_id}'."
            )
        return branche_maj

    def supprimer_branche(
        self, tracking_id: UUID, forcer_cascade: bool = False
    ) -> None:
        """
        Supprime une branche.
        Empêche la suppression si des voies y sont rattachées, sauf si forcer_cascade=True.
        """
        self.obtenir_branche(tracking_id)
        voies = self._voie_repo.rechercher_par_branche(tracking_id)
        if voies:
            if not forcer_cascade:
                raise SuppressionImpossibleErreur(
                    f"Impossible de supprimer la branche '{tracking_id}' : "
                    f"{len(voies)} voie(s) lui sont encore rattachée(s)."
                )
            for voie in voies:
                self.supprimer_voie(voie.tracking_id)

        self._branche_repo.supprimer(tracking_id)

    # -----------------------------------------------------------------------
    # CRUD & Recherches : Voie
    # -----------------------------------------------------------------------

    def creer_voie(
        self,
        nom: str,
        branche_tracking_id: UUID,
        direction: DirectionVoie,
        position: int = 1,
        tracking_id: UUID | None = None,
    ) -> Voie:
        """Crée et persiste une nouvelle voie rattachée à une branche existante."""
        nom_nettoye = _normaliser_chaine(nom)
        if not nom_nettoye:
            raise ErreurValidationIntersection(
                "Le nom de la voie ne peut pas être vide.",
                (
                    AnomalieValidationIntersection(
                        code="NOM_VOIE_VIDE",
                        message="Le nom de la voie doit être une chaîne non vide.",
                        champ="nom",
                    ),
                ),
            )

        if not isinstance(direction, DirectionVoie):
            raise ErreurValidationIntersection(
                "Direction de voie invalide.",
                (
                    AnomalieValidationIntersection(
                        code="DIRECTION_VOIE_INVALIDE",
                        message="La direction doit être DirectionVoie.ENTRANTE ou SORTANTE.",
                        champ="direction",
                    ),
                ),
            )

        if not _est_position_voie_valide(position):
            raise ErreurValidationIntersection(
                f"Position de voie invalide : {position}.",
                (
                    AnomalieValidationIntersection(
                        code="POSITION_VOIE_INVALIDE",
                        message=f"La position doit être un entier supérieur ou égal à 1 (reçu: {position}).",
                        champ="position",
                    ),
                ),
            )

        branche = self._branche_repo.trouver_par_tracking_id(branche_tracking_id)
        if not branche:
            raise EntiteNonTrouveeErreur(
                f"Impossible de créer la voie : la branche parente "
                f"'{branche_tracking_id}' n'existe pas."
            )

        if self._voie_repo.existe_doublon_position(
            branche_tracking_id=branche_tracking_id,
            direction=direction,
            position=position,
        ):
            raise ConflitDonneesErreur(
                f"Une voie existe déjà à la position {position} pour la direction "
                f"'{direction.value}' sur la branche '{branche_tracking_id}'."
            )

        tid = tracking_id or uuid4()
        if self._voie_repo.trouver_par_tracking_id(tid):
            raise ConflitDonneesErreur(
                f"Une voie avec le tracking_id '{tid}' existe déjà."
            )

        voie = Voie(
            nom=nom_nettoye,
            branche_tracking_id=branche_tracking_id,
            branche_id=branche.id,
            direction=direction,
            position=position,
            tracking_id=tid,
        )
        return self._voie_repo.creer(voie, branche_id=branche.id)

    def obtenir_voie(self, tracking_id: UUID) -> Voie:
        """Retourne une voie par son tracking_id ou lève une exception."""
        voie = self._voie_repo.trouver_par_tracking_id(tracking_id)
        if not voie:
            raise EntiteNonTrouveeErreur(
                f"Voie introuvable pour le tracking_id '{tracking_id}'."
            )
        return voie

    def lister_voies(
        self, direction: DirectionVoie | None = None
    ) -> list[Voie]:
        """Retourne toutes les voies, filtrées optionnellement par direction."""
        return self._voie_repo.lister(direction=direction)

    def rechercher_voies_branche(
        self,
        branche_tracking_id: UUID,
        direction: DirectionVoie | None = None,
    ) -> list[Voie]:
        """Retourne toutes les voies d'une branche, triées par position."""
        self.obtenir_branche(branche_tracking_id)
        return self._voie_repo.rechercher_par_branche(
            branche_tracking_id=branche_tracking_id,
            direction=direction,
        )

    def rechercher_voies_entrantes(
        self, branche_tracking_id: UUID | None = None
    ) -> list[Voie]:
        """Recherche ciblée des voies entrantes."""
        if branche_tracking_id is not None:
            self.obtenir_branche(branche_tracking_id)
        return self._voie_repo.rechercher_voies_entrantes(
            branche_tracking_id=branche_tracking_id
        )

    def rechercher_voies_sortantes(
        self, branche_tracking_id: UUID | None = None
    ) -> list[Voie]:
        """Recherche ciblée des voies sortantes."""
        if branche_tracking_id is not None:
            self.obtenir_branche(branche_tracking_id)
        return self._voie_repo.rechercher_voies_sortantes(
            branche_tracking_id=branche_tracking_id
        )

    def modifier_voie(
        self,
        tracking_id: UUID,
        nom: str | None = None,
        direction: DirectionVoie | None = None,
        position: int | None = None,
    ) -> Voie:
        """Modifie les attributs d'une voie avec contrôle d'intégrité."""
        voie_existante = self.obtenir_voie(tracking_id)

        nom_nettoye = None
        if nom is not None:
            nom_nettoye = _normaliser_chaine(nom)
            if not nom_nettoye:
                raise ErreurValidationIntersection(
                    "Le nom de la voie ne peut pas être vide.",
                    (
                        AnomalieValidationIntersection(
                            code="NOM_VOIE_VIDE",
                            message="Le nom de la voie doit être une chaîne non vide.",
                            champ="nom",
                        ),
                    ),
                )

        dir_cible = direction if direction is not None else voie_existante.direction
        pos_cible = position if position is not None else voie_existante.position

        if position is not None and not _est_position_voie_valide(position):
            raise ErreurValidationIntersection(
                f"Position de voie invalide : {position}.",
                (
                    AnomalieValidationIntersection(
                        code="POSITION_VOIE_INVALIDE",
                        message=f"La position doit être un entier >= 1 (reçu: {position}).",
                        champ="position",
                    ),
                ),
            )

        if direction is not None or position is not None:
            if self._voie_repo.existe_doublon_position(
                branche_tracking_id=voie_existante.branche_tracking_id,
                direction=dir_cible,
                position=pos_cible,
                exclure_tracking_id=tracking_id,
            ):
                raise ConflitDonneesErreur(
                    f"Une voie existe déjà à la position {pos_cible} pour la direction "
                    f"'{dir_cible.value}' sur la branche '{voie_existante.branche_tracking_id}'."
                )

        voie_maj = self._voie_repo.mettre_a_jour(
            tracking_id=tracking_id,
            nom=nom_nettoye,
            direction=direction,
            position=position,
        )
        if not voie_maj:
            raise EntiteNonTrouveeErreur(
                f"Voie introuvable pour le tracking_id '{tracking_id}'."
            )
        return voie_maj

    def supprimer_voie(self, tracking_id: UUID) -> None:
        """Supprime une voie par son tracking_id."""
        self.obtenir_voie(tracking_id)
        self._voie_repo.supprimer(tracking_id)
