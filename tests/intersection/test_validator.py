"""Tests unitaires du validateur d'intersection."""

from __future__ import annotations

import math
import pytest

from app.intersection.entities import (
    Branche,
    ConflitBranches,
    DirectionVoie,
    Intersection,
    Phase,
    Voie,
)
from app.intersection.exceptions import ErreurValidationIntersection
from app.intersection.validator import (
    GraviteValidation,
    RapportValidationIntersection,
    ValidateurIntersection,
    obtenir_voies_entrantes,
    obtenir_voies_sortantes,
    valider_intersection,
)


def _creer_topologie_base(
    id_inter: str = "int_1",
    nb_branches: int = 3,
) -> tuple[Intersection, list[Branche], list[Voie]]:
    """Construit une topologie valide avec nb_branches et 2 voies par branche (1 ENTRANTE, 1 SORTANTE)."""
    inter = Intersection(id_intersection=id_inter, nom="Carrefour Principal", description="Description")
    branches: list[Branche] = []
    voies: list[Voie] = []

    angles = [0.0, 90.0, 180.0, 270.0, 45.0]
    for i in range(nb_branches):
        b_id = f"b_{i + 1}"
        angle = angles[i % len(angles)]
        branches.append(
            Branche(
                id_branche=b_id,
                id_intersection=id_inter,
                nom=f"Branche {i + 1}",
                angle_degres=angle,
            )
        )
        voies.append(
            Voie(
                id_voie=f"v_{b_id}_in",
                id_branche=b_id,
                nom=f"Voie Entrante {i + 1}",
                direction=DirectionVoie.ENTRANTE,
                position=1,
            )
        )
        voies.append(
            Voie(
                id_voie=f"v_{b_id}_out",
                id_branche=b_id,
                nom=f"Voie Sortante {i + 1}",
                direction=DirectionVoie.SORTANTE,
                position=1,
            )
        )

    return inter, branches, voies


def _creer_phases_et_conflits_valides(
    id_inter: str = "int_1",
) -> tuple[tuple[Phase, ...], tuple[ConflitBranches, ...]]:
    """Construit des phases et conflits cohérents pour un carrefour à 3 branches (b_1, b_2, b_3)."""
    phases = (
        Phase(id_phase="p1", id_intersection=id_inter, nom="Phase 1", ordre=1, ids_branches=("b_1", "b_2")),
        Phase(id_phase="p2", id_intersection=id_inter, nom="Phase 2", ordre=2, ids_branches=("b_3",)),
    )
    conflits = (
        ConflitBranches(id_branche_a="b_1", id_branche_b="b_3"),
        ConflitBranches(id_branche_a="b_2", id_branche_b="b_3"),
    )
    return phases, conflits


# ---------------------------------------------------------------------------
# 1. Une intersection a au moins 3 branches valides
# ---------------------------------------------------------------------------


def test_intersection_a_au_moins_trois_branches_valides() -> None:
    # 2 branches -> invalide
    inter, branches_2, voies_2 = _creer_topologie_base(nb_branches=2)
    rapport_2 = valider_intersection(inter, branches_2, voies_2)
    assert rapport_2.est_valide is False
    codes_2 = {e.code for e in rapport_2.erreurs}
    assert "NOMBRE_BRANCHES_INSUFFISANT" in codes_2

    # 3 branches -> valide
    inter, branches_3, voies_3 = _creer_topologie_base(nb_branches=3)
    rapport_3 = valider_intersection(inter, branches_3, voies_3)
    assert rapport_3.est_valide is True
    assert len(rapport_3.erreurs) == 0

    # 4 branches -> valide
    inter, branches_4, voies_4 = _creer_topologie_base(nb_branches=4)
    rapport_4 = valider_intersection(inter, branches_4, voies_4)
    assert rapport_4.est_valide is True


# ---------------------------------------------------------------------------
# 2. Une branche d'une autre intersection n'est pas valide et ne valide pas ses voies
# ---------------------------------------------------------------------------


def test_branche_autre_intersection_invalide_et_ne_valide_pas_ses_voies() -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=2)

    # 3e branche rattachée à une autre intersection
    branche_etrangere = Branche(
        id_branche="b_autre",
        id_intersection="int_etrangere",
        nom="Branche Infiltrée",
        angle_degres=90.0,
    )
    voie_etrangere = Voie(
        id_voie="v_etrangere",
        id_branche="b_autre",
        nom="Voie étrangère",
        direction=DirectionVoie.ENTRANTE,
        position=1,
    )

    toutes_branches = (*branches, branche_etrangere)
    toutes_voies = (*voies, voie_etrangere)

    rapport = valider_intersection(inter, toutes_branches, toutes_voies)
    assert rapport.est_valide is False
    codes = {e.code for e in rapport.erreurs}
    assert "BRANCHE_INTERSECTION_INCOHERENTE" in codes
    assert "NOMBRE_BRANCHES_INSUFFISANT" in codes
    assert "VOIE_BRANCHE_INCONNUE" in codes


# ---------------------------------------------------------------------------
# 3. Un id_branche dupliqué rend les branches concernées invalides
# ---------------------------------------------------------------------------


def test_id_branche_duplique_rend_branches_concernées_invalides() -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=2)

    # Deux branches partagent l'identifiant "b_doublon"
    b_dup1 = Branche(
        id_branche="b_doublon",
        id_intersection=inter.id_intersection,
        nom="Branche Copie 1",
        angle_degres=90.0,
    )
    b_dup2 = Branche(
        id_branche="b_doublon",
        id_intersection=inter.id_intersection,
        nom="Branche Copie 2",
        angle_degres=120.0,
    )
    v_dup = Voie(
        id_voie="v_dup",
        id_branche="b_doublon",
        nom="Voie b_doublon",
        direction=DirectionVoie.ENTRANTE,
        position=1,
    )

    toutes_branches = (*branches, b_dup1, b_dup2)
    toutes_voies = (*voies, v_dup)

    rapport = valider_intersection(inter, toutes_branches, toutes_voies)
    assert rapport.est_valide is False
    codes = {e.code for e in rapport.erreurs}
    assert "ID_BRANCHE_DUPLIQUE" in codes
    # b_doublon n'est pas considérée comme valide, donc ses voies ne trouvent pas de branche valide
    assert "VOIE_BRANCHE_INCONNUE" in codes
    # Il ne reste que les 2 premières branches valides
    assert "NOMBRE_BRANCHES_INSUFFISANT" in codes


# ---------------------------------------------------------------------------
# 4. Un id_voie dupliqué rend la voie invalide et ne compte pas pour sa branche
# ---------------------------------------------------------------------------


def test_id_voie_duplique_rend_voie_invalide_et_ne_compte_pas_pour_sa_branche() -> None:
    inter = Intersection(id_intersection="int_1", nom="Carrefour 1")
    b1 = Branche(id_branche="b1", id_intersection="int_1", nom="Branche 1", angle_degres=0.0)
    b2 = Branche(id_branche="b2", id_intersection="int_1", nom="Branche 2", angle_degres=90.0)
    b3 = Branche(id_branche="b3", id_intersection="int_1", nom="Branche 3", angle_degres=180.0)

    # b1 et b2 ont des voies valides
    v1 = Voie(id_voie="v1", id_branche="b1", nom="Voie 1", direction=DirectionVoie.ENTRANTE, position=1)
    v2 = Voie(id_voie="v2", id_branche="b2", nom="Voie 2", direction=DirectionVoie.ENTRANTE, position=1)

    # b3 n'a que des voies avec un id_voie dupliqué "v_collision"
    v3_a = Voie(id_voie="v_collision", id_branche="b3", nom="Voie 3A", direction=DirectionVoie.ENTRANTE, position=1)
    v3_b = Voie(id_voie="v_collision", id_branche="b3", nom="Voie 3B", direction=DirectionVoie.SORTANTE, position=1)

    rapport = valider_intersection(inter, (b1, b2, b3), (v1, v2, v3_a, v3_b))
    assert rapport.est_valide is False
    codes = {e.code for e in rapport.erreurs}
    assert "ID_VOIE_DUPLIQUE" in codes
    # Comme les voies dupliquées sont invalides, b3 n'a aucune voie valide
    assert "BRANCHE_SANS_VOIE" in codes


# ---------------------------------------------------------------------------
# 5. Chaque branche a au moins une voie valide
# ---------------------------------------------------------------------------


def test_chaque_branche_a_au_moins_une_voie_valide() -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=3)

    # Cas 1 : branche sans aucune voie
    voies_sans_b3 = [v for v in voies if v.id_branche != "b_3"]
    rapport_vide = valider_intersection(inter, branches, voies_sans_b3)
    assert rapport_vide.est_valide is False
    codes_vide = {e.code for e in rapport_vide.erreurs}
    assert "BRANCHE_SANS_VOIE" in codes_vide

    # Cas 2 : branche avec seulement des voies invalides
    voies_invalides_b3 = [
        Voie(id_voie="v_invalide_1", id_branche="b_3", nom="", direction=DirectionVoie.ENTRANTE, position=1),
        Voie(id_voie="v_invalide_2", id_branche="b_3", nom="Voie", direction=DirectionVoie.ENTRANTE, position=0),
    ]
    rapport_invalide = valider_intersection(inter, branches, (*voies_sans_b3, *voies_invalides_b3))
    assert rapport_invalide.est_valide is False
    codes_inv = {e.code for e in rapport_invalide.erreurs}
    assert "NOM_VOIE_VIDE" in codes_inv
    assert "POSITION_VOIE_INVALIDE" in codes_inv
    assert "BRANCHE_SANS_VOIE" in codes_inv

    # Cas 3 : branche avec 1 voie valide et 1 voie invalide -> pas d'erreur BRANCHE_SANS_VOIE
    voie_valide_b3 = Voie(
        id_voie="v_valide_b3",
        id_branche="b_3",
        nom="Voie Valide",
        direction=DirectionVoie.SORTANTE,
        position=2,
    )
    rapport_mixte = valider_intersection(inter, branches, (*voies_sans_b3, *voies_invalides_b3, voie_valide_b3))
    assert rapport_mixte.est_valide is False
    codes_mixte = {e.code for e in rapport_mixte.erreurs}
    assert "BRANCHE_SANS_VOIE" not in codes_mixte


# ---------------------------------------------------------------------------
# 6. Positions de voie entières ≥ 1, uniques par (id_branche, direction)
# ---------------------------------------------------------------------------


def test_positions_voie_entieres_positives_et_uniques_par_branche_et_direction() -> None:
    inter, branches, _ = _creer_topologie_base(nb_branches=3)

    # Position 0 ou négative
    v_pos_0 = Voie(id_voie="v_0", id_branche="b_1", nom="Pos 0", direction=DirectionVoie.ENTRANTE, position=0)
    v_pos_neg = Voie(id_voie="v_neg", id_branche="b_1", nom="Pos -1", direction=DirectionVoie.ENTRANTE, position=-1)
    rapport_pos = valider_intersection(inter, branches, (v_pos_0, v_pos_neg))
    codes_pos = {e.code for e in rapport_pos.erreurs}
    assert "POSITION_VOIE_INVALIDE" in codes_pos

    # Positions dupliquées pour une même direction sur la même branche
    v_dup_1 = Voie(id_voie="v1", id_branche="b_1", nom="Voie A", direction=DirectionVoie.ENTRANTE, position=1)
    v_dup_2 = Voie(id_voie="v2", id_branche="b_1", nom="Voie B", direction=DirectionVoie.ENTRANTE, position=1)
    v_autre = Voie(id_voie="v3", id_branche="b_2", nom="Voie C", direction=DirectionVoie.ENTRANTE, position=1)
    v_autre_3 = Voie(id_voie="v4", id_branche="b_3", nom="Voie D", direction=DirectionVoie.ENTRANTE, position=1)

    rapport_dup = valider_intersection(inter, branches, (v_dup_1, v_dup_2, v_autre, v_autre_3))
    assert rapport_dup.est_valide is False
    codes_dup = {e.code for e in rapport_dup.erreurs}
    assert "POSITION_VOIE_DUPLIQUEE" in codes_dup

    # Même position mais directions différentes (ENTRANTE vs SORTANTE) sur la même branche -> autorisé
    v_in = Voie(id_voie="v_in", id_branche="b_1", nom="Entrée", direction=DirectionVoie.ENTRANTE, position=1)
    v_out = Voie(id_voie="v_out", id_branche="b_1", nom="Sortie", direction=DirectionVoie.SORTANTE, position=1)
    v_b2 = Voie(id_voie="v_b2", id_branche="b_2", nom="Entrée 2", direction=DirectionVoie.ENTRANTE, position=1)
    v_b3 = Voie(id_voie="v_b3", id_branche="b_3", nom="Entrée 3", direction=DirectionVoie.ENTRANTE, position=1)

    rapport_diff_dir = valider_intersection(inter, branches, (v_in, v_out, v_b2, v_b3))
    assert rapport_diff_dir.est_valide is True


# ---------------------------------------------------------------------------
# 7. Angle de branche : nombre fini entre 0 et 360, bool, NaN, infini et chaînes refusés
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "angle_invalide",
    [
        -0.1,
        -45.0,
        360.1,
        500.0,
        math.nan,
        math.inf,
        -math.inf,
        True,
        False,
        "90.0",
        None,
    ],
)
def test_angle_branche_nombre_fini_entre_0_et_360_refuse_invalides(angle_invalide: object) -> None:
    inter = Intersection(id_intersection="int_1", nom="Carrefour 1")
    b1 = Branche(
        id_branche="b1",
        id_intersection="int_1",
        nom="Branche Angle Invalide",
        angle_degres=angle_invalide,  # type: ignore[arg-type]
    )
    b2 = Branche(id_branche="b2", id_intersection="int_1", nom="Branche 2", angle_degres=90.0)
    b3 = Branche(id_branche="b3", id_intersection="int_1", nom="Branche 3", angle_degres=180.0)

    voies = (
        Voie(id_voie="v1", id_branche="b1", nom="V1", direction=DirectionVoie.ENTRANTE, position=1),
        Voie(id_voie="v2", id_branche="b2", nom="V2", direction=DirectionVoie.ENTRANTE, position=1),
        Voie(id_voie="v3", id_branche="b3", nom="V3", direction=DirectionVoie.ENTRANTE, position=1),
    )

    rapport = valider_intersection(inter, (b1, b2, b3), voies)
    assert rapport.est_valide is False
    codes = {e.code for e in rapport.erreurs}
    assert "ANGLE_BRANCHE_INVALIDE" in codes


# ---------------------------------------------------------------------------
# 8. Un identifiant ou un nom d'un mauvais type produit une anomalie, jamais d'exception Python
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mauvais_type", [123, 45.6, True, None, ["liste"], {"cle": "val"}])
def test_identifiant_ou_nom_mauvais_type_produit_anomalie_sans_exception(mauvais_type: object) -> None:
    inter = Intersection(
        id_intersection=mauvais_type,  # type: ignore[arg-type]
        nom=mauvais_type,  # type: ignore[arg-type]
        description=mauvais_type,  # type: ignore[arg-type]
    )
    b = Branche(
        id_branche=mauvais_type,  # type: ignore[arg-type]
        id_intersection=mauvais_type,  # type: ignore[arg-type]
        nom=mauvais_type,  # type: ignore[arg-type]
        angle_degres=0.0,
    )
    v = Voie(
        id_voie=mauvais_type,  # type: ignore[arg-type]
        id_branche=mauvais_type,  # type: ignore[arg-type]
        nom=mauvais_type,  # type: ignore[arg-type]
        direction=DirectionVoie.ENTRANTE,
        position=1,
    )

    # Ne doit jamais lever d'exception Python non gérée
    validateur = ValidateurIntersection()
    rapport = validateur.valider(inter, (b,), (v,))

    assert rapport.est_valide is False
    codes = {e.code for e in rapport.erreurs}
    assert "ID_INTERSECTION_INVALIDE" in codes
    assert "NOM_INTERSECTION_INVALIDE" in codes
    assert "DESCRIPTION_INTERSECTION_INVALIDE" in codes
    assert "ID_BRANCHE_INVALIDE" in codes
    assert "NOM_BRANCHE_INVALIDE" in codes
    assert "ID_VOIE_INVALIDE" in codes
    assert "NOM_VOIE_INVALIDE" in codes


# ---------------------------------------------------------------------------
# 9. valider() avec un objet de mauvais type produit une anomalie, jamais d'exception Python
# ---------------------------------------------------------------------------


def test_valider_avec_objet_mauvais_type_produit_anomalie_sans_exception() -> None:
    validateur = ValidateurIntersection()

    # Types racines complètement erronés
    rapport_1 = validateur.valider(
        intersection="pas_une_intersection",
        branches="pas_une_liste",
        voies=None,
    )
    assert rapport_1.est_valide is False
    codes_1 = {e.code for e in rapport_1.erreurs}
    assert "TYPE_INTERSECTION_INVALIDE" in codes_1
    assert "TYPE_COLLECTION_BRANCHES_INVALIDE" in codes_1
    assert "TYPE_COLLECTION_VOIES_INVALIDE" in codes_1

    # Objets intrus au sein des collections
    inter, branches, voies = _creer_topologie_base(nb_branches=3)
    rapport_2 = validateur.valider(
        intersection=inter,
        branches=(*branches, {"intrus": "dict"}),
        voies=(*voies, 999),
    )
    assert rapport_2.est_valide is False
    codes_2 = {e.code for e in rapport_2.erreurs}
    assert "TYPE_BRANCHE_INVALIDE" in codes_2
    assert "TYPE_VOIE_INVALIDE" in codes_2


# ---------------------------------------------------------------------------
# Fonctions de filtrage des voies entrantes et sortantes
# ---------------------------------------------------------------------------


def test_recuperation_voies_entrantes_et_sortantes() -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=3)
    b1 = branches[0]

    # Extraction par objet Branche et par identifiant string
    entrantes_branche = obtenir_voies_entrantes(b1, voies)
    sortantes_str = obtenir_voies_sortantes(b1.id_branche, voies)

    assert len(entrantes_branche) == 1
    assert entrantes_branche[0].direction == DirectionVoie.ENTRANTE
    assert len(sortantes_str) == 1
    assert sortantes_str[0].direction == DirectionVoie.SORTANTE

    # Vérification des erreurs sur arguments invalides
    with pytest.raises(ValueError):
        obtenir_voies_entrantes("", voies)

    with pytest.raises(ValueError):
        obtenir_voies_entrantes(b1, "pas_une_liste_de_voies")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Rapport et levée d'exception explicite
# ---------------------------------------------------------------------------


def test_lever_si_invalide_leve_erreur_validation_intersection() -> None:
    inter = Intersection(id_intersection="i1", nom="")
    with pytest.raises(ErreurValidationIntersection) as exc_info:
        valider_intersection(inter, (), (), lever_exception=True)

    assert "Validation de l'intersection échouée" in str(exc_info.value)
    assert len(exc_info.value.anomalies) > 0


# ---------------------------------------------------------------------------
# T3 : Conflits (Règle D.1)
# ---------------------------------------------------------------------------


def test_conflit_reference_deux_branches_valides_differentes() -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=3)
    phases, _ = _creer_phases_et_conflits_valides()

    # Auto-référence (A == B)
    c_auto = ConflitBranches(id_branche_a="b_1", id_branche_b="b_1")
    rapport_auto = valider_intersection(inter, branches, voies, phases=phases, conflits=(c_auto,))
    assert rapport_auto.est_valide is False
    codes_auto = {e.code for e in rapport_auto.erreurs}
    assert "CONFLIT_BRANCHE_AUTO_REFERENCE" in codes_auto

    # Branche inconnue
    c_inconnu = ConflitBranches(id_branche_a="b_1", id_branche_b="b_inconnue")
    rapport_inconnu = valider_intersection(inter, branches, voies, phases=phases, conflits=(c_inconnu,))
    assert rapport_inconnu.est_valide is False
    codes_inconnu = {e.code for e in rapport_inconnu.erreurs}
    assert "CONFLIT_BRANCHE_INCONNUE" in codes_inconnu


def test_conflit_doublon_meme_inverse_est_rejete() -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=3)
    phases, conflits_valides = _creer_phases_et_conflits_valides()

    # Ajout du conflit inverse ("b_3", "b_1") alors que ("b_1", "b_3") existe déjà
    c_inverse = ConflitBranches(id_branche_a="b_3", id_branche_b="b_1")
    conflits_avec_doublon = (*conflits_valides, c_inverse)

    rapport = valider_intersection(inter, branches, voies, phases=phases, conflits=conflits_avec_doublon)
    assert rapport.est_valide is False
    codes = {e.code for e in rapport.erreurs}
    assert "CONFLIT_DUPLIQUE" in codes


def test_conflit_mauvais_types_produit_anomalie_sans_exception() -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=3)
    phases, _ = _creer_phases_et_conflits_valides()

    c_mauvais_type = ConflitBranches(id_branche_a=123, id_branche_b=None)  # type: ignore[arg-type]
    conflits_avec_intrus = (c_mauvais_type, "pas_un_conflit")

    validateur = ValidateurIntersection()
    rapport = validateur.valider(
        inter,
        branches,
        voies,
        phases=phases,
        conflits=conflits_avec_intrus,
    )
    assert rapport.est_valide is False
    codes = {e.code for e in rapport.erreurs}
    assert "ID_BRANCHE_CONFLIT_INVALIDE" in codes
    assert "TYPE_CONFLIT_INVALIDE" in codes


# ---------------------------------------------------------------------------
# T3 : Phases (Règle D.2)
# ---------------------------------------------------------------------------


def test_phase_id_unique_et_non_vide() -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=3)
    _, conflits = _creer_phases_et_conflits_valides()

    # ID vide
    p_vide = Phase(id_phase="", id_intersection="int_1", nom="P1", ordre=1, ids_branches=("b_1", "b_2"))
    p_2 = Phase(id_phase="p2", id_intersection="int_1", nom="P2", ordre=2, ids_branches=("b_3",))
    rapport_vide = valider_intersection(inter, branches, voies, phases=(p_vide, p_2), conflits=conflits)
    assert rapport_vide.est_valide is False
    codes_vide = {e.code for e in rapport_vide.erreurs}
    assert "ID_PHASE_VIDE" in codes_vide

    # ID dupliqué
    p_dup1 = Phase(id_phase="p_meme", id_intersection="int_1", nom="P1", ordre=1, ids_branches=("b_1", "b_2"))
    p_dup2 = Phase(id_phase="p_meme", id_intersection="int_1", nom="P2", ordre=2, ids_branches=("b_3",))
    rapport_dup = valider_intersection(inter, branches, voies, phases=(p_dup1, p_dup2), conflits=conflits)
    assert rapport_dup.est_valide is False
    codes_dup = {e.code for e in rapport_dup.erreurs}
    assert "ID_PHASE_DUPLIQUE" in codes_dup


@pytest.mark.parametrize("ordre_invalide", [0, -1, True, False, 1.5, "1"])
def test_phase_ordre_entier_positif_refuse_invalides_et_doublons(ordre_invalide: object) -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=3)
    _, conflits = _creer_phases_et_conflits_valides()

    # Ordre invalide
    p_inv = Phase(id_phase="p1", id_intersection="int_1", nom="P1", ordre=ordre_invalide, ids_branches=("b_1", "b_2"))  # type: ignore[arg-type]
    p_2 = Phase(id_phase="p2", id_intersection="int_1", nom="P2", ordre=2, ids_branches=("b_3",))
    rapport_inv = valider_intersection(inter, branches, voies, phases=(p_inv, p_2), conflits=conflits)
    assert rapport_inv.est_valide is False
    codes_inv = {e.code for e in rapport_inv.erreurs}
    assert "ORDRE_PHASE_INVALIDE" in codes_inv

    # Ordres dupliqués
    p_dup_o1 = Phase(id_phase="p1", id_intersection="int_1", nom="P1", ordre=1, ids_branches=("b_1", "b_2"))
    p_dup_o2 = Phase(id_phase="p2", id_intersection="int_1", nom="P2", ordre=1, ids_branches=("b_3",))
    rapport_dup_o = valider_intersection(inter, branches, voies, phases=(p_dup_o1, p_dup_o2), conflits=conflits)
    assert rapport_dup_o.est_valide is False
    codes_dup_o = {e.code for e in rapport_dup_o.erreurs}
    assert "ORDRE_PHASE_DUPLIQUE" in codes_dup_o


def test_phase_id_intersection_incoherent() -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=3)
    _, conflits = _creer_phases_et_conflits_valides()

    p1 = Phase(id_phase="p1", id_intersection="autre_inter", nom="P1", ordre=1, ids_branches=("b_1", "b_2"))
    p2 = Phase(id_phase="p2", id_intersection="int_1", nom="P2", ordre=2, ids_branches=("b_3",))
    rapport = valider_intersection(inter, branches, voies, phases=(p1, p2), conflits=conflits)
    assert rapport.est_valide is False
    codes = {e.code for e in rapport.erreurs}
    assert "PHASE_INTERSECTION_INCOHERENTE" in codes


def test_phase_ids_branches_valide_sans_doublon_et_sans_inconnu() -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=3)
    _, conflits = _creer_phases_et_conflits_valides()

    # ids_branches vide
    p_sans_branche = Phase(id_phase="p1", id_intersection="int_1", nom="P1", ordre=1, ids_branches=())
    p2 = Phase(id_phase="p2", id_intersection="int_1", nom="P2", ordre=2, ids_branches=("b_3",))
    rapport_vide = valider_intersection(inter, branches, voies, phases=(p_sans_branche, p2), conflits=conflits)
    assert rapport_vide.est_valide is False
    codes_vide = {e.code for e in rapport_vide.erreurs}
    assert "PHASE_SANS_BRANCHE" in codes_vide

    # Doublon de branche dans la même phase
    p_branche_dup = Phase(id_phase="p1", id_intersection="int_1", nom="P1", ordre=1, ids_branches=("b_1", "b_1"))
    rapport_dup = valider_intersection(inter, branches, voies, phases=(p_branche_dup, p2), conflits=conflits)
    assert rapport_dup.est_valide is False
    codes_dup = {e.code for e in rapport_dup.erreurs}
    assert "BRANCHE_PHASE_DUPLIQUEE" in codes_dup

    # Branche inconnue
    p_inconnu = Phase(id_phase="p1", id_intersection="int_1", nom="P1", ordre=1, ids_branches=("b_1", "b_inconnue"))
    rapport_inconnu = valider_intersection(inter, branches, voies, phases=(p_inconnu, p2), conflits=conflits)
    assert rapport_inconnu.est_valide is False
    codes_inconnu = {e.code for e in rapport_inconnu.erreurs}
    assert "BRANCHE_PHASE_INCONNUE" in codes_inconnu

    # ids_branches mauvais type
    p_mauvais_type = Phase(id_phase="p1", id_intersection="int_1", nom="P1", ordre=1, ids_branches=123)  # type: ignore[arg-type]
    rapport_type = valider_intersection(inter, branches, voies, phases=(p_mauvais_type, p2), conflits=conflits)
    assert rapport_type.est_valide is False
    codes_type = {e.code for e in rapport_type.erreurs}
    assert "TYPE_IDS_BRANCHES_INVALIDE" in codes_type

    # Élément de ids_branches de mauvais type
    p_elem_mauvais = Phase(id_phase="p1", id_intersection="int_1", nom="P1", ordre=1, ids_branches=(999,))  # type: ignore[arg-type]
    rapport_elem = valider_intersection(inter, branches, voies, phases=(p_elem_mauvais, p2), conflits=conflits)
    assert rapport_elem.est_valide is False
    codes_elem = {e.code for e in rapport_elem.erreurs}
    assert "ID_BRANCHE_PHASE_INVALIDE" in codes_elem


# ---------------------------------------------------------------------------
# T3 : Aucune phase ne contient deux branches en conflit (Règle D.3)
# ---------------------------------------------------------------------------


def test_aucune_phase_ne_contient_deux_branches_en_conflit() -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=3)

    # Conflit déclaré entre b_1 et b_2
    conflits = (
        ConflitBranches(id_branche_a="b_1", id_branche_b="b_2"),
        ConflitBranches(id_branche_a="b_2", id_branche_b="b_3"),
        ConflitBranches(id_branche_a="b_1", id_branche_b="b_3"),
    )
    # Phase 1 réunit b_1 et b_2 (qui sont en conflit !)
    p1 = Phase(id_phase="p1", id_intersection="int_1", nom="P1", ordre=1, ids_branches=("b_1", "b_2"))
    p2 = Phase(id_phase="p2", id_intersection="int_1", nom="P2", ordre=2, ids_branches=("b_3",))

    rapport = valider_intersection(inter, branches, voies, phases=(p1, p2), conflits=conflits)
    assert rapport.est_valide is False
    codes = {e.code for e in rapport.erreurs}
    assert "CONFLIT_DANS_PHASE" in codes


# ---------------------------------------------------------------------------
# T3 : Toute branche valide ayant une voie ENTRANTE est servie (Règle D.4)
# ---------------------------------------------------------------------------


def test_toute_branche_avec_voie_entrante_doit_etre_servie() -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=3)
    _, conflits = _creer_phases_et_conflits_valides()

    # b_3 possède une voie ENTRANTE, mais n'est pas dans les phases (seules b_1 et b_2 sont servies)
    p1 = Phase(id_phase="p1", id_intersection="int_1", nom="P1", ordre=1, ids_branches=("b_1", "b_2"))

    rapport = valider_intersection(inter, branches, voies, phases=(p1,), conflits=conflits)
    assert rapport.est_valide is False
    codes = {e.code for e in rapport.erreurs}
    assert "BRANCHE_NON_SERVIE" in codes


# ---------------------------------------------------------------------------
# T3 : Toute branche valide ayant une voie ENTRANTE apparaît dans un conflit (Règle D.5)
# ---------------------------------------------------------------------------


def test_toute_branche_avec_voie_entrante_doit_etre_en_conflit() -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=3)
    phases, _ = _creer_phases_et_conflits_valides()

    # Seul conflit déclaré : entre b_1 et b_2. b_3 (ayant une voie ENTRANTE) n'a aucun conflit
    conflits_sans_b3 = (
        ConflitBranches(id_branche_a="b_1", id_branche_b="b_2"),
    )

    rapport = valider_intersection(inter, branches, voies, phases=phases, conflits=conflits_sans_b3)
    assert rapport.est_valide is False
    codes = {e.code for e in rapport.erreurs}
    assert "BRANCHE_SANS_CONFLIT" in codes


# ---------------------------------------------------------------------------
# T3 : phases=() vide produit AUCUNE_PHASE (Règle D.6)
# ---------------------------------------------------------------------------


def test_phases_vide_produit_aucune_phase() -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=3)
    _, conflits = _creer_phases_et_conflits_valides()

    rapport = valider_intersection(inter, branches, voies, phases=(), conflits=conflits)
    assert rapport.est_valide is False
    codes = {e.code for e in rapport.erreurs}
    assert "AUCUNE_PHASE" in codes


# ---------------------------------------------------------------------------
# T3 : Activation conditionnelle de l'étape "phases" et support multi-phases
# ---------------------------------------------------------------------------


def test_phases_none_ne_declenche_pas_etape_phases() -> None:
    inter, branches, voies = _creer_topologie_base(nb_branches=3)

    # Sans phases ni conflits (None par défaut)
    rapport_sans = valider_intersection(inter, branches, voies)
    assert rapport_sans.est_valide is True
    assert "phases" not in rapport_sans.etapes_executees
    assert rapport_sans.etapes_executees == ("identite", "topologie", "voies")

    # Avec phases et conflits
    phases, conflits = _creer_phases_et_conflits_valides()
    rapport_avec = valider_intersection(inter, branches, voies, phases=phases, conflits=conflits)
    assert rapport_avec.est_valide is True
    assert "phases" in rapport_avec.etapes_executees
    assert rapport_avec.etapes_executees == ("identite", "topologie", "voies", "phases")


def test_carrefour_quatre_phases_est_valide() -> None:
    """Vérifie qu'un carrefour à 4 phases (1 phase par branche) est parfaitement valide."""
    inter, branches_4, voies_4 = _creer_topologie_base(nb_branches=4)

    # 4 phases indépendantes
    phases_4 = (
        Phase(id_phase="p1", id_intersection="int_1", nom="P1", ordre=1, ids_branches=("b_1",)),
        Phase(id_phase="p2", id_intersection="int_1", nom="P2", ordre=2, ids_branches=("b_2",)),
        Phase(id_phase="p3", id_intersection="int_1", nom="P3", ordre=3, ids_branches=("b_3",)),
        Phase(id_phase="p4", id_intersection="int_1", nom="P4", ordre=4, ids_branches=("b_4",)),
    )
    # Conflits croisés entre toutes les approches
    conflits_4 = (
        ConflitBranches(id_branche_a="b_1", id_branche_b="b_2"),
        ConflitBranches(id_branche_a="b_1", id_branche_b="b_4"),
        ConflitBranches(id_branche_a="b_3", id_branche_b="b_2"),
        ConflitBranches(id_branche_a="b_3", id_branche_b="b_4"),
    )

    rapport = valider_intersection(inter, branches_4, voies_4, phases=phases_4, conflits=conflits_4)
    assert rapport.est_valide is True
    assert len(rapport.erreurs) == 0
