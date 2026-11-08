"""Tests unitaires et d'intégration du service métier IntersectionService."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.intersection.exceptions import (
    ConflitDonneesErreur,
    EntiteNonTrouveeErreur,
    ErreurValidationIntersection,
    SuppressionImpossibleErreur,
)
from app.intersection.entities import DirectionVoie
from app.intersection.service import IntersectionService


def test_service_crud_complet_intersection(db_session: Session) -> None:
    service = IntersectionService(db_session)

    # 1. Création valide
    inter = service.creer_intersection(nom="Carrefour Dékon", description="Lomé Centre")
    db_session.commit()
    assert inter.nom == "Carrefour Dékon"
    assert inter.id is not None

    # 2. Consultation
    recuperee = service.obtenir_intersection(inter.tracking_id)
    assert recuperee.tracking_id == inter.tracking_id

    # 3. Modification
    maj = service.modifier_intersection(
        inter.tracking_id, nom="Carrefour Dékon Rénové", description="Mise à jour"
    )
    db_session.commit()
    assert maj.nom == "Carrefour Dékon Rénové"
    assert maj.description == "Mise à jour"

    # 4. Rejet nom vide
    with pytest.raises(ErreurValidationIntersection):
        service.modifier_intersection(inter.tracking_id, nom="   ")

    # 5. Suppression
    service.supprimer_intersection(inter.tracking_id)
    db_session.commit()
    with pytest.raises(EntiteNonTrouveeErreur):
        service.obtenir_intersection(inter.tracking_id)


def test_service_empeche_branche_sans_intersection(db_session: Session) -> None:
    service = IntersectionService(db_session)
    faux_tracking_id = uuid4()

    with pytest.raises(EntiteNonTrouveeErreur) as exc_info:
        service.creer_branche(
            nom="Branche Orpheline",
            intersection_tracking_id=faux_tracking_id,
            angle_degres=90.0,
        )
    assert "n'existe pas" in str(exc_info.value)


def test_service_empeche_voie_sans_branche(db_session: Session) -> None:
    service = IntersectionService(db_session)
    faux_tracking_id = uuid4()

    with pytest.raises(EntiteNonTrouveeErreur) as exc_info:
        service.creer_voie(
            nom="Voie Orpheline",
            branche_tracking_id=faux_tracking_id,
            direction=DirectionVoie.ENTRANTE,
            position=1,
        )
    assert "n'existe pas" in str(exc_info.value)


def test_service_bloque_collision_position_voie(db_session: Session) -> None:
    service = IntersectionService(db_session)

    inter = service.creer_intersection(nom="Carrefour Test")
    branche = service.creer_branche(
        nom="Branche Nord",
        intersection_tracking_id=inter.tracking_id,
        angle_degres=0.0,
    )
    db_session.commit()

    service.creer_voie(
        nom="Voie 1",
        branche_tracking_id=branche.tracking_id,
        direction=DirectionVoie.ENTRANTE,
        position=1,
    )
    db_session.commit()

    # Tentative d'ajouter une seconde voie entrante à la même position 1
    with pytest.raises(ConflitDonneesErreur) as exc_info:
        service.creer_voie(
            nom="Voie 1 Bis",
            branche_tracking_id=branche.tracking_id,
            direction=DirectionVoie.ENTRANTE,
            position=1,
        )
    assert "existe déjà à la position 1" in str(exc_info.value)


def test_service_politique_anti_orphelins_a_la_suppression(db_session: Session) -> None:
    service = IntersectionService(db_session)

    inter = service.creer_intersection(nom="Carrefour GTA")
    branche = service.creer_branche(
        nom="Avenue Nord",
        intersection_tracking_id=inter.tracking_id,
        angle_degres=0.0,
    )
    voie = service.creer_voie(
        nom="Entrée 1",
        branche_tracking_id=branche.tracking_id,
        direction=DirectionVoie.ENTRANTE,
        position=1,
    )
    db_session.commit()

    # 1. Tentative de suppression de l'intersection sans cascade -> rejetée
    with pytest.raises(SuppressionImpossibleErreur) as exc_inter:
        service.supprimer_intersection(inter.tracking_id, forcer_cascade=False)
    assert "branche(s) lui sont encore rattachée(s)" in str(exc_inter.value)

    # 2. Tentative de suppression de la branche sans cascade -> rejetée
    with pytest.raises(SuppressionImpossibleErreur) as exc_branche:
        service.supprimer_branche(branche.tracking_id, forcer_cascade=False)
    assert "voie(s) lui sont encore rattachée(s)" in str(exc_branche.value)

    # 3. Suppression avec cascade autorisée
    service.supprimer_intersection(inter.tracking_id, forcer_cascade=True)
    db_session.commit()

    with pytest.raises(EntiteNonTrouveeErreur):
        service.obtenir_intersection(inter.tracking_id)
    with pytest.raises(EntiteNonTrouveeErreur):
        service.obtenir_branche(branche.tracking_id)
    with pytest.raises(EntiteNonTrouveeErreur):
        service.obtenir_voie(voie.tracking_id)


def test_service_recherches_et_filtres_direction(db_session: Session) -> None:
    service = IntersectionService(db_session)

    inter = service.creer_intersection(nom="Carrefour Filtres")
    branche = service.creer_branche(
        nom="Branche Est",
        intersection_tracking_id=inter.tracking_id,
        angle_degres=90.0,
    )
    v1 = service.creer_voie(
        nom="Entrée 1",
        branche_tracking_id=branche.tracking_id,
        direction=DirectionVoie.ENTRANTE,
        position=1,
    )
    v2 = service.creer_voie(
        nom="Entrée 2",
        branche_tracking_id=branche.tracking_id,
        direction=DirectionVoie.ENTRANTE,
        position=2,
    )
    v3 = service.creer_voie(
        nom="Sortie 1",
        branche_tracking_id=branche.tracking_id,
        direction=DirectionVoie.SORTANTE,
        position=1,
    )
    db_session.commit()

    # Filtre voies entrantes
    entrantes = service.rechercher_voies_entrantes(branche.tracking_id)
    assert len(entrantes) == 2
    assert [v.nom for v in entrantes] == ["Entrée 1", "Entrée 2"]

    # Filtre voies sortantes
    sortantes = service.rechercher_voies_sortantes(branche.tracking_id)
    assert len(sortantes) == 1
    assert sortantes[0].nom == "Sortie 1"

    # Liste filtrée via direction enum
    assert len(service.lister_voies(direction=DirectionVoie.ENTRANTE)) == 2
    assert len(service.lister_voies(direction=DirectionVoie.SORTANTE)) == 1
