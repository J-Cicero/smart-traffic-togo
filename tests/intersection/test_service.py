"""Tests unitaires du service de chargement de carrefour."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import pytest

from app.intersection.entities import Branche, DirectionVoie, Intersection, Voie
from app.intersection.exceptions import (
    ErreurChargementCarrefour,
    ErreurValidationIntersection,
)
from app.intersection.service import CarrefourCharge, charger_carrefour


CHEMIN_EXEMPLE = Path("config/carrefours/exemple_4_branches.json")


def test_chargement_exemple_reussi() -> None:
    carrefour = charger_carrefour(CHEMIN_EXEMPLE)

    assert isinstance(carrefour, CarrefourCharge)
    assert isinstance(carrefour.intersection, Intersection)
    assert carrefour.intersection.id_intersection == "int_dekon"
    assert carrefour.intersection.nom == "Carrefour Dékon"

    assert len(carrefour.branches) == 4
    for b in carrefour.branches:
        assert isinstance(b, Branche)
        assert b.id_intersection == "int_dekon"

    assert len(carrefour.voies) == 8
    for v in carrefour.voies:
        assert isinstance(v, Voie)
        assert v.direction in (DirectionVoie.ENTRANTE, DirectionVoie.SORTANTE)


def test_fichier_introuvable(tmp_path: Path) -> None:
    chemin_inconnu = tmp_path / "inexistant.json"
    with pytest.raises(ErreurChargementCarrefour) as exc_info:
        charger_carrefour(chemin_inconnu)

    assert "Fichier de carrefour introuvable" in str(exc_info.value)


def test_json_invalide(tmp_path: Path) -> None:
    fichier_invalide = tmp_path / "invalide.json"
    fichier_invalide.write_text("{ ce n'est pas un json valide }", encoding="utf-8")

    with pytest.raises(ErreurChargementCarrefour) as exc_info:
        charger_carrefour(fichier_invalide)

    assert "JSON invalide" in str(exc_info.value)


@pytest.mark.parametrize(
    "supprimer_cle_racine",
    ["intersection", "branches", "voies"],
)
def test_cle_racine_manquante(tmp_path: Path, supprimer_cle_racine: str) -> None:
    donnees = json.loads(CHEMIN_EXEMPLE.read_text(encoding="utf-8"))
    del donnees[supprimer_cle_racine]

    fichier = tmp_path / f"sans_{supprimer_cle_racine}.json"
    fichier.write_text(json.dumps(donnees), encoding="utf-8")

    with pytest.raises(ErreurChargementCarrefour) as exc_info:
        charger_carrefour(fichier)

    assert "Clé manquante à la racine" in str(exc_info.value)


def test_cle_interne_manquante(tmp_path: Path) -> None:
    # Clé manquante dans branche
    donnees = json.loads(CHEMIN_EXEMPLE.read_text(encoding="utf-8"))
    del donnees["branches"][0]["angle_degres"]

    fichier_branche = tmp_path / "branche_sans_angle.json"
    fichier_branche.write_text(json.dumps(donnees), encoding="utf-8")

    with pytest.raises(ErreurChargementCarrefour) as exc_info:
        charger_carrefour(fichier_branche)

    assert "Clé manquante dans branches[0]: 'angle_degres'" in str(exc_info.value)


def test_type_incorrect(tmp_path: Path) -> None:
    donnees = json.loads(CHEMIN_EXEMPLE.read_text(encoding="utf-8"))
    donnees["branches"][0]["angle_degres"] = "pas_un_nombre"

    fichier = tmp_path / "angle_str.json"
    fichier.write_text(json.dumps(donnees), encoding="utf-8")

    with pytest.raises(ErreurChargementCarrefour) as exc_info:
        charger_carrefour(fichier)

    assert "'angle_degres' dans branches[0] doit être un nombre" in str(exc_info.value)


def test_direction_inconnue(tmp_path: Path) -> None:
    donnees = json.loads(CHEMIN_EXEMPLE.read_text(encoding="utf-8"))
    donnees["voies"][0]["direction"] = "DIAGONALE"

    fichier = tmp_path / "direction_inconnue.json"
    fichier.write_text(json.dumps(donnees), encoding="utf-8")

    with pytest.raises(ErreurChargementCarrefour) as exc_info:
        charger_carrefour(fichier)

    assert "Direction inconnue dans voies[0]: 'DIAGONALE'" in str(exc_info.value)


def test_topologie_invalide_branche_autre_intersection(tmp_path: Path) -> None:
    donnees = json.loads(CHEMIN_EXEMPLE.read_text(encoding="utf-8"))
    donnees["branches"][0]["id_intersection"] = "autre_carrefour"

    fichier = tmp_path / "branche_autre_intersection.json"
    fichier.write_text(json.dumps(donnees), encoding="utf-8")

    with pytest.raises(ErreurValidationIntersection) as exc_info:
        charger_carrefour(fichier)

    codes = {e.code for e in exc_info.value.anomalies}
    assert "BRANCHE_INTERSECTION_INCOHERENTE" in codes


def test_entites_retournees_figees_et_collections_sont_des_tuples() -> None:
    carrefour = charger_carrefour(CHEMIN_EXEMPLE)

    # Vérification que les collections sont des tuples
    assert isinstance(carrefour.branches, tuple)
    assert isinstance(carrefour.voies, tuple)

    # Vérification de l'immutabilité (dataclasses figées)
    with pytest.raises(FrozenInstanceError):
        carrefour.intersection.nom = "Nouveau Nom"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        carrefour.branches[0].nom = "Nouveau Nom"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        carrefour.voies[0].nom = "Nouveau Nom"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        carrefour.branches = ()  # type: ignore[misc]
