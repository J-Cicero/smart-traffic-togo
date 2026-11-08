"""Tests d'intégration de l'API REST FastAPI du module Intersection."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def test_api_crud_intersection_et_absence_strict_du_champ_id(client: TestClient) -> None:
    # 1. Création
    payload = {"nom": "Carrefour Dékon", "description": "Centre de Lomé"}
    resp = client.post("/api/v1/intersections", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    # RÈGLE ABSOLUE : Pas de champ `id` technique exposé !
    assert "id" not in data
    assert "tracking_id" in data
    assert data["nom"] == "Carrefour Dékon"
    assert data["description"] == "Centre de Lomé"
    tracking_id = data["tracking_id"]

    # 2. Consultation par tracking_id
    resp_get = client.get(f"/api/v1/intersections/{tracking_id}")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert "id" not in data_get
    assert data_get["tracking_id"] == tracking_id

    # 3. Liste
    resp_list = client.get("/api/v1/intersections")
    assert resp_list.status_code == 200
    items = resp_list.json()
    assert len(items) == 1
    assert "id" not in items[0]

    # 4. Modification
    resp_put = client.put(
        f"/api/v1/intersections/{tracking_id}",
        json={"nom": "Carrefour Dékon Mis à Jour", "description": "Nouvelle desc"},
    )
    assert resp_put.status_code == 200
    assert resp_put.json()["nom"] == "Carrefour Dékon Mis à Jour"

    # 5. Suppression
    resp_del = client.delete(f"/api/v1/intersections/{tracking_id}")
    assert resp_del.status_code == 204

    # 6. Vérification 404
    resp_404 = client.get(f"/api/v1/intersections/{tracking_id}")
    assert resp_404.status_code == 404


def test_api_crud_branche_et_recherches(client: TestClient) -> None:
    # Création de l'intersection parente
    resp_inter = client.post(
        "/api/v1/intersections", json={"nom": "Carrefour GTA", "description": ""}
    )
    inter_tid = resp_inter.json()["tracking_id"]

    # 1. Création de branche
    payload_branche = {
        "nom": "Boulevard Nord",
        "intersection_tracking_id": inter_tid,
        "angle_degres": 0.0,
    }
    resp_b = client.post("/api/v1/branches", json=payload_branche)
    assert resp_b.status_code == 201
    branche_data = resp_b.json()
    assert "id" not in branche_data
    assert "intersection_id" not in branche_data
    assert branche_data["intersection_tracking_id"] == inter_tid
    branche_tid = branche_data["tracking_id"]

    # 2. Recherche des branches de l'intersection
    resp_branches_inter = client.get(f"/api/v1/intersections/{inter_tid}/branches")
    assert resp_branches_inter.status_code == 200
    assert len(resp_branches_inter.json()) == 1

    # 3. Modification de branche
    resp_b_put = client.put(
        f"/api/v1/branches/{branche_tid}",
        json={"nom": "Boulevard Nord Express", "angle_degres": 5.0},
    )
    assert resp_b_put.status_code == 200
    assert resp_b_put.json()["nom"] == "Boulevard Nord Express"

    # 4. Suppression de branche
    resp_b_del = client.delete(f"/api/v1/branches/{branche_tid}")
    assert resp_b_del.status_code == 204


def test_api_crud_voie_et_filtres_direction(client: TestClient) -> None:
    # Setup intersection & branche
    resp_inter = client.post("/api/v1/intersections", json={"nom": "Carrefour Test"})
    inter_tid = resp_inter.json()["tracking_id"]
    resp_b = client.post(
        "/api/v1/branches",
        json={"nom": "Branche Sud", "intersection_tracking_id": inter_tid},
    )
    branche_tid = resp_b.json()["tracking_id"]

    # 1. Création voie entrante
    resp_v1 = client.post(
        "/api/v1/voies",
        json={
            "nom": "Voie Entrée 1",
            "branche_tracking_id": branche_tid,
            "direction": "ENTRANTE",
            "position": 1,
        },
    )
    assert resp_v1.status_code == 201
    data_v1 = resp_v1.json()
    assert "id" not in data_v1
    assert "branche_id" not in data_v1
    voie_tid = data_v1["tracking_id"]

    # 2. Création voie sortante
    resp_v2 = client.post(
        "/api/v1/voies",
        json={
            "nom": "Voie Sortie 1",
            "branche_tracking_id": branche_tid,
            "direction": "SORTANTE",
            "position": 1,
        },
    )
    assert resp_v2.status_code == 201

    # 3. Collision de position sur la même direction
    resp_collision = client.post(
        "/api/v1/voies",
        json={
            "nom": "Voie Entrée Doublon",
            "branche_tracking_id": branche_tid,
            "direction": "ENTRANTE",
            "position": 1,
        },
    )
    assert resp_collision.status_code == 409

    # 4. Filtre par direction sur les voies
    resp_entrantes = client.get("/api/v1/voies?direction=ENTRANTE")
    assert resp_entrantes.status_code == 200
    assert len(resp_entrantes.json()) == 1

    resp_sortantes = client.get("/api/v1/voies?direction=SORTANTE")
    assert resp_sortantes.status_code == 200
    assert len(resp_sortantes.json()) == 1

    # 5. Recherche des voies de la branche
    resp_voies_branche = client.get(f"/api/v1/branches/{branche_tid}/voies")
    assert resp_voies_branche.status_code == 200
    assert len(resp_voies_branche.json()) == 2

    # 6. Modification de voie
    resp_v_put = client.put(
        f"/api/v1/voies/{voie_tid}",
        json={"nom": "Voie Entrée Principale"},
    )
    assert resp_v_put.status_code == 200
    assert resp_v_put.json()["nom"] == "Voie Entrée Principale"

    # 7. Suppression de voie
    resp_v_del = client.delete(f"/api/v1/voies/{voie_tid}")
    assert resp_v_del.status_code == 204


def test_api_rejet_parent_inexistant(client: TestClient) -> None:
    fake_tid = str(uuid4())

    # Branche avec intersection inexistante -> 404
    resp_b = client.post(
        "/api/v1/branches",
        json={"nom": "Branche", "intersection_tracking_id": fake_tid},
    )
    assert resp_b.status_code == 404

    # Voie avec branche inexistante -> 404
    resp_v = client.post(
        "/api/v1/voies",
        json={
            "nom": "Voie",
            "branche_tracking_id": fake_tid,
            "direction": "ENTRANTE",
            "position": 1,
        },
    )
    assert resp_v.status_code == 404


def test_api_rejet_suppression_orphelins(client: TestClient) -> None:
    resp_inter = client.post("/api/v1/intersections", json={"nom": "Carrefour"})
    inter_tid = resp_inter.json()["tracking_id"]

    resp_b = client.post(
        "/api/v1/branches",
        json={"nom": "Branche", "intersection_tracking_id": inter_tid},
    )
    branche_tid = resp_b.json()["tracking_id"]

    # Tentative de suppression sans forcer_cascade -> 400
    resp_del = client.delete(f"/api/v1/intersections/{inter_tid}")
    assert resp_del.status_code == 400

    # Suppression avec forcer_cascade=true -> 204
    resp_del_cascade = client.delete(
        f"/api/v1/intersections/{inter_tid}?forcer_cascade=true"
    )
    assert resp_del_cascade.status_code == 204
