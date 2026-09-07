"""Tests de l'API — contrat HTTP, isolement par cookie, export.

Le modèle est neutralisé : ces tests portent sur le transport et l'état, pas
sur la qualité des sorties du LLM.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import main, pipeline
from app.persistance import Registre


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "REGISTRE", Registre(racine=tmp_path))

    def faux_modele(historique, message, timeout=60):
        return {"intent": "devis", "mention": None,
                "payload": {"pieces": ["salon"],
                            "lignes": [{"lot_code": "PEINT_FINITION",
                                        "dimension": {"type": "surface", "valeur": 22.0}}]}}

    monkeypatch.setattr(pipeline, "appeler_modele", faux_modele)
    return TestClient(main.app)


def test_page_d_accueil_se_sert_sans_dependre_du_repertoire_courant(client, monkeypatch,
                                                                   tmp_path):
    """Le chemin de index.html est absolu : lancer uvicorn d'ailleurs ne casse rien."""
    monkeypatch.chdir(tmp_path)
    r = client.get("/")
    assert r.status_code == 200
    assert "<html" in r.text.lower()


def test_devis_vide_au_premier_appel(client):
    r = client.get("/api/devis")
    assert r.status_code == 200
    corps = r.json()
    assert corps["devis"]["lignes"] == []
    assert corps["devis"]["total_ht"] == 0
    assert corps["projet_id"]


def test_un_message_alimente_le_devis(client):
    r = client.post("/api/message", json={"texte": "22 m2 de peinture dans le salon"})
    assert r.status_code == 200
    corps = r.json()
    assert corps["intent"] == "devis"
    assert len(corps["devis"]["lignes"]) == 1
    assert corps["devis"]["total_ht"] > 0


def test_le_devis_survit_a_un_rechargement(client):
    client.post("/api/message", json={"texte": "22 m2 de peinture"})
    corps = client.get("/api/devis").json()
    assert len(corps["devis"]["lignes"]) == 1


def test_deux_navigateurs_ne_partagent_pas_leur_devis(client, tmp_path, monkeypatch):
    """Le défaut corrigé : SESSION unique au niveau du module."""
    autre = TestClient(main.app)  # cookies séparés = autre navigateur
    client.post("/api/message", json={"texte": "22 m2 de peinture"})
    assert len(client.get("/api/devis").json()["devis"]["lignes"]) == 1
    assert autre.get("/api/devis").json()["devis"]["lignes"] == []


def test_reset_vide_le_projet(client):
    client.post("/api/message", json={"texte": "22 m2 de peinture"})
    r = client.post("/api/reset")
    assert r.json()["devis"]["lignes"] == []
    assert client.get("/api/devis").json()["devis"]["lignes"] == []


def test_correction_retire_la_ligne_et_laisse_une_trace(client):
    client.post("/api/message", json={"texte": "22 m2 de peinture"})
    r = client.post("/api/corriger", json={"index": 0, "description": "pas ce lot"})
    corps = r.json()
    assert corps["devis"]["lignes"] == []
    assert corps["devis"]["corrections"][0]["description"] == "pas ce lot"
    assert corps["devis"]["corrections"][0]["auteur"] == "artisan"


def test_export_rend_un_docx(client):
    client.post("/api/message", json={"texte": "22 m2 de peinture"})
    r = client.get("/api/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument")
    assert r.content[:2] == b"PK"  # un .docx est une archive zip


def test_aucune_ligne_ne_porte_de_reference_produit_inventee(client):
    """Garde-fou structurel : le modèle n'exprime jamais de prix ni de référence."""
    corps = client.post("/api/message", json={"texte": "22 m2 de peinture"}).json()
    for ligne in corps["devis"]["lignes"]:
        assert ligne["prix_unitaire_ht"] > 0  # vient du catalogue, pas du modèle
    assert corps["devis"]["total_ht"] > 0
