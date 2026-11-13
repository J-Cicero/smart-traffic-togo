"""Tests unitaires et d'intégration pour la couche de persistance et les repositories."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.intersection.entities import (
    Branche,
    DirectionVoie,
    Intersection,
    Voie,
)
from app.intersection.repository import (
    BrancheRepository,
    IntersectionRepository,
    VoieRepository,
)


def test_intersection_repository_crud_reel(db_session: Session) -> None:
    repo = IntersectionRepository(db_session)

    # 1. Création
    inter = Intersection(
        nom="Carrefour Dékon",
        description="Carrefour central de Lomé",
        tracking_id=uuid4(),
    )
    creee = repo.creer(inter)
    db_session.commit()

    assert creee.id is not None
    assert creee.tracking_id == inter.tracking_id
    assert creee.nom == "Carrefour Dékon"

    # 2. Récupération par tracking_id
    trouvee = repo.trouver_par_tracking_id(inter.tracking_id)
    assert trouvee is not None
    assert trouvee.tracking_id == inter.tracking_id
    assert trouvee.id == creee.id

    # 3. Récupération par id interne
    trouvee_id = repo.trouver_par_id(creee.id)
    assert trouvee_id is not None
    assert trouvee_id.tracking_id == inter.tracking_id

    # 4. Liste
    inter2 = Intersection(nom="Carrefour GTA", tracking_id=uuid4())
    repo.creer(inter2)
    db_session.commit()
    toutes = repo.lister()
    assert len(toutes) == 2

    # 5. Mise à jour
    maj = repo.mettre_a_jour(
        inter.tracking_id,
        nom="Carrefour Dékon Modifié",
        description="Nouvelle description",
    )
    db_session.commit()
    assert maj is not None
    assert maj.nom == "Carrefour Dékon Modifié"
    assert maj.description == "Nouvelle description"

    # 6. Suppression
    succes = repo.supprimer(inter.tracking_id)
    db_session.commit()
    assert succes is True
    assert repo.trouver_par_tracking_id(inter.tracking_id) is None


def test_branche_repository_crud_et_recherches(db_session: Session) -> None:
    inter_repo = IntersectionRepository(db_session)
    branche_repo = BrancheRepository(db_session)

    inter = inter_repo.creer(Intersection(nom="Carrefour Aéroport", tracking_id=uuid4()))
    db_session.commit()

    # Création de branches rattachées
    b1 = Branche(
        nom="Boulevard Sud",
        intersection_tracking_id=inter.tracking_id,
        angle_degres=180.0,
        tracking_id=uuid4(),
    )
    b2 = Branche(
        nom="Boulevard Nord",
        intersection_tracking_id=inter.tracking_id,
        angle_degres=0.0,
        tracking_id=uuid4(),
    )
    creee_b1 = branche_repo.creer(b1, intersection_id=inter.id)
    creee_b2 = branche_repo.creer(b2, intersection_id=inter.id)
    db_session.commit()

    assert creee_b1.id is not None
    assert creee_b1.intersection_id == inter.id
    assert creee_b1.intersection_tracking_id == inter.tracking_id

    # Recherche par intersection
    branches_inter = branche_repo.rechercher_par_intersection(inter.tracking_id)
    assert len(branches_inter) == 2
    assert branche_repo.compter_par_intersection(inter.tracking_id) == 2

    # Mise à jour
    maj = branche_repo.mettre_a_jour(b1.tracking_id, nom="Sud Express", angle_degres=185.0)
    db_session.commit()
    assert maj is not None
    assert maj.nom == "Sud Express"
    assert maj.angle_degres == 185.0

    # Suppression
    assert branche_repo.supprimer(b2.tracking_id) is True
    db_session.commit()
    assert branche_repo.compter_par_intersection(inter.tracking_id) == 1


def test_voie_repository_crud_et_filtres_direction(db_session: Session) -> None:
    inter_repo = IntersectionRepository(db_session)
    branche_repo = BrancheRepository(db_session)
    voie_repo = VoieRepository(db_session)

    inter = inter_repo.creer(Intersection(nom="Carrefour Colombe", tracking_id=uuid4()))
    branche = branche_repo.creer(
        Branche(
            nom="Avenue Est",
            intersection_tracking_id=inter.tracking_id,
            tracking_id=uuid4(),
        ),
        intersection_id=inter.id,
    )
    db_session.commit()

    # Création de voies avec différentes directions et positions
    v_ent_1 = Voie(
        nom="Entrée 1",
        branche_tracking_id=branche.tracking_id,
        direction=DirectionVoie.ENTRANTE,
        position=1,
        tracking_id=uuid4(),
    )
    v_ent_2 = Voie(
        nom="Entrée 2",
        branche_tracking_id=branche.tracking_id,
        direction=DirectionVoie.ENTRANTE,
        position=2,
        tracking_id=uuid4(),
    )
    v_sort_1 = Voie(
        nom="Sortie 1",
        branche_tracking_id=branche.tracking_id,
        direction=DirectionVoie.SORTANTE,
        position=1,
        tracking_id=uuid4(),
    )

    voie_repo.creer(v_ent_1, branche_id=branche.id)
    voie_repo.creer(v_ent_2, branche_id=branche.id)
    voie_repo.creer(v_sort_1, branche_id=branche.id)
    db_session.commit()

    # Tests des filtres SQL par direction
    entrantes = voie_repo.rechercher_voies_entrantes(branche.tracking_id)
    sortantes = voie_repo.rechercher_voies_sortantes(branche.tracking_id)

    assert len(entrantes) == 2
    assert [v.nom for v in entrantes] == ["Entrée 1", "Entrée 2"]
    assert len(sortantes) == 1
    assert sortantes[0].nom == "Sortie 1"

    # Recherche globale par direction
    toutes_entrantes = voie_repo.rechercher_par_direction(DirectionVoie.ENTRANTE)
    assert len(toutes_entrantes) == 2

    # Détection doublon position
    assert (
        voie_repo.existe_doublon_position(
            branche.tracking_id, DirectionVoie.ENTRANTE, position=1
        )
        is True
    )
    assert (
        voie_repo.existe_doublon_position(
            branche.tracking_id, DirectionVoie.ENTRANTE, position=3
        )
        is False
    )

    # Mise à jour
    maj = voie_repo.mettre_a_jour(v_sort_1.tracking_id, nom="Sortie Principale")
    db_session.commit()
    assert maj is not None
    assert maj.nom == "Sortie Principale"

    # Suppression
    assert voie_repo.supprimer(v_ent_2.tracking_id) is True
    db_session.commit()
    assert len(voie_repo.rechercher_voies_entrantes(branche.tracking_id)) == 1


def test_contrainte_unicite_tracking_id(db_session: Session) -> None:
    repo = IntersectionRepository(db_session)
    collision_tid = uuid4()

    repo.creer(Intersection(nom="Carrefour A", tracking_id=collision_tid))
    db_session.commit()

    with pytest.raises(IntegrityError):
        repo.creer(Intersection(nom="Carrefour B", tracking_id=collision_tid))
        db_session.commit()
    db_session.rollback()


def test_contrainte_unicite_position_voie_sur_meme_branche_et_direction(
    db_session: Session,
) -> None:
    inter_repo = IntersectionRepository(db_session)
    branche_repo = BrancheRepository(db_session)
    voie_repo = VoieRepository(db_session)

    inter = inter_repo.creer(Intersection(nom="Carrefour", tracking_id=uuid4()))
    branche = branche_repo.creer(
        Branche(nom="Branche", intersection_tracking_id=inter.tracking_id, tracking_id=uuid4()),
        intersection_id=inter.id,
    )
    db_session.commit()

    voie_repo.creer(
        Voie(
            nom="Voie 1",
            branche_tracking_id=branche.tracking_id,
            direction=DirectionVoie.ENTRANTE,
            position=1,
            tracking_id=uuid4(),
        ),
        branche_id=branche.id,
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        voie_repo.creer(
            Voie(
                nom="Voie Doublon",
                branche_tracking_id=branche.tracking_id,
                direction=DirectionVoie.ENTRANTE,
                position=1,
                tracking_id=uuid4(),
            ),
            branche_id=branche.id,
        )
        db_session.commit()
    db_session.rollback()
