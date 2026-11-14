"""Service de chargement et de validation de carrefours depuis des fichiers JSON."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from app.intersection.entities import (
    Branche,
    ConflitBranches,
    DirectionVoie,
    Intersection,
    Phase,
    Voie,
)
from app.intersection.exceptions import (
    ErreurChargementCarrefour,
    ErreurValidationIntersection,
)
from app.intersection.validator import valider_intersection


@dataclass(frozen=True, slots=True)
class CarrefourCharge:
    """Carrefour validé et chargé en mémoire."""

    intersection: Intersection
    branches: tuple[Branche, ...]
    voies: tuple[Voie, ...]
    phases: tuple[Phase, ...]
    conflits: tuple[ConflitBranches, ...]


def charger_carrefour(chemin: Path) -> CarrefourCharge:
    """
    Lit un carrefour depuis un fichier JSON, instancie les entités,
    exécute le validateur et retourne un CarrefourCharge.

    Lève:
        ErreurChargementCarrefour: si le fichier est introuvable, le JSON invalide,
                                  une clé manquante, un type incorrect ou une direction inconnue.
        ErreurValidationIntersection: si la topologie du carrefour est invalide.
    """
    chemin_path = Path(chemin)
    if not chemin_path.is_file():
        raise ErreurChargementCarrefour(f"Fichier de carrefour introuvable: {chemin_path}")

    try:
        contenu = chemin_path.read_text(encoding="utf-8")
    except OSError as err:
        raise ErreurChargementCarrefour(f"Impossible de lire le fichier {chemin_path}: {err}") from err

    try:
        donnees = json.loads(contenu)
    except json.JSONDecodeError as err:
        raise ErreurChargementCarrefour(f"JSON invalide dans {chemin_path}: {err}") from err

    if not isinstance(donnees, dict):
        raise ErreurChargementCarrefour("Le contenu JSON racine doit être un objet/dictionnaire.")

    for cle_racine in ("intersection", "branches", "voies", "phases", "conflits"):
        if cle_racine not in donnees:
            raise ErreurChargementCarrefour(f"Clé manquante à la racine du JSON: '{cle_racine}'.")

    donnees_inter = donnees["intersection"]
    if not isinstance(donnees_inter, dict):
        raise ErreurChargementCarrefour("La section 'intersection' doit être un dictionnaire.")

    for cle_inter in ("id_intersection", "nom"):
        if cle_inter not in donnees_inter:
            raise ErreurChargementCarrefour(f"Clé manquante dans 'intersection': '{cle_inter}'.")

    id_intersection = donnees_inter["id_intersection"]
    nom_intersection = donnees_inter["nom"]
    description_intersection = donnees_inter.get("description", "")

    if (
        not isinstance(id_intersection, str)
        or not isinstance(nom_intersection, str)
        or not isinstance(description_intersection, str)
    ):
        raise ErreurChargementCarrefour(
            "Les champs 'id_intersection', 'nom' et 'description' de l'intersection doivent être des chaînes."
        )

    intersection = Intersection(
        id_intersection=id_intersection,
        nom=nom_intersection,
        description=description_intersection,
    )

    donnees_branches = donnees["branches"]
    if not isinstance(donnees_branches, list):
        raise ErreurChargementCarrefour("La section 'branches' doit être une liste.")

    branches_list: list[Branche] = []
    for idx_b, b_item in enumerate(donnees_branches):
        if not isinstance(b_item, dict):
            raise ErreurChargementCarrefour(f"branches[{idx_b}] doit être un dictionnaire.")
        for cle_b in ("id_branche", "id_intersection", "nom", "angle_degres"):
            if cle_b not in b_item:
                raise ErreurChargementCarrefour(f"Clé manquante dans branches[{idx_b}]: '{cle_b}'.")

        id_b = b_item["id_branche"]
        id_inter_b = b_item["id_intersection"]
        nom_b = b_item["nom"]
        angle_b = b_item["angle_degres"]

        if not isinstance(id_b, str) or not isinstance(id_inter_b, str) or not isinstance(nom_b, str):
            raise ErreurChargementCarrefour(f"Identifiants et nom dans branches[{idx_b}] doivent être des chaînes.")
        if isinstance(angle_b, bool) or not isinstance(angle_b, (int, float)):
            raise ErreurChargementCarrefour(f"'angle_degres' dans branches[{idx_b}] doit être un nombre.")

        branches_list.append(
            Branche(
                id_branche=id_b,
                id_intersection=id_inter_b,
                nom=nom_b,
                angle_degres=float(angle_b),
            )
        )

    donnees_voies = donnees["voies"]
    if not isinstance(donnees_voies, list):
        raise ErreurChargementCarrefour("La section 'voies' doit être une liste.")

    voies_list: list[Voie] = []
    for idx_v, v_item in enumerate(donnees_voies):
        if not isinstance(v_item, dict):
            raise ErreurChargementCarrefour(f"voies[{idx_v}] doit être un dictionnaire.")
        for cle_v in ("id_voie", "id_branche", "nom", "direction", "position"):
            if cle_v not in v_item:
                raise ErreurChargementCarrefour(f"Clé manquante dans voies[{idx_v}]: '{cle_v}'.")

        id_v = v_item["id_voie"]
        id_branche_v = v_item["id_branche"]
        nom_v = v_item["nom"]
        dir_v = v_item["direction"]
        pos_v = v_item["position"]

        if not isinstance(id_v, str) or not isinstance(id_branche_v, str) or not isinstance(nom_v, str):
            raise ErreurChargementCarrefour(f"Identifiants et nom dans voies[{idx_v}] doivent être des chaînes.")

        if not isinstance(dir_v, str):
            raise ErreurChargementCarrefour(f"'direction' dans voies[{idx_v}] doit être une chaîne.")

        try:
            direction_enum = DirectionVoie(dir_v)
        except ValueError as err:
            raise ErreurChargementCarrefour(
                f"Direction inconnue dans voies[{idx_v}]: '{dir_v}'."
            ) from err

        if isinstance(pos_v, bool) or not isinstance(pos_v, int):
            raise ErreurChargementCarrefour(f"'position' dans voies[{idx_v}] doit être un entier.")

        voies_list.append(
            Voie(
                id_voie=id_v,
                id_branche=id_branche_v,
                nom=nom_v,
                direction=direction_enum,
                position=pos_v,
            )
        )

    donnees_phases = donnees["phases"]
    if not isinstance(donnees_phases, list):
        raise ErreurChargementCarrefour("La section 'phases' doit être une liste.")

    phases_list: list[Phase] = []
    for idx_p, p_item in enumerate(donnees_phases):
        if not isinstance(p_item, dict):
            raise ErreurChargementCarrefour(f"phases[{idx_p}] doit être un dictionnaire.")
        for cle_p in ("id_phase", "id_intersection", "nom", "ordre", "ids_branches"):
            if cle_p not in p_item:
                raise ErreurChargementCarrefour(f"Clé manquante dans phases[{idx_p}]: '{cle_p}'.")

        id_p = p_item["id_phase"]
        id_inter_p = p_item["id_intersection"]
        nom_p = p_item["nom"]
        ordre_p = p_item["ordre"]
        ids_branches_p = p_item["ids_branches"]

        if not isinstance(id_p, str) or not isinstance(id_inter_p, str) or not isinstance(nom_p, str):
            raise ErreurChargementCarrefour(f"Identifiants et nom dans phases[{idx_p}] doivent être des chaînes.")

        if isinstance(ordre_p, bool) or not isinstance(ordre_p, int):
            raise ErreurChargementCarrefour(f"'ordre' dans phases[{idx_p}] doit être un entier.")

        if not isinstance(ids_branches_p, list):
            raise ErreurChargementCarrefour(f"'ids_branches' dans phases[{idx_p}] doit être une liste.")

        for idx_bp, b_id in enumerate(ids_branches_p):
            if not isinstance(b_id, str):
                raise ErreurChargementCarrefour(
                    f"Élément ids_branches[{idx_bp}] dans phases[{idx_p}] doit être une chaîne."
                )

        phases_list.append(
            Phase(
                id_phase=id_p,
                id_intersection=id_inter_p,
                nom=nom_p,
                ordre=ordre_p,
                ids_branches=tuple(ids_branches_p),
            )
        )

    donnees_conflits = donnees["conflits"]
    if not isinstance(donnees_conflits, list):
        raise ErreurChargementCarrefour("La section 'conflits' doit être une liste.")

    conflits_list: list[ConflitBranches] = []
    for idx_c, c_item in enumerate(donnees_conflits):
        if not isinstance(c_item, dict):
            raise ErreurChargementCarrefour(f"conflits[{idx_c}] doit être un dictionnaire.")
        for cle_c in ("id_branche_a", "id_branche_b"):
            if cle_c not in c_item:
                raise ErreurChargementCarrefour(f"Clé manquante dans conflits[{idx_c}]: '{cle_c}'.")

        id_ba = c_item["id_branche_a"]
        id_bb = c_item["id_branche_b"]

        if not isinstance(id_ba, str) or not isinstance(id_bb, str):
            raise ErreurChargementCarrefour(f"Identifiants dans conflits[{idx_c}] doivent être des chaînes.")

        conflits_list.append(
            ConflitBranches(
                id_branche_a=id_ba,
                id_branche_b=id_bb,
            )
        )

    branches_tuple = tuple(branches_list)
    voies_tuple = tuple(voies_list)
    phases_tuple = tuple(phases_list)
    conflits_tuple = tuple(conflits_list)

    rapport = valider_intersection(
        intersection=intersection,
        branches=branches_tuple,
        voies=voies_tuple,
        phases=phases_tuple,
        conflits=conflits_tuple,
    )
    rapport.lever_si_invalide()

    return CarrefourCharge(
        intersection=intersection,
        branches=branches_tuple,
        voies=voies_tuple,
        phases=phases_tuple,
        conflits=conflits_tuple,
    )
