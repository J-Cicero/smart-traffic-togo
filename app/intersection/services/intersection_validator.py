"""
Service de validation évolutive de la cohérence d'une intersection à entités indépendantes.

Double identification et rattachement :
- Chaque entité possède un identifiant technique `id` (int | None) et un `tracking_id` (UUID).
- Les associations métier en mémoire reposent sur les identifiants explicites UUID :
  * `branche.intersection_tracking_id` fait référence à `intersection.tracking_id`
  * `voie.branche_tracking_id` fait référence à `branche.tracking_id`
- Les clés étrangères techniques `intersection_id` et `branche_id` sont supportées pour la persistance BDD.

Échelle d'évolution du validateur :
1. [ACTIF] Validation de l'identité de l'intersection (tracking_id UUID, id technique, nom, description).
2. [ACTIF] Cohérence de la topologie et des branches indépendantes
   (tracking_id UUID, rattachement par intersection_tracking_id UUID, >= 3 branches valides,
   unicité des tracking_id, angles finis 0..360).
3. [ACTIF] Validité des voies indépendantes
   (tracking_id UUID, rattachement exclusif aux branches valides par branche_tracking_id UUID,
   >= 1 voie entièrement valide par branche, unicité globale des tracking_id,
   nom non vide, direction valide, position >= 1 et unicité de la position par (branche_tracking_id, direction)).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import TypeGuard
from uuid import UUID

from app.intersection.exceptions import ErreurValidationIntersection
from app.intersection.models.topology import (
    Branche,
    DirectionVoie,
    Intersection,
    Voie,
)

NOMBRE_MIN_BRANCHES = 3
ANGLE_MIN_DEGRES = 0.0
ANGLE_MAX_DEGRES = 360.0


def _normaliser_chaine(valeur: object) -> str | None:
    """
    Extrait une chaîne nettoyée (`.strip()`) si et seulement si `valeur` est de type `str`.
    Retourne `None` si `valeur` n'est pas une chaîne (`int`, `None`, `list`, etc.).
    """
    if not isinstance(valeur, str):
        return None
    return valeur.strip()


def _est_sequence_objets(valeur: object) -> TypeGuard[Sequence[object]]:
    """
    Vérifie que `valeur` est une séquence itérable d'objets et non une chaîne ou des octets.
    """
    return isinstance(valeur, Sequence) and not isinstance(
        valeur, (str, bytes, bytearray)
    )


def _est_angle_valide(angle: object) -> bool:
    """
    Vérifie qu'un angle est un nombre réel fini (`int` ou `float`, hors `bool`),
    ni `NaN` ni infini (`inf`, `-inf`), et compris dans [0.0, 360.0].
    """
    if isinstance(angle, bool) or not isinstance(angle, (int, float)):
        return False
    valeur = float(angle)
    if not math.isfinite(valeur):
        return False
    return ANGLE_MIN_DEGRES <= valeur <= ANGLE_MAX_DEGRES


def _est_position_voie_valide(position: object) -> TypeGuard[int]:
    """
    Vérifie que la position d'une voie est un entier strictement positif (>= 1), hors `bool`.
    """
    return (
        isinstance(position, int)
        and not isinstance(position, bool)
        and position >= 1
    )


def _est_uuid_valide(valeur: object) -> TypeGuard[UUID]:
    """
    Vérifie que la valeur est une instance valide de UUID.
    """
    return isinstance(valeur, UUID)


def _est_id_technique_valide(valeur: object) -> bool:
    """
    Vérifie qu'un identifiant technique de base de données est soit None, soit un entier >= 1 (hors bool).
    """
    if valeur is None:
        return True
    return isinstance(valeur, int) and not isinstance(valeur, bool) and valeur >= 1


class GraviteValidation(str, Enum):
    """Gravité d'une anomalie relevée sur une intersection."""

    AVERTISSEMENT = "AVERTISSEMENT"
    ERREUR = "ERREUR"


@dataclass(frozen=True, slots=True)
class AnomalieValidationIntersection:
    """Anomalie unitaire détectée lors de la vérification d'une intersection."""

    code: str
    message: str
    gravite: GraviteValidation = GraviteValidation.ERREUR
    champ: str | None = None


@dataclass(slots=True)
class RapportValidationIntersection:
    """Rapport complet des vérifications exécutées sur une intersection."""

    _anomalies: list[AnomalieValidationIntersection] = field(default_factory=list)
    _etapes_executees: list[str] = field(default_factory=list)

    @property
    def anomalies(self) -> tuple[AnomalieValidationIntersection, ...]:
        """Retourne toutes les anomalies collectées."""
        return tuple(self._anomalies)

    @property
    def erreurs(self) -> tuple[AnomalieValidationIntersection, ...]:
        """Retourne uniquement les erreurs bloquantes."""
        return tuple(
            anomalie
            for anomalie in self._anomalies
            if anomalie.gravite == GraviteValidation.ERREUR
        )

    @property
    def avertissements(self) -> tuple[AnomalieValidationIntersection, ...]:
        """Retourne uniquement les avertissements non bloquants."""
        return tuple(
            anomalie
            for anomalie in self._anomalies
            if anomalie.gravite == GraviteValidation.AVERTISSEMENT
        )

    @property
    def etapes_executees(self) -> tuple[str, ...]:
        """Retourne la liste ordonnée des étapes de validation réellement exécutées."""
        return tuple(self._etapes_executees)

    @property
    def est_valide(self) -> bool:
        """Indique si l'intersection est valide (aucune erreur bloquante)."""
        return len(self.erreurs) == 0

    def enregistrer_etape(self, nom_etape: str) -> None:
        """Enregistre l'exécution effective d'une étape de validation."""
        self._etapes_executees.append(nom_etape)

    def ajouter_erreur(
        self,
        code: str,
        message: str,
        champ: str | None = None,
    ) -> None:
        """Ajoute une erreur bloquante au rapport."""
        self._anomalies.append(
            AnomalieValidationIntersection(
                code=code,
                message=message,
                gravite=GraviteValidation.ERREUR,
                champ=champ,
            )
        )

    def ajouter_avertissement(
        self,
        code: str,
        message: str,
        champ: str | None = None,
    ) -> None:
        """Ajoute un avertissement non bloquant au rapport."""
        self._anomalies.append(
            AnomalieValidationIntersection(
                code=code,
                message=message,
                gravite=GraviteValidation.AVERTISSEMENT,
                champ=champ,
            )
        )

    def lever_si_invalide(self) -> None:
        """Lève une exception de validation si au moins une erreur bloquante est présente."""
        if not self.est_valide:
            details = [f"[{e.code}] {e.message}" for e in self.erreurs]
            raise ErreurValidationIntersection(
                f"Validation de l'intersection échouée ({len(self.erreurs)} erreur(s)):\n"
                + "\n".join(details)
            )


class ValidateurIntersection:
    """
    Validateur de cohérence d'intersection pour entités indépendantes.
    Vérifie l'intégrité de la topologie, le rattachement par tracking_id (UUID),
    l'exactitude des identifiants techniques et l'unicité stricte des voies.
    """

    def valider(
        self,
        intersection: object,
        branches: object = (),
        voies: object = (),
    ) -> RapportValidationIntersection:
        """Point d'entrée principal de validation."""
        rapport = RapportValidationIntersection()

        # Étape 1 : Identité de l'intersection
        intersection_tracking_id_valide = self._valider_identite(intersection, rapport)

        # Si l'intersection elle-même n'est pas une instance ou son type est invalide, on arrête
        if not isinstance(intersection, Intersection):
            if not _est_sequence_objets(branches):
                rapport.ajouter_erreur(
                    code="TYPE_COLLECTION_BRANCHES_INVALIDE",
                    message="L'argument 'branches' doit être une séquence d'instances de Branche.",
                    champ="branches",
                )
            if not _est_sequence_objets(voies):
                rapport.ajouter_erreur(
                    code="TYPE_COLLECTION_VOIES_INVALIDE",
                    message="L'argument 'voies' doit être une séquence d'instances de Voie.",
                    champ="voies",
                )
            return rapport

        # Étape 2 : Branches indépendantes et rattachement par intersection_tracking_id
        tracking_ids_branches_valides = self._valider_topologie(
            intersection_tracking_id_valide=intersection_tracking_id_valide,
            branches=branches,
            rapport=rapport,
        )

        # Étape 3 : Voies indépendantes et rattachement par branche_tracking_id
        self._valider_voies(
            branches=branches,
            tracking_ids_branches_valides=tracking_ids_branches_valides,
            voies=voies,
            rapport=rapport,
        )

        return rapport

    def _valider_identite(
        self,
        intersection: object,
        rapport: RapportValidationIntersection,
    ) -> UUID | None:
        """
        Étape 1 (Active) : vérifie l'existence, le type, le tracking_id (UUID),
        l'identifiant technique `id` et le nom de l'intersection.
        """
        rapport.enregistrer_etape("identite")

        if not isinstance(intersection, Intersection):
            rapport.ajouter_erreur(
                code="TYPE_INTERSECTION_INVALIDE",
                message="L'argument 'intersection' doit être une instance de Intersection.",
                champ="intersection",
            )
            return None

        # Validation de l'UUID de traçage (tracking_id)
        if not _est_uuid_valide(intersection.tracking_id):
            rapport.ajouter_erreur(
                code="TRACKING_ID_INTERSECTION_INVALIDE",
                message="Le tracking_id de l'intersection doit être un UUID valide.",
                champ="tracking_id",
            )
            tracking_id_valide: UUID | None = None
        else:
            tracking_id_valide = intersection.tracking_id

        # Validation de l'identifiant technique (id BDD)
        if not _est_id_technique_valide(intersection.id):
            rapport.ajouter_erreur(
                code="ID_INTERSECTION_INVALIDE",
                message="L'id technique de l'intersection doit être un entier positif (>= 1) ou None.",
                champ="id",
            )

        nom_normalise = _normaliser_chaine(intersection.nom)
        if not nom_normalise:
            rapport.ajouter_erreur(
                code="NOM_INTERSECTION_VIDE",
                message="Le nom de l'intersection doit être une chaîne non vide.",
                champ="nom",
            )

        description_normalisee = _normaliser_chaine(intersection.description)
        if description_normalisee is None:
            rapport.ajouter_erreur(
                code="DESCRIPTION_INTERSECTION_INVALIDE",
                message="La description de l'intersection doit être une chaîne de caractères.",
                champ="description",
            )
        elif not description_normalisee:
            rapport.ajouter_avertissement(
                code="DESCRIPTION_INTERSECTION_VIDE",
                message="La description de l'intersection n'est pas renseignée.",
                champ="description",
            )

        if not rapport.est_valide:
            return None
        return tracking_id_valide

    def _valider_topologie(
        self,
        intersection_tracking_id_valide: UUID | None,
        branches: object,
        rapport: RapportValidationIntersection,
    ) -> set[UUID]:
        """
        Étape 2 (Active) : vérifie les branches indépendantes et leur rattachement explicite
        par `intersection_tracking_id` (UUID).
        Retourne l'ensemble des `tracking_id` (UUID) de branches entièrement valides.
        """
        rapport.enregistrer_etape("topologie")

        if not _est_sequence_objets(branches):
            rapport.ajouter_erreur(
                code="TYPE_COLLECTION_BRANCHES_INVALIDE",
                message="L'argument 'branches' doit être une séquence d'instances de Branche.",
                champ="branches",
            )
            return set()

        tracking_ids_vus: set[UUID] = set()
        tracking_ids_dupliques: set[UUID] = set()
        tracking_ids_candidats_valides: set[UUID] = set()

        for idx, branche in enumerate(branches):
            est_branche_valide, tid_b = self._valider_branche(
                branche=branche,
                index=idx,
                intersection_tracking_id_valide=intersection_tracking_id_valide,
                tracking_ids_vus=tracking_ids_vus,
                tracking_ids_dupliques=tracking_ids_dupliques,
                rapport=rapport,
            )
            if est_branche_valide and tid_b is not None:
                tracking_ids_candidats_valides.add(tid_b)

        tracking_ids_valides = tracking_ids_candidats_valides - tracking_ids_dupliques

        if len(tracking_ids_valides) < NOMBRE_MIN_BRANCHES:
            rapport.ajouter_erreur(
                code="NOMBRE_BRANCHES_INSUFFISANT",
                message=(
                    f"Une intersection doit posséder au moins {NOMBRE_MIN_BRANCHES} branches "
                    f"valides rattachées ({len(tracking_ids_valides)} valide(s) sur {len(branches)} fournie(s))."
                ),
                champ="branches",
            )

        return tracking_ids_valides

    def _valider_branche(
        self,
        branche: object,
        index: int,
        intersection_tracking_id_valide: UUID | None,
        tracking_ids_vus: set[UUID],
        tracking_ids_dupliques: set[UUID],
        rapport: RapportValidationIntersection,
    ) -> tuple[bool, UUID | None]:
        """
        Vérifie le type, le tracking_id (UUID), l'id technique, le rattachement
        intersection_tracking_id, le nom et l'angle d'une branche.
        """
        prefixe_champ = f"branches[{index}]"
        if not isinstance(branche, Branche):
            rapport.ajouter_erreur(
                code="TYPE_BRANCHE_INVALIDE",
                message=f"L'élément à l'index {index} de 'branches' doit être une instance de Branche.",
                champ=prefixe_champ,
            )
            return False, None

        aucune_erreur = True

        # Validation du tracking_id (UUID)
        if not _est_uuid_valide(branche.tracking_id):
            rapport.ajouter_erreur(
                code="TRACKING_ID_BRANCHE_INVALIDE",
                message=f"Le tracking_id de la branche à l'index {index} doit être un UUID valide.",
                champ=f"{prefixe_champ}.tracking_id",
            )
            aucune_erreur = False
            tid_b = None
        elif branche.tracking_id in tracking_ids_vus:
            tracking_ids_dupliques.add(branche.tracking_id)
            rapport.ajouter_erreur(
                code="TRACKING_ID_BRANCHE_DUPLIQUE",
                message=f"Le tracking_id '{branche.tracking_id}' est dupliqué au sein de l'intersection.",
                champ=f"{prefixe_champ}.tracking_id",
            )
            aucune_erreur = False
            tid_b = branche.tracking_id
        else:
            tracking_ids_vus.add(branche.tracking_id)
            tid_b = branche.tracking_id

        # Validation des identifiants techniques éventuels (id et intersection_id)
        if not _est_id_technique_valide(branche.id):
            rapport.ajouter_erreur(
                code="ID_BRANCHE_INVALIDE",
                message=f"L'id technique de la branche à l'index {index} doit être un entier positif ou None.",
                champ=f"{prefixe_champ}.id",
            )
            aucune_erreur = False

        if not _est_id_technique_valide(branche.intersection_id):
            rapport.ajouter_erreur(
                code="ID_INTERSECTION_INVALIDE",
                message=f"L'intersection_id technique de la branche à l'index {index} doit être un entier positif ou None.",
                champ=f"{prefixe_champ}.intersection_id",
            )
            aucune_erreur = False

        # Vérification du rattachement explicite intersection_tracking_id (UUID)
        if (
            intersection_tracking_id_valide is None
            or not _est_uuid_valide(branche.intersection_tracking_id)
            or branche.intersection_tracking_id != intersection_tracking_id_valide
        ):
            rapport.ajouter_erreur(
                code="BRANCHE_INTERSECTION_INCOHERENTE",
                message=(
                    f"La branche à l'index {index} référence l'intersection_tracking_id "
                    f"'{branche.intersection_tracking_id}' au lieu de '{intersection_tracking_id_valide}'."
                ),
                champ=f"{prefixe_champ}.intersection_tracking_id",
            )
            aucune_erreur = False

        nom_branche = _normaliser_chaine(branche.nom)
        if not nom_branche:
            rapport.ajouter_erreur(
                code="NOM_BRANCHE_VIDE",
                message=f"Le nom de la branche à l'index {index} doit être une chaîne non vide.",
                champ=f"{prefixe_champ}.nom",
            )
            aucune_erreur = False

        if branche.angle_degres is not None and not _est_angle_valide(branche.angle_degres):
            rapport.ajouter_erreur(
                code="ANGLE_BRANCHE_INVALIDE",
                message=(
                    f"L'angle de la branche à l'index {index} ({branche.angle_degres!r}) "
                    f"doit être un nombre fini compris entre {ANGLE_MIN_DEGRES}° et {ANGLE_MAX_DEGRES}°."
                ),
                champ=f"{prefixe_champ}.angle_degres",
            )
            aucune_erreur = False

        return aucune_erreur, tid_b

    def _valider_voies(
        self,
        branches: object,
        tracking_ids_branches_valides: set[UUID],
        voies: object,
        rapport: RapportValidationIntersection,
    ) -> None:
        """
        Étape 3 (Active) : vérifie les voies indépendantes, leur rattachement par branche_tracking_id (UUID)
        à une branche valide, l'unicité globale de tracking_id (UUID),
        et l'unicité de (branche_tracking_id, direction, position).
        """
        rapport.enregistrer_etape("voies")

        compteur_voies_valides_par_branche: dict[UUID, int] = {
            tid_b: 0 for tid_b in tracking_ids_branches_valides
        }

        if not _est_sequence_objets(voies):
            rapport.ajouter_erreur(
                code="TYPE_COLLECTION_VOIES_INVALIDE",
                message="L'argument 'voies' doit être une séquence d'instances de Voie.",
                champ="voies",
            )
            self._signaler_branches_sans_voie_valide(
                branches=branches,
                tracking_ids_branches_valides=tracking_ids_branches_valides,
                compteur_voies_valides_par_branche=compteur_voies_valides_par_branche,
                rapport=rapport,
            )
            return

        occurrences_tracking_ids: Counter[UUID] = Counter()
        occurrences_positions: Counter[tuple[UUID, DirectionVoie, int]] = Counter()

        for item in voies:
            if isinstance(item, Voie):
                if _est_uuid_valide(item.tracking_id):
                    occurrences_tracking_ids[item.tracking_id] += 1

                if (
                    _est_uuid_valide(item.branche_tracking_id)
                    and item.branche_tracking_id in tracking_ids_branches_valides
                    and isinstance(item.direction, DirectionVoie)
                    and _est_position_voie_valide(item.position)
                ):
                    occurrences_positions[
                        (item.branche_tracking_id, item.direction, item.position)
                    ] += 1

        tracking_ids_vus: set[UUID] = set()
        positions_vues: set[tuple[UUID, DirectionVoie, int]] = set()

        for idx_voie, voie in enumerate(voies):
            self._valider_voie(
                voie=voie,
                index_voie=idx_voie,
                tracking_ids_branches_valides=tracking_ids_branches_valides,
                tracking_ids_vus=tracking_ids_vus,
                occurrences_tracking_ids=occurrences_tracking_ids,
                positions_vues=positions_vues,
                occurrences_positions=occurrences_positions,
                compteur_voies_valides_par_branche=compteur_voies_valides_par_branche,
                rapport=rapport,
            )

        self._signaler_branches_sans_voie_valide(
            branches=branches,
            tracking_ids_branches_valides=tracking_ids_branches_valides,
            compteur_voies_valides_par_branche=compteur_voies_valides_par_branche,
            rapport=rapport,
        )

    def _signaler_branches_sans_voie_valide(
        self,
        branches: object,
        tracking_ids_branches_valides: set[UUID],
        compteur_voies_valides_par_branche: dict[UUID, int],
        rapport: RapportValidationIntersection,
    ) -> None:
        """Signale toute branche valide qui ne possède aucune voie entièrement valide."""
        if not _est_sequence_objets(branches):
            return

        branches_deja_signalees: set[UUID] = set()

        for idx_branche, branche in enumerate(branches):
            if not isinstance(branche, Branche):
                continue
            tid_b = branche.tracking_id
            if (
                _est_uuid_valide(tid_b)
                and tid_b in tracking_ids_branches_valides
                and tid_b not in branches_deja_signalees
                and compteur_voies_valides_par_branche[tid_b] == 0
            ):
                branches_deja_signalees.add(tid_b)
                rapport.ajouter_erreur(
                    code="BRANCHE_SANS_VOIE",
                    message=f"La branche '{branche.nom}' doit posséder au moins une voie entièrement valide.",
                    champ=f"branches[{idx_branche}]",
                )

    def _valider_voie(
        self,
        voie: object,
        index_voie: int,
        tracking_ids_branches_valides: set[UUID],
        tracking_ids_vus: set[UUID],
        occurrences_tracking_ids: Counter[UUID],
        positions_vues: set[tuple[UUID, DirectionVoie, int]],
        occurrences_positions: Counter[tuple[UUID, DirectionVoie, int]],
        compteur_voies_valides_par_branche: dict[UUID, int],
        rapport: RapportValidationIntersection,
    ) -> None:
        """
        Vérifie les 7 conditions de validité d'une voie et n'incrémente le compteur de sa
        branche que si la voie est intégralement valide.
        """
        prefixe_champ_voie = f"voies[{index_voie}]"
        if not isinstance(voie, Voie):
            rapport.ajouter_erreur(
                code="TYPE_VOIE_INVALIDE",
                message=f"L'élément à l'index {index_voie} de 'voies' doit être une instance de Voie.",
                champ=prefixe_champ_voie,
            )
            return

        # 1 & 2. tracking_id valide (UUID) et globalement unique
        tracking_id_valide = _est_uuid_valide(voie.tracking_id)
        if not tracking_id_valide:
            rapport.ajouter_erreur(
                code="TRACKING_ID_VOIE_INVALIDE",
                message=f"La voie à l'index {index_voie} doit avoir un tracking_id UUID valide.",
                champ=f"{prefixe_champ_voie}.tracking_id",
            )
        elif voie.tracking_id in tracking_ids_vus:
            rapport.ajouter_erreur(
                code="TRACKING_ID_VOIE_DUPLIQUE",
                message=(
                    f"Le tracking_id '{voie.tracking_id}' est dupliqué "
                    "au sein de l'intersection."
                ),
                champ=f"{prefixe_champ_voie}.tracking_id",
            )
        else:
            tracking_ids_vus.add(voie.tracking_id)

        tracking_id_unique = (
            tracking_id_valide and occurrences_tracking_ids[voie.tracking_id] == 1
        )

        # Validation des identifiants techniques éventuels (id et branche_id)
        if not _est_id_technique_valide(voie.id):
            rapport.ajouter_erreur(
                code="ID_VOIE_INVALIDE",
                message=f"L'id technique de la voie à l'index {index_voie} doit être un entier positif ou None.",
                champ=f"{prefixe_champ_voie}.id",
            )

        if not _est_id_technique_valide(voie.branche_id):
            rapport.ajouter_erreur(
                code="ID_BRANCHE_INVALIDE",
                message=f"Le branche_id technique de la voie à l'index {index_voie} doit être un entier positif ou None.",
                champ=f"{prefixe_champ_voie}.branche_id",
            )

        # 3. Référence branche_tracking_id explicite (UUID) vers une branche valide
        branche_rattachee_valide = (
            _est_uuid_valide(voie.branche_tracking_id)
            and voie.branche_tracking_id in tracking_ids_branches_valides
        )
        if not branche_rattachee_valide:
            rapport.ajouter_erreur(
                code="VOIE_BRANCHE_INCONNUE",
                message=(
                    f"La voie à l'index {index_voie} référence une branche "
                    f"inconnue ou non valide '{voie.branche_tracking_id}'."
                ),
                champ=f"{prefixe_champ_voie}.branche_tracking_id",
            )

        # 4. Nom non vide
        nom_voie = _normaliser_chaine(voie.nom)
        nom_valide = bool(nom_voie)
        if not nom_valide:
            rapport.ajouter_erreur(
                code="NOM_VOIE_VIDE",
                message=f"Le nom de la voie à l'index {index_voie} doit être une chaîne non vide.",
                champ=f"{prefixe_champ_voie}.nom",
            )

        # 5. Direction valide
        direction_valide = isinstance(voie.direction, DirectionVoie)
        if not direction_valide:
            rapport.ajouter_erreur(
                code="DIRECTION_VOIE_INVALIDE",
                message=(
                    f"La direction de la voie à l'index {index_voie} est invalide "
                    "(attendu: DirectionVoie.ENTRANTE ou DirectionVoie.SORTANTE)."
                ),
                champ=f"{prefixe_champ_voie}.direction",
            )

        # 6. Position entière strictement positive (>= 1)
        position_valide = _est_position_voie_valide(voie.position)
        if not position_valide:
            rapport.ajouter_erreur(
                code="POSITION_VOIE_INVALIDE",
                message=(
                    f"La position de la voie à l'index {index_voie} ({voie.position!r}) "
                    "doit être un entier supérieur ou égal à 1."
                ),
                champ=f"{prefixe_champ_voie}.position",
            )

        # 7. Position non dupliquée pour le couple (branche_tracking_id, direction)
        position_unique = False
        if branche_rattachee_valide and direction_valide and position_valide:
            cle_position = (voie.branche_tracking_id, voie.direction, voie.position)
            if cle_position in positions_vues:
                rapport.ajouter_erreur(
                    code="POSITION_VOIE_DUPLIQUEE",
                    message=(
                        f"La position {voie.position} ({voie.direction.value}) est dupliquée "
                        f"sur la branche '{voie.branche_tracking_id}'."
                    ),
                    champ=f"{prefixe_champ_voie}.position",
                )
            else:
                positions_vues.add(cle_position)

            position_unique = occurrences_positions[cle_position] == 1

        # Comptabilisation stricte : la voie compte pour sa branche si tout est valide
        if (
            tracking_id_unique
            and branche_rattachee_valide
            and nom_valide
            and direction_valide
            and position_valide
            and position_unique
        ):
            compteur_voies_valides_par_branche[voie.branche_tracking_id] += 1


def _extraire_tracking_id_branche(branche_ou_tracking_id: Branche | UUID) -> UUID:
    """Extrait le tracking_id UUID d'une Branche ou retourne l'UUID directement."""
    if isinstance(branche_ou_tracking_id, Branche):
        return branche_ou_tracking_id.tracking_id
    if _est_uuid_valide(branche_ou_tracking_id):
        return branche_ou_tracking_id
    raise ValueError(
        "L'argument 'branche_ou_tracking_id' doit être une instance de Branche ou un UUID valide."
    )


def _filtrer_voies_par_branche_et_direction(
    branche_ou_tracking_id: Branche | UUID,
    voies: Sequence[Voie],
    direction: DirectionVoie,
) -> tuple[Voie, ...]:
    """
    Contrat déterministe de filtrage des voies par branche et direction :
    - `branche_ou_tracking_id` doit être une instance de Branche ou un UUID valide.
    - Ignore toute voie non valide ou qui ne correspond pas au tracking_id/direction.
    - Retourne les voies triées par position croissante puis par tracking_id.
    """
    tracking_id_branche = _extraire_tracking_id_branche(branche_ou_tracking_id)

    if not _est_sequence_objets(voies):
        raise ValueError("L'argument 'voies' doit être une séquence de voies.")

    voies_filtrees: list[Voie] = []
    for voie in voies:
        if not isinstance(voie, Voie):
            continue
        if (
            not _est_uuid_valide(voie.branche_tracking_id)
            or voie.branche_tracking_id != tracking_id_branche
            or not _normaliser_chaine(voie.nom)
            or voie.direction != direction
            or not _est_position_voie_valide(voie.position)
            or not _est_uuid_valide(voie.tracking_id)
        ):
            continue
        voies_filtrees.append(voie)

    voies_filtrees.sort(key=lambda v: (v.position, str(v.tracking_id)))
    return tuple(voies_filtrees)


def obtenir_voies_entrantes(
    branche_ou_tracking_id: Branche | UUID,
    voies: Sequence[Voie],
) -> tuple[Voie, ...]:
    """
    Retourne les voies entrantes (`DirectionVoie.ENTRANTE`) valides rattachées à la branche,
    triées par `position` croissante.
    """
    return _filtrer_voies_par_branche_et_direction(
        branche_ou_tracking_id=branche_ou_tracking_id,
        voies=voies,
        direction=DirectionVoie.ENTRANTE,
    )


def obtenir_voies_sortantes(
    branche_ou_tracking_id: Branche | UUID,
    voies: Sequence[Voie],
) -> tuple[Voie, ...]:
    """
    Retourne les voies sortantes (`DirectionVoie.SORTANTE`) valides rattachées à la branche,
    triées par `position` croissante.
    """
    return _filtrer_voies_par_branche_et_direction(
        branche_ou_tracking_id=branche_ou_tracking_id,
        voies=voies,
        direction=DirectionVoie.SORTANTE,
    )


def valider_intersection(
    intersection: Intersection,
    branches: Sequence[Branche] = (),
    voies: Sequence[Voie] = (),
    *,
    lever_exception: bool = False,
) -> RapportValidationIntersection:
    """Fonction utilitaire validant une intersection et ses entités associées."""
    rapport = ValidateurIntersection().valider(
        intersection=intersection,
        branches=branches,
        voies=voies,
    )
    if lever_exception:
        rapport.lever_si_invalide()
    return rapport
