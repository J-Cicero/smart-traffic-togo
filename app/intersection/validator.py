"""
Validateur de cohérence et de topologie pour les intersections.

Règles de validation :
- Identité : nom non vide, identifiant str non vide.
- Topologie : >= 3 branches valides rattachées par id_intersection, angles finis 0..360°.
- Voies : >= 1 voie entièrement valide par branche, unicité des id_voie,
  nom non vide, direction valide, position >= 1 et unicité par (id_branche, direction).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import TypeGuard

from app.intersection.entities import (
    Branche,
    DirectionVoie,
    Intersection,
    Voie,
)
from app.intersection.exceptions import ErreurValidationIntersection

NOMBRE_MIN_BRANCHES = 3
ANGLE_MIN_DEGRES = 0.0
ANGLE_MAX_DEGRES = 360.0


def _normaliser_chaine(valeur: object) -> str | None:
    """Extrait une chaîne nettoyée si et seulement si valeur est de type str."""
    if not isinstance(valeur, str):
        return None
    return valeur.strip()


def _est_sequence_objets(valeur: object) -> TypeGuard[Sequence[object]]:
    """Vérifie que valeur est une séquence itérable d'objets (hors str/bytes)."""
    return isinstance(valeur, Sequence) and not isinstance(
        valeur, (str, bytes, bytearray)
    )


def _est_angle_valide(angle: object) -> bool:
    """Vérifie qu'un angle est un nombre réel fini compris entre 0.0 et 360.0."""
    if isinstance(angle, bool) or not isinstance(angle, (int, float)):
        return False
    valeur = float(angle)
    if not math.isfinite(valeur):
        return False
    return ANGLE_MIN_DEGRES <= valeur <= ANGLE_MAX_DEGRES


def _est_position_voie_valide(position: object) -> TypeGuard[int]:
    """Vérifie que la position d'une voie est un entier strictement positif (>= 1)."""
    return (
        isinstance(position, int)
        and not isinstance(position, bool)
        and position >= 1
    )


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
        return tuple(self._anomalies)

    @property
    def erreurs(self) -> tuple[AnomalieValidationIntersection, ...]:
        return tuple(
            anomalie
            for anomalie in self._anomalies
            if anomalie.gravite == GraviteValidation.ERREUR
        )

    @property
    def avertissements(self) -> tuple[AnomalieValidationIntersection, ...]:
        return tuple(
            anomalie
            for anomalie in self._anomalies
            if anomalie.gravite == GraviteValidation.AVERTISSEMENT
        )

    @property
    def etapes_executees(self) -> tuple[str, ...]:
        return tuple(self._etapes_executees)

    @property
    def est_valide(self) -> bool:
        return len(self.erreurs) == 0

    def enregistrer_etape(self, nom_etape: str) -> None:
        self._etapes_executees.append(nom_etape)

    def ajouter_erreur(
        self,
        code: str,
        message: str,
        champ: str | None = None,
    ) -> None:
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
        self._anomalies.append(
            AnomalieValidationIntersection(
                code=code,
                message=message,
                gravite=GraviteValidation.AVERTISSEMENT,
                champ=champ,
            )
        )

    def lever_si_invalide(self) -> None:
        if not self.est_valide:
            details = [f"[{e.code}] {e.message}" for e in self.erreurs]
            raise ErreurValidationIntersection(
                f"Validation de l'intersection échouée ({len(self.erreurs)} erreur(s)):\n"
                + "\n".join(details),
                anomalies=self.anomalies,
            )


class ValidateurIntersection:
    """Validateur de cohérence d'intersection pour entités indépendantes."""

    def valider(
        self,
        intersection: object,
        branches: object = (),
        voies: object = (),
    ) -> RapportValidationIntersection:
        rapport = RapportValidationIntersection()

        intersection_id_valide = self._valider_identite(intersection, rapport)

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

        ids_branches_valides = self._valider_topologie(
            intersection_id_valide=intersection_id_valide,
            branches=branches,
            rapport=rapport,
        )

        self._valider_voies(
            branches=branches,
            ids_branches_valides=ids_branches_valides,
            voies=voies,
            rapport=rapport,
        )

        return rapport

    def _valider_identite(
        self,
        intersection: object,
        rapport: RapportValidationIntersection,
    ) -> str | None:
        rapport.enregistrer_etape("identite")

        if not isinstance(intersection, Intersection):
            rapport.ajouter_erreur(
                code="TYPE_INTERSECTION_INVALIDE",
                message="L'argument 'intersection' doit être une instance de Intersection.",
                champ="intersection",
            )
            return None

        id_valide: str | None = None
        if not isinstance(intersection.id_intersection, str):
            rapport.ajouter_erreur(
                code="ID_INTERSECTION_INVALIDE",
                message="L'identifiant de l'intersection doit être une chaîne de caractères.",
                champ="id_intersection",
            )
        elif not intersection.id_intersection.strip():
            rapport.ajouter_erreur(
                code="ID_INTERSECTION_VIDE",
                message="L'identifiant de l'intersection ne peut pas être vide.",
                champ="id_intersection",
            )
        else:
            id_valide = intersection.id_intersection.strip()

        nom_normalise = _normaliser_chaine(intersection.nom)
        if not isinstance(intersection.nom, str):
            rapport.ajouter_erreur(
                code="NOM_INTERSECTION_INVALIDE",
                message="Le nom de l'intersection doit être une chaîne de caractères.",
                champ="nom",
            )
        elif not nom_normalise:
            rapport.ajouter_erreur(
                code="NOM_INTERSECTION_VIDE",
                message="Le nom de l'intersection doit être une chaîne non vide.",
                champ="nom",
            )

        description_normalisee = _normaliser_chaine(intersection.description)
        if not isinstance(intersection.description, str):
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
        return id_valide

    def _valider_topologie(
        self,
        intersection_id_valide: str | None,
        branches: object,
        rapport: RapportValidationIntersection,
    ) -> set[str]:
        rapport.enregistrer_etape("topologie")

        if not _est_sequence_objets(branches):
            rapport.ajouter_erreur(
                code="TYPE_COLLECTION_BRANCHES_INVALIDE",
                message="L'argument 'branches' doit être une séquence d'instances de Branche.",
                champ="branches",
            )
            return set()

        ids_vus: set[str] = set()
        ids_dupliques: set[str] = set()
        ids_candidats_valides: set[str] = set()

        for idx, branche in enumerate(branches):
            est_branche_valide, id_b = self._valider_branche(
                branche=branche,
                index=idx,
                intersection_id_valide=intersection_id_valide,
                ids_vus=ids_vus,
                ids_dupliques=ids_dupliques,
                rapport=rapport,
            )
            if est_branche_valide and id_b is not None:
                ids_candidats_valides.add(id_b)

        ids_branches_valides = ids_candidats_valides - ids_dupliques

        if len(ids_branches_valides) < NOMBRE_MIN_BRANCHES:
            rapport.ajouter_erreur(
                code="NOMBRE_BRANCHES_INSUFFISANT",
                message=(
                    f"Une intersection doit posséder au moins {NOMBRE_MIN_BRANCHES} branches "
                    f"valides rattachées ({len(ids_branches_valides)} valide(s) sur {len(branches)} fournie(s))."
                ),
                champ="branches",
            )

        return ids_branches_valides

    def _valider_branche(
        self,
        branche: object,
        index: int,
        intersection_id_valide: str | None,
        ids_vus: set[str],
        ids_dupliques: set[str],
        rapport: RapportValidationIntersection,
    ) -> tuple[bool, str | None]:
        prefixe_champ = f"branches[{index}]"
        if not isinstance(branche, Branche):
            rapport.ajouter_erreur(
                code="TYPE_BRANCHE_INVALIDE",
                message=f"L'élément à l'index {index} de 'branches' doit être une instance de Branche.",
                champ=prefixe_champ,
            )
            return False, None

        aucune_erreur = True
        id_b: str | None = None

        if not isinstance(branche.id_branche, str):
            rapport.ajouter_erreur(
                code="ID_BRANCHE_INVALIDE",
                message=f"L'id_branche de la branche à l'index {index} doit être une chaîne de caractères.",
                champ=f"{prefixe_champ}.id_branche",
            )
            aucune_erreur = False
        elif not branche.id_branche.strip():
            rapport.ajouter_erreur(
                code="ID_BRANCHE_VIDE",
                message=f"L'id_branche de la branche à l'index {index} ne peut pas être vide.",
                champ=f"{prefixe_champ}.id_branche",
            )
            aucune_erreur = False
        else:
            id_b = branche.id_branche.strip()
            if id_b in ids_vus:
                ids_dupliques.add(id_b)
                rapport.ajouter_erreur(
                    code="ID_BRANCHE_DUPLIQUE",
                    message=f"L'id_branche '{id_b}' est dupliqué au sein de l'intersection.",
                    champ=f"{prefixe_champ}.id_branche",
                )
                aucune_erreur = False
            else:
                ids_vus.add(id_b)

        if (
            intersection_id_valide is None
            or not isinstance(branche.id_intersection, str)
            or branche.id_intersection.strip() != intersection_id_valide
        ):
            rapport.ajouter_erreur(
                code="BRANCHE_INTERSECTION_INCOHERENTE",
                message=(
                    f"La branche à l'index {index} référence l'intersection "
                    f"'{branche.id_intersection}' au lieu de '{intersection_id_valide}'."
                ),
                champ=f"{prefixe_champ}.id_intersection",
            )
            aucune_erreur = False

        nom_branche = _normaliser_chaine(branche.nom)
        if not isinstance(branche.nom, str):
            rapport.ajouter_erreur(
                code="NOM_BRANCHE_INVALIDE",
                message=f"Le nom de la branche à l'index {index} doit être une chaîne de caractères.",
                champ=f"{prefixe_champ}.nom",
            )
            aucune_erreur = False
        elif not nom_branche:
            rapport.ajouter_erreur(
                code="NOM_BRANCHE_VIDE",
                message=f"Le nom de la branche à l'index {index} doit être une chaîne non vide.",
                champ=f"{prefixe_champ}.nom",
            )
            aucune_erreur = False

        if not _est_angle_valide(branche.angle_degres):
            rapport.ajouter_erreur(
                code="ANGLE_BRANCHE_INVALIDE",
                message=(
                    f"L'angle de la branche à l'index {index} ({branche.angle_degres!r}) "
                    f"doit être un nombre fini compris entre {ANGLE_MIN_DEGRES}° et {ANGLE_MAX_DEGRES}°."
                ),
                champ=f"{prefixe_champ}.angle_degres",
            )
            aucune_erreur = False

        return aucune_erreur, id_b

    def _valider_voies(
        self,
        branches: object,
        ids_branches_valides: set[str],
        voies: object,
        rapport: RapportValidationIntersection,
    ) -> None:
        rapport.enregistrer_etape("voies")

        compteur_voies_valides_par_branche: dict[str, int] = {
            id_b: 0 for id_b in ids_branches_valides
        }

        if not _est_sequence_objets(voies):
            rapport.ajouter_erreur(
                code="TYPE_COLLECTION_VOIES_INVALIDE",
                message="L'argument 'voies' doit être une séquence d'instances de Voie.",
                champ="voies",
            )
            self._signaler_branches_sans_voie_valide(
                branches=branches,
                ids_branches_valides=ids_branches_valides,
                compteur_voies_valides_par_branche=compteur_voies_valides_par_branche,
                rapport=rapport,
            )
            return

        occurrences_ids_voies: Counter[str] = Counter()
        occurrences_positions: Counter[tuple[str, DirectionVoie, int]] = Counter()

        for item in voies:
            if isinstance(item, Voie):
                if isinstance(item.id_voie, str) and item.id_voie.strip():
                    occurrences_ids_voies[item.id_voie.strip()] += 1

                if (
                    isinstance(item.id_branche, str)
                    and item.id_branche.strip() in ids_branches_valides
                    and isinstance(item.direction, DirectionVoie)
                    and _est_position_voie_valide(item.position)
                ):
                    occurrences_positions[
                        (item.id_branche.strip(), item.direction, item.position)
                    ] += 1

        ids_voies_vus: set[str] = set()
        positions_vues: set[tuple[str, DirectionVoie, int]] = set()

        for idx_voie, voie in enumerate(voies):
            self._valider_voie(
                voie=voie,
                index_voie=idx_voie,
                ids_branches_valides=ids_branches_valides,
                ids_voies_vus=ids_voies_vus,
                occurrences_ids_voies=occurrences_ids_voies,
                positions_vues=positions_vues,
                occurrences_positions=occurrences_positions,
                compteur_voies_valides_par_branche=compteur_voies_valides_par_branche,
                rapport=rapport,
            )

        self._signaler_branches_sans_voie_valide(
            branches=branches,
            ids_branches_valides=ids_branches_valides,
            compteur_voies_valides_par_branche=compteur_voies_valides_par_branche,
            rapport=rapport,
        )

    def _signaler_branches_sans_voie_valide(
        self,
        branches: object,
        ids_branches_valides: set[str],
        compteur_voies_valides_par_branche: dict[str, int],
        rapport: RapportValidationIntersection,
    ) -> None:
        if not _est_sequence_objets(branches):
            return

        branches_deja_signalees: set[str] = set()

        for idx_branche, branche in enumerate(branches):
            if not isinstance(branche, Branche):
                continue
            id_b = getattr(branche, "id_branche", None)
            if (
                isinstance(id_b, str)
                and id_b.strip() in ids_branches_valides
                and id_b.strip() not in branches_deja_signalees
                and compteur_voies_valides_par_branche[id_b.strip()] == 0
            ):
                branches_deja_signalees.add(id_b.strip())
                rapport.ajouter_erreur(
                    code="BRANCHE_SANS_VOIE",
                    message=f"La branche '{branche.nom}' doit posséder au moins une voie entièrement valide.",
                    champ=f"branches[{idx_branche}]",
                )

    def _valider_voie(
        self,
        voie: object,
        index_voie: int,
        ids_branches_valides: set[str],
        ids_voies_vus: set[str],
        occurrences_ids_voies: Counter[str],
        positions_vues: set[tuple[str, DirectionVoie, int]],
        occurrences_positions: Counter[tuple[str, DirectionVoie, int]],
        compteur_voies_valides_par_branche: dict[str, int],
        rapport: RapportValidationIntersection,
    ) -> None:
        prefixe_champ_voie = f"voies[{index_voie}]"
        if not isinstance(voie, Voie):
            rapport.ajouter_erreur(
                code="TYPE_VOIE_INVALIDE",
                message=f"L'élément à l'index {index_voie} de 'voies' doit être une instance de Voie.",
                champ=prefixe_champ_voie,
            )
            return

        id_voie_valide = False
        id_v: str | None = None
        if not isinstance(voie.id_voie, str):
            rapport.ajouter_erreur(
                code="ID_VOIE_INVALIDE",
                message=f"L'id_voie de la voie à l'index {index_voie} doit être une chaîne de caractères.",
                champ=f"{prefixe_champ_voie}.id_voie",
            )
        elif not voie.id_voie.strip():
            rapport.ajouter_erreur(
                code="ID_VOIE_VIDE",
                message=f"L'id_voie de la voie à l'index {index_voie} ne peut pas être vide.",
                champ=f"{prefixe_champ_voie}.id_voie",
            )
        else:
            id_v = voie.id_voie.strip()
            if id_v in ids_voies_vus:
                rapport.ajouter_erreur(
                    code="ID_VOIE_DUPLIQUE",
                    message=f"L'id_voie '{id_v}' est dupliqué au sein de l'intersection.",
                    champ=f"{prefixe_champ_voie}.id_voie",
                )
            else:
                ids_voies_vus.add(id_v)
                id_voie_valide = True

        id_voie_unique = id_voie_valide and (id_v is not None and occurrences_ids_voies[id_v] == 1)

        id_b_valide = (
            isinstance(voie.id_branche, str)
            and voie.id_branche.strip() in ids_branches_valides
        )
        if not id_b_valide:
            rapport.ajouter_erreur(
                code="VOIE_BRANCHE_INCONNUE",
                message=(
                    f"La voie à l'index {index_voie} référence une branche "
                    f"inconnue ou non valide '{voie.id_branche}'."
                ),
                champ=f"{prefixe_champ_voie}.id_branche",
            )

        nom_voie = _normaliser_chaine(voie.nom)
        if not isinstance(voie.nom, str):
            rapport.ajouter_erreur(
                code="NOM_VOIE_INVALIDE",
                message=f"Le nom de la voie à l'index {index_voie} doit être une chaîne de caractères.",
                champ=f"{prefixe_champ_voie}.nom",
            )
            nom_valide = False
        elif not nom_voie:
            rapport.ajouter_erreur(
                code="NOM_VOIE_VIDE",
                message=f"Le nom de la voie à l'index {index_voie} doit être une chaîne non vide.",
                champ=f"{prefixe_champ_voie}.nom",
            )
            nom_valide = False
        else:
            nom_valide = True

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

        position_unique = False
        if id_b_valide and direction_valide and position_valide:
            cle_position = (voie.id_branche.strip(), voie.direction, voie.position)
            if cle_position in positions_vues:
                rapport.ajouter_erreur(
                    code="POSITION_VOIE_DUPLIQUEE",
                    message=(
                        f"La position {voie.position} ({voie.direction.value}) est dupliquée "
                        f"sur la branche '{voie.id_branche}'."
                    ),
                    champ=f"{prefixe_champ_voie}.position",
                )
            else:
                positions_vues.add(cle_position)

            position_unique = occurrences_positions[cle_position] == 1

        if (
            id_voie_unique
            and id_b_valide
            and nom_valide
            and direction_valide
            and position_valide
            and position_unique
        ):
            compteur_voies_valides_par_branche[voie.id_branche.strip()] += 1


def _extraire_id_branche(branche_ou_id: Branche | str) -> str:
    """Extrait l'id_branche d'une Branche ou retourne la chaîne nettoyée."""
    if isinstance(branche_ou_id, Branche):
        return branche_ou_id.id_branche.strip()
    if isinstance(branche_ou_id, str) and branche_ou_id.strip():
        return branche_ou_id.strip()
    raise ValueError(
        "L'argument 'branche_ou_id' doit être une instance de Branche ou un identifiant non vide."
    )


def _filtrer_voies_par_branche_et_direction(
    branche_ou_id: Branche | str,
    voies: Sequence[Voie],
    direction: DirectionVoie,
) -> tuple[Voie, ...]:
    id_branche = _extraire_id_branche(branche_ou_id)

    if not _est_sequence_objets(voies):
        raise ValueError("L'argument 'voies' doit être une séquence de voies.")

    voies_filtrees: list[Voie] = []
    for voie in voies:
        if not isinstance(voie, Voie):
            continue
        if (
            not isinstance(voie.id_branche, str)
            or voie.id_branche.strip() != id_branche
            or not _normaliser_chaine(voie.nom)
            or voie.direction != direction
            or not _est_position_voie_valide(voie.position)
            or not isinstance(voie.id_voie, str)
            or not voie.id_voie.strip()
        ):
            continue
        voies_filtrees.append(voie)

    voies_filtrees.sort(key=lambda v: (v.position, v.id_voie))
    return tuple(voies_filtrees)


def obtenir_voies_entrantes(
    branche_ou_id: Branche | str,
    voies: Sequence[Voie],
) -> tuple[Voie, ...]:
    return _filtrer_voies_par_branche_et_direction(
        branche_ou_id=branche_ou_id,
        voies=voies,
        direction=DirectionVoie.ENTRANTE,
    )


def obtenir_voies_sortantes(
    branche_ou_id: Branche | str,
    voies: Sequence[Voie],
) -> tuple[Voie, ...]:
    return _filtrer_voies_par_branche_et_direction(
        branche_ou_id=branche_ou_id,
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
    rapport = ValidateurIntersection().valider(
        intersection=intersection,
        branches=branches,
        voies=voies,
    )
    if lever_exception:
        rapport.lever_si_invalide()
    return rapport
