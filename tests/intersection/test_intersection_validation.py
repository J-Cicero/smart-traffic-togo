"""Tests unitaires pour les entités topologiques avec double identification (id technique + tracking_id UUID)."""

from __future__ import annotations

from collections.abc import Sequence
import math
from uuid import UUID, uuid4

import pytest

from app.intersection.exceptions import ErreurValidationIntersection
from app.intersection.entities import (
    Branche,
    DirectionVoie,
    Intersection,
    Voie,
)
from app.intersection.validator import (
    AnomalieValidationIntersection,
    GraviteValidation,
    RapportValidationIntersection,
    ValidateurIntersection,
    obtenir_voies_entrantes,
    obtenir_voies_sortantes,
    valider_intersection,
)


def _creer_branche_et_voies(
    intersection: Intersection,
    nom_branche: str,
    angle_degres: float | None = None,
) -> tuple[Branche, tuple[Voie, Voie]]:
    """Construit une branche reliée par son intersection_tracking_id et deux voies reliées par leur branche_tracking_id."""
    branche = Branche(
        nom=nom_branche,
        intersection_tracking_id=intersection.tracking_id,
        intersection_id=intersection.id,
        angle_degres=angle_degres,
    )
    voies = (
        Voie(
            nom=f"Voie entrante {nom_branche}",
            branche_tracking_id=branche.tracking_id,
            branche_id=branche.id,
            direction=DirectionVoie.ENTRANTE,
            position=1,
        ),
        Voie(
            nom=f"Voie sortante {nom_branche}",
            branche_tracking_id=branche.tracking_id,
            branche_id=branche.id,
            direction=DirectionVoie.SORTANTE,
            position=1,
        ),
    )
    return branche, voies


def _assembler_topologie(
    intersection: Intersection,
    specs_branches: Sequence[tuple[str, float | None]],
) -> tuple[tuple[Branche, ...], tuple[Voie, ...]]:
    branches: list[Branche] = []
    voies: list[Voie] = []
    for nom_b, angle_b in specs_branches:
        branche, voies_b = _creer_branche_et_voies(intersection, nom_b, angle_b)
        branches.append(branche)
        voies.extend(voies_b)
    return tuple(branches), tuple(voies)


# ---------------------------------------------------------------------------
# Architecture des entités : double identifiant (id + tracking_id)
# ---------------------------------------------------------------------------


def test_entites_possedent_id_et_tracking_id_et_references_independantes() -> None:
    intersection = Intersection(
        nom="Carrefour Indépendant",
        description="Double identification id + tracking_id",
        id=1,
    )
    branche = Branche(
        nom="Branche Nord",
        intersection_tracking_id=intersection.tracking_id,
        intersection_id=intersection.id,
        angle_degres=0.0,
        id=10,
    )
    voie = Voie(
        nom="Voie Nord 1",
        branche_tracking_id=branche.tracking_id,
        branche_id=branche.id,
        direction=DirectionVoie.ENTRANTE,
        position=1,
        id=100,
    )

    # Identifiant technique et tracking_id UUID sur Intersection
    assert intersection.id == 1
    assert isinstance(intersection.tracking_id, UUID)

    # Identifiant technique et tracking_id UUID sur Branche
    assert branche.id == 10
    assert isinstance(branche.tracking_id, UUID)
    assert branche.intersection_id == 1
    assert branche.intersection_tracking_id == intersection.tracking_id

    # Identifiant technique et tracking_id UUID sur Voie
    assert voie.id == 100
    assert isinstance(voie.tracking_id, UUID)
    assert voie.branche_id == 10
    assert voie.branche_tracking_id == branche.tracking_id

    # Absence stricte de collections imbriquées (pas de OneToMany / ManyToMany)
    assert not hasattr(intersection, "branches")
    assert not hasattr(branche, "voies")

    # Absence stricte d'objets imbriqués directs
    assert not hasattr(branche, "intersection")
    assert not hasattr(voie, "branche")


def test_tracking_id_invalide_est_rejete() -> None:
    intersection = Intersection(
        nom="Carrefour Mauvais UUID",
        tracking_id="pas_un_uuid",  # type: ignore[arg-type]
    )
    branches, voies = _assembler_topologie(
        intersection,
        (
            ("Nord", 0.0),
            ("Sud", 180.0),
            ("Est", 90.0),
        ),
    )

    rapport = valider_intersection(intersection, branches, voies)
    assert rapport.est_valide is False
    codes_erreur = {anomalie.code for anomalie in rapport.erreurs}
    assert "TRACKING_ID_INTERSECTION_INVALIDE" in codes_erreur


def test_tracking_id_branche_et_voie_non_uuid_sont_rejetes() -> None:
    intersection = Intersection(nom="Carrefour Cible")
    b1 = Branche(
        nom="Nord",
        intersection_tracking_id=intersection.tracking_id,
        tracking_id=12345,  # type: ignore[arg-type]
    )
    v1 = Voie(
        nom="Voie Nord 1",
        branche_tracking_id=b1.tracking_id,
        direction=DirectionVoie.ENTRANTE,
        position=1,
        tracking_id="non-uuid",  # type: ignore[arg-type]
    )

    rapport = valider_intersection(intersection, (b1,), (v1,))
    assert rapport.est_valide is False
    codes_erreur = {anomalie.code for anomalie in rapport.erreurs}
    assert "TRACKING_ID_BRANCHE_INVALIDE" in codes_erreur
    assert "TRACKING_ID_VOIE_INVALIDE" in codes_erreur


@pytest.mark.parametrize("mauvais_id", [-1, 0, "abc", True, [1]])
def test_id_technique_invalide_est_rejete(mauvais_id: object) -> None:
    intersection = Intersection(
        nom="Carrefour ID Invalide",
        id=mauvais_id,  # type: ignore[arg-type]
    )
    branche = Branche(
        nom="Nord",
        intersection_tracking_id=intersection.tracking_id,
        id=mauvais_id,  # type: ignore[arg-type]
    )
    voie = Voie(
        nom="Voie 1",
        branche_tracking_id=branche.tracking_id,
        id=mauvais_id,  # type: ignore[arg-type]
    )

    rapport = valider_intersection(intersection, (branche,), (voie,))
    assert rapport.est_valide is False
    codes_erreur = {anomalie.code for anomalie in rapport.erreurs}
    assert "ID_INTERSECTION_INVALIDE" in codes_erreur
    assert "ID_BRANCHE_INVALIDE" in codes_erreur
    assert "ID_VOIE_INVALIDE" in codes_erreur


# ---------------------------------------------------------------------------
# Intersections valides à 3, 4 et 5 branches + voies ENTRANTE/SORTANTE
# ---------------------------------------------------------------------------


def test_intersection_valide_trois_branches() -> None:
    intersection = Intersection(
        nom="Carrefour en T - Boulevard du Mono",
        description="Intersection à 3 branches",
        id=1,
    )
    branches, voies = _assembler_topologie(
        intersection,
        (
            ("Branche Nord", 0.0),
            ("Branche Sud", 180.0),
            ("Branche Est", 90.0),
        ),
    )

    rapport = valider_intersection(intersection, branches, voies)
    assert rapport.est_valide is True
    assert len(rapport.erreurs) == 0
    assert rapport.etapes_executees == ("identite", "topologie", "voies")


def test_intersection_valide_quatre_branches() -> None:
    intersection = Intersection(
        nom="Carrefour Dékon",
        description="Intersection urbaine à 4 branches",
    )
    branches, voies = _assembler_topologie(
        intersection,
        (
            ("Nord", 0.0),
            ("Est", 90.0),
            ("Sud", 180.0),
            ("Ouest", 270.0),
        ),
    )

    rapport = valider_intersection(intersection, branches, voies)
    assert rapport.est_valide is True
    assert len(rapport.erreurs) == 0
    assert len(branches) == 4


def test_intersection_valide_cinq_branches() -> None:
    intersection = Intersection(
        nom="Rond-Point GTA (5 branches)",
        description="Intersection asymétrique à 5 branches",
    )
    branches, voies = _assembler_topologie(
        intersection,
        (
            ("Boulevard Nord", 0.0),
            ("Avenue Nord-Est", 65.0),
            ("Avenue Sud-Est", 140.0),
            ("Boulevard Sud-Ouest", 215.0),
            ("Rue Nord-Ouest", 305.0),
        ),
    )

    rapport = valider_intersection(intersection, branches, voies)
    assert rapport.est_valide is True
    assert len(rapport.erreurs) == 0
    assert len(branches) == 5


def test_intersection_valide_distingue_voies_entrantes_et_sortantes() -> None:
    intersection = Intersection(
        nom="Carrefour Aéroport",
        description="Test distinction voies entrantes et sortantes par service",
    )
    branches_autres, voies_autres = _assembler_topologie(
        intersection,
        (
            ("Sud", 180.0),
            ("Ouest", 270.0),
        ),
    )
    branche_nord = Branche(
        nom="Boulevard Nord",
        intersection_tracking_id=intersection.tracking_id,
        angle_degres=0.0,
    )
    voies_nord = (
        Voie(
            nom="Entrée Nord Gauche",
            branche_tracking_id=branche_nord.tracking_id,
            direction=DirectionVoie.ENTRANTE,
            position=2,
        ),
        Voie(
            nom="Entrée Nord Droite",
            branche_tracking_id=branche_nord.tracking_id,
            direction=DirectionVoie.ENTRANTE,
            position=1,
        ),
        Voie(
            nom="Sortie Nord",
            branche_tracking_id=branche_nord.tracking_id,
            direction=DirectionVoie.SORTANTE,
            position=1,
        ),
    )

    toutes_branches = (branche_nord, *branches_autres)
    toutes_voies = (*voies_nord, *voies_autres)

    rapport = valider_intersection(intersection, toutes_branches, toutes_voies)
    assert rapport.est_valide is True

    # Test avec instance de Branche ET avec UUID tracking_id
    entrantes_nord = obtenir_voies_entrantes(branche_nord, toutes_voies)
    sortantes_nord = obtenir_voies_sortantes(branche_nord.tracking_id, toutes_voies)

    assert len(entrantes_nord) == 2
    assert len(sortantes_nord) == 1
    assert [v.nom for v in entrantes_nord] == ["Entrée Nord Droite", "Entrée Nord Gauche"]
    assert sortantes_nord[0].nom == "Sortie Nord"


# ---------------------------------------------------------------------------
# Comptabilisation stricte des voies et détection des doublons
# ---------------------------------------------------------------------------


def test_branche_avec_uniquement_des_voies_invalides_est_signalee_sans_voie() -> None:
    intersection = Intersection(nom="Carrefour Test", description="Branche Est sans voie valide")
    branches_valides, voies_valides = _assembler_topologie(
        intersection,
        (
            ("Nord", 0.0),
            ("Sud", 180.0),
        ),
    )
    branche_est = Branche(
        nom="Est",
        intersection_tracking_id=intersection.tracking_id,
        angle_degres=90.0,
    )
    voies_est_invalides = (
        Voie(nom="", branche_tracking_id=branche_est.tracking_id, direction=DirectionVoie.ENTRANTE, position=1),
        Voie(nom="Voie 2", branche_tracking_id=branche_est.tracking_id, direction=DirectionVoie.ENTRANTE, position=0),
        Voie(nom="Voie 3", branche_tracking_id=branche_est.tracking_id, direction="MAUVAISE_DIR", position=1),  # type: ignore[arg-type]
    )

    rapport = valider_intersection(
        intersection,
        (*branches_valides, branche_est),
        (*voies_valides, *voies_est_invalides),
    )
    assert rapport.est_valide is False
    codes_erreur = {anomalie.code for anomalie in rapport.erreurs}
    assert "NOM_VOIE_VIDE" in codes_erreur
    assert "POSITION_VOIE_INVALIDE" in codes_erreur
    assert "DIRECTION_VOIE_INVALIDE" in codes_erreur
    assert "BRANCHE_SANS_VOIE" in codes_erreur


def test_branche_avec_une_voie_valide_et_une_voie_invalide_n_est_pas_sans_voie() -> None:
    intersection = Intersection(nom="Carrefour Mixte")
    branches_valides, voies_valides = _assembler_topologie(
        intersection,
        (
            ("Nord", 0.0),
            ("Sud", 180.0),
        ),
    )
    branche_est = Branche(
        nom="Est",
        intersection_tracking_id=intersection.tracking_id,
        angle_degres=90.0,
    )
    voie_valide = Voie(
        nom="Voie Valide",
        branche_tracking_id=branche_est.tracking_id,
        direction=DirectionVoie.ENTRANTE,
        position=1,
    )
    voie_invalide = Voie(
        nom="Voie Invalide",
        branche_tracking_id=branche_est.tracking_id,
        direction=DirectionVoie.SORTANTE,
        position=-1,
    )

    rapport = valider_intersection(
        intersection,
        (*branches_valides, branche_est),
        (*voies_valides, voie_valide, voie_invalide),
    )
    assert rapport.est_valide is False
    codes_erreur = {anomalie.code for anomalie in rapport.erreurs}
    assert "POSITION_VOIE_INVALIDE" in codes_erreur
    assert "BRANCHE_SANS_VOIE" not in codes_erreur


def test_deux_voies_avec_meme_tracking_id_ne_rendent_pas_leur_branche_valide() -> None:
    intersection = Intersection(nom="Carrefour Collision UUID")
    branches_valides, voies_valides = _assembler_topologie(
        intersection,
        (
            ("Nord", 0.0),
            ("Sud", 180.0),
        ),
    )
    branche_est = Branche(
        nom="Est",
        intersection_tracking_id=intersection.tracking_id,
        angle_degres=90.0,
    )
    collision_uuid = uuid4()
    voies_est_dupliquees = (
        Voie(
            nom="Entrée Est",
            branche_tracking_id=branche_est.tracking_id,
            direction=DirectionVoie.ENTRANTE,
            position=1,
            tracking_id=collision_uuid,
        ),
        Voie(
            nom="Sortie Est",
            branche_tracking_id=branche_est.tracking_id,
            direction=DirectionVoie.SORTANTE,
            position=1,
            tracking_id=collision_uuid,
        ),
    )

    rapport = valider_intersection(
        intersection,
        (*branches_valides, branche_est),
        (*voies_valides, *voies_est_dupliquees),
    )
    assert rapport.est_valide is False
    codes_erreur = {anomalie.code for anomalie in rapport.erreurs}
    assert "TRACKING_ID_VOIE_DUPLIQUE" in codes_erreur
    assert "BRANCHE_SANS_VOIE" in codes_erreur


def test_deux_voies_meme_position_et_meme_direction_ne_rendent_pas_branche_valide() -> None:
    intersection = Intersection(nom="Carrefour Collision Position")
    branches_valides, voies_valides = _assembler_topologie(
        intersection,
        (
            ("Nord", 0.0),
            ("Sud", 180.0),
        ),
    )
    branche_est = Branche(
        nom="Est",
        intersection_tracking_id=intersection.tracking_id,
        angle_degres=90.0,
    )
    voies_est = (
        Voie(
            nom="Entrée A",
            branche_tracking_id=branche_est.tracking_id,
            direction=DirectionVoie.ENTRANTE,
            position=1,
        ),
        Voie(
            nom="Entrée B",
            branche_tracking_id=branche_est.tracking_id,
            direction=DirectionVoie.ENTRANTE,
            position=1,
        ),
    )

    rapport = valider_intersection(
        intersection,
        (*branches_valides, branche_est),
        (*voies_valides, *voies_est),
    )
    assert rapport.est_valide is False
    codes_erreur = {anomalie.code for anomalie in rapport.erreurs}
    assert "POSITION_VOIE_DUPLIQUEE" in codes_erreur
    assert "BRANCHE_SANS_VOIE" in codes_erreur


def test_deux_voies_meme_position_mais_directions_differentes_sont_valides() -> None:
    intersection = Intersection(nom="Carrefour Directions Différentes")
    branches_autres, voies_autres = _assembler_topologie(
        intersection,
        (
            ("Nord", 0.0),
            ("Sud", 180.0),
        ),
    )
    branche_est = Branche(
        nom="Est",
        intersection_tracking_id=intersection.tracking_id,
        angle_degres=90.0,
    )
    voies_est = (
        Voie(
            nom="Entrée 1",
            branche_tracking_id=branche_est.tracking_id,
            direction=DirectionVoie.ENTRANTE,
            position=1,
        ),
        Voie(
            nom="Sortie 1",
            branche_tracking_id=branche_est.tracking_id,
            direction=DirectionVoie.SORTANTE,
            position=1,
        ),
    )

    rapport = valider_intersection(
        intersection,
        (*branches_autres, branche_est),
        (*voies_autres, *voies_est),
    )
    assert rapport.est_valide is True
    assert len(rapport.erreurs) == 0


# ---------------------------------------------------------------------------
# Vérification des références d'identifiants (intersection_tracking_id & branche_tracking_id)
# ---------------------------------------------------------------------------


def test_branche_rattachee_a_autre_intersection_ne_valide_pas_ses_voies() -> None:
    intersection_cible = Intersection(nom="Carrefour Cible")
    autre_intersection = Intersection(nom="Autre Carrefour")

    branches_valides, voies_valides = _assembler_topologie(
        intersection_cible,
        (
            ("Nord", 0.0),
            ("Sud", 180.0),
        ),
    )
    branche_etrangere, voies_etrangeres = _creer_branche_et_voies(
        autre_intersection,
        "Est",
        90.0,
    )

    rapport = valider_intersection(
        intersection_cible,
        (*branches_valides, branche_etrangere),
        (*voies_valides, *voies_etrangeres),
    )
    assert rapport.est_valide is False
    codes_erreur = {anomalie.code for anomalie in rapport.erreurs}
    assert "BRANCHE_INTERSECTION_INCOHERENTE" in codes_erreur
    assert "NOMBRE_BRANCHES_INSUFFISANT" in codes_erreur
    assert "VOIE_BRANCHE_INCONNUE" in codes_erreur


def test_voie_referencant_branche_non_fournie_est_rejetee() -> None:
    intersection = Intersection(nom="Carrefour Voie Orpheline")
    branches, voies = _assembler_topologie(
        intersection,
        (
            ("Nord", 0.0),
            ("Sud", 180.0),
            ("Est", 90.0),
        ),
    )
    autre_branche = Branche(
        nom="Branche Non Fournie",
        intersection_tracking_id=intersection.tracking_id,
        angle_degres=45.0,
    )
    voie_orpheline = Voie(
        nom="Voie sans branche déclarée",
        branche_tracking_id=autre_branche.tracking_id,
        direction=DirectionVoie.ENTRANTE,
        position=1,
    )

    rapport = valider_intersection(intersection, branches, (*voies, voie_orpheline))
    assert rapport.est_valide is False
    codes_erreur = {anomalie.code for anomalie in rapport.erreurs}
    assert "VOIE_BRANCHE_INCONNUE" in codes_erreur


def test_tracking_ids_branches_dupliques_sont_rejetes() -> None:
    intersection = Intersection(nom="Carrefour Doublon Branche")
    b1, v1 = _creer_branche_et_voies(intersection, "Nord 1", 0.0)
    b2 = Branche(
        nom="Nord 2",
        intersection_tracking_id=intersection.tracking_id,
        angle_degres=90.0,
        tracking_id=b1.tracking_id,
    )
    b3, v3 = _creer_branche_et_voies(intersection, "Sud", 180.0)

    rapport = valider_intersection(
        intersection,
        (b1, b2, b3),
        (*v1, *v3),
    )
    assert rapport.est_valide is False
    codes_erreur = {anomalie.code for anomalie in rapport.erreurs}
    assert "TRACKING_ID_BRANCHE_DUPLIQUE" in codes_erreur
    assert "VOIE_BRANCHE_INCONNUE" in codes_erreur


# ---------------------------------------------------------------------------
# Sécurisation des types d'entrée et fonctions de récupération
# ---------------------------------------------------------------------------


def test_objets_de_mauvais_type_transmis_a_valider_produisent_erreurs_maitrisees() -> None:
    validateur = ValidateurIntersection()

    rapport_1 = validateur.valider(
        intersection="pas_une_intersection",  # type: ignore[arg-type]
        branches="pas_une_liste",  # type: ignore[arg-type]
        voies=None,  # type: ignore[arg-type]
    )
    assert rapport_1.est_valide is False
    codes_1 = {err.code for err in rapport_1.erreurs}
    assert "TYPE_INTERSECTION_INVALIDE" in codes_1
    assert "TYPE_COLLECTION_BRANCHES_INVALIDE" in codes_1
    assert "TYPE_COLLECTION_VOIES_INVALIDE" in codes_1

    intersection = Intersection(nom="Carrefour")
    b1, v1 = _creer_branche_et_voies(intersection, "Nord", 0.0)
    b2, v2 = _creer_branche_et_voies(intersection, "Sud", 180.0)
    b3, v3 = _creer_branche_et_voies(intersection, "Est", 90.0)

    rapport_2 = validateur.valider(
        intersection=intersection,
        branches=(b1, b2, b3, {"objet": "intrus"}),  # type: ignore[arg-type]
        voies=(*v1, *v2, *v3, 999),  # type: ignore[arg-type]
    )
    assert rapport_2.est_valide is False
    codes_2 = {err.code for err in rapport_2.erreurs}
    assert "TYPE_BRANCHE_INVALIDE" in codes_2
    assert "TYPE_VOIE_INVALIDE" in codes_2


@pytest.mark.parametrize("mauvais_nom", [123, None, ["liste"], True, {"cle": "val"}])
def test_noms_de_mauvais_type_ne_provoquent_pas_exception_non_maitrisee(
    mauvais_nom: object,
) -> None:
    intersection = Intersection(
        nom=mauvais_nom,  # type: ignore[arg-type]
        description=mauvais_nom,  # type: ignore[arg-type]
    )
    branche = Branche(
        nom=mauvais_nom,  # type: ignore[arg-type]
        intersection_tracking_id=intersection.tracking_id,
        angle_degres=0.0,
    )
    voie = Voie(
        nom=mauvais_nom,  # type: ignore[arg-type]
        branche_tracking_id=branche.tracking_id,
        direction=DirectionVoie.ENTRANTE,
        position=1,
    )

    rapport = valider_intersection(intersection, (branche,), (voie,))
    assert rapport.est_valide is False
    codes_erreur = {anomalie.code for anomalie in rapport.erreurs}
    assert "NOM_INTERSECTION_VIDE" in codes_erreur
    assert "DESCRIPTION_INTERSECTION_INVALIDE" in codes_erreur
    assert "NOM_BRANCHE_VIDE" in codes_erreur
    assert "NOM_VOIE_VIDE" in codes_erreur


def test_comportement_fonctions_recuperation_voies_avec_donnees_incorrectes() -> None:
    intersection = Intersection(nom="Carrefour")
    branche = Branche(nom="Branche 1", intersection_tracking_id=intersection.tracking_id)
    autre_branche = Branche(nom="Branche 2", intersection_tracking_id=intersection.tracking_id)

    voies_mixtes: tuple[object, ...] = (
        "intrus",
        None,
        Voie(nom="Pos 0", branche_tracking_id=branche.tracking_id, direction=DirectionVoie.ENTRANTE, position=0),
        Voie(nom="Pos -5", branche_tracking_id=branche.tracking_id, direction=DirectionVoie.ENTRANTE, position=-5),
        Voie(nom="Pos True", branche_tracking_id=branche.tracking_id, direction=DirectionVoie.ENTRANTE, position=True),  # type: ignore[arg-type]
        Voie(nom="Pos str", branche_tracking_id=branche.tracking_id, direction=DirectionVoie.ENTRANTE, position="1"),  # type: ignore[arg-type]
        Voie(nom="   ", branche_tracking_id=branche.tracking_id, direction=DirectionVoie.ENTRANTE, position=1),
        Voie(nom="Autre", branche_tracking_id=autre_branche.tracking_id, direction=DirectionVoie.ENTRANTE, position=1),
        Voie(nom="Entrée 3", branche_tracking_id=branche.tracking_id, direction=DirectionVoie.ENTRANTE, position=3),
        Voie(nom="Entrée 1", branche_tracking_id=branche.tracking_id, direction=DirectionVoie.ENTRANTE, position=1),
        Voie(nom="Sortie 2", branche_tracking_id=branche.tracking_id, direction=DirectionVoie.SORTANTE, position=2),
        Voie(nom="Sortie 1", branche_tracking_id=branche.tracking_id, direction=DirectionVoie.SORTANTE, position=1),
    )

    # Récupération soit par Branche soit par UUID
    entrantes = obtenir_voies_entrantes(branche, voies_mixtes)  # type: ignore[arg-type]
    sortantes = obtenir_voies_sortantes(branche.tracking_id, voies_mixtes)  # type: ignore[arg-type]

    assert [v.nom for v in entrantes] == ["Entrée 1", "Entrée 3"]
    assert [v.nom for v in sortantes] == ["Sortie 1", "Sortie 2"]
    assert obtenir_voies_entrantes(uuid4(), voies_mixtes) == ()  # type: ignore[arg-type]

    for b_invalide in ("", None, 42, "pas_un_uuid"):
        with pytest.raises(ValueError):
            obtenir_voies_entrantes(b_invalide, ())  # type: ignore[arg-type]

    for collection_invalide in ("chaine", None, 123):
        with pytest.raises(ValueError):
            obtenir_voies_entrantes(branche.tracking_id, collection_invalide)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Angles et validation de base
# ---------------------------------------------------------------------------


def test_intersection_avec_moins_de_trois_branches_est_invalide() -> None:
    intersection = Intersection(nom="Carrefour incomplet")
    branches, voies = _assembler_topologie(
        intersection,
        (
            ("Nord", 0.0),
            ("Sud", 180.0),
        ),
    )

    rapport = valider_intersection(intersection, branches, voies)
    assert rapport.est_valide is False
    codes_erreur = {anomalie.code for anomalie in rapport.erreurs}
    assert "NOMBRE_BRANCHES_INSUFFISANT" in codes_erreur


def test_branche_sans_voie_est_invalide() -> None:
    intersection = Intersection(nom="Carrefour branche vide")
    branches_valides, voies_valides = _assembler_topologie(
        intersection,
        (
            ("Nord", 0.0),
            ("Sud", 180.0),
        ),
    )
    branche_vide = Branche(
        nom="Branche sans voie",
        intersection_tracking_id=intersection.tracking_id,
        angle_degres=90.0,
    )

    rapport = valider_intersection(
        intersection,
        (*branches_valides, branche_vide),
        voies_valides,
    )
    assert rapport.est_valide is False
    codes_erreur = {anomalie.code for anomalie in rapport.erreurs}
    assert "BRANCHE_SANS_VOIE" in codes_erreur


@pytest.mark.parametrize(
    "angle_invalide",
    [
        -0.1,
        -45.0,
        360.1,
        400.0,
        math.nan,
        math.inf,
        -math.inf,
        True,
        False,
        "90.0",
    ],
)
def test_angle_branche_invalide_est_rejete(angle_invalide: object) -> None:
    intersection = Intersection(nom="Carrefour angle invalide")
    branches, voies = _assembler_topologie(
        intersection,
        (
            ("Nord", angle_invalide),  # type: ignore[arg-type]
            ("Sud", 180.0),
            ("Est", 90.0),
        ),
    )

    rapport = valider_intersection(intersection, branches, voies)
    assert rapport.est_valide is False
    codes_erreur = {anomalie.code for anomalie in rapport.erreurs}
    assert "ANGLE_BRANCHE_INVALIDE" in codes_erreur


def test_identite_intersection_invalide_rapporte_erreurs_et_leve_exception() -> None:
    intersection_invalide = Intersection(nom="")
    branches, voies = _assembler_topologie(
        intersection_invalide,
        (
            ("Nord", 0.0),
            ("Sud", 180.0),
            ("Est", 90.0),
        ),
    )

    rapport = valider_intersection(intersection_invalide, branches, voies)
    assert rapport.est_valide is False
    codes_erreur = {anomalie.code for anomalie in rapport.erreurs}
    assert "NOM_INTERSECTION_VIDE" in codes_erreur

    with pytest.raises(ErreurValidationIntersection) as exc_info:
        valider_intersection(intersection_invalide, branches, voies, lever_exception=True)

    assert "NOM_INTERSECTION_VIDE" in str(exc_info.value)


def test_rapport_validation_distingue_avertissements_et_erreurs() -> None:
    rapport = RapportValidationIntersection()
    rapport.ajouter_avertissement(
        code="DESCRIPTION_MANQUANTE",
        message="La description de l'intersection n'est pas renseignée.",
        champ="description",
    )
    assert rapport.est_valide is True
    assert len(rapport.avertissements) == 1
    assert len(rapport.erreurs) == 0
    assert rapport.avertissements[0] == AnomalieValidationIntersection(
        code="DESCRIPTION_MANQUANTE",
        message="La description de l'intersection n'est pas renseignée.",
        gravite=GraviteValidation.AVERTISSEMENT,
        champ="description",
    )


def test_validateur_emet_avertissement_si_description_vide_sans_invalider() -> None:
    intersection = Intersection(nom="Carrefour GTA", description="")
    branches, voies = _assembler_topologie(
        intersection,
        (
            ("Nord", 0.0),
            ("Sud", 180.0),
            ("Est", 90.0),
        ),
    )

    validateur = ValidateurIntersection()
    rapport = validateur.valider(intersection, branches, voies)

    assert rapport.est_valide is True
    assert len(rapport.erreurs) == 0
    assert len(rapport.avertissements) == 1
    assert rapport.avertissements[0].code == "DESCRIPTION_INTERSECTION_VIDE"
