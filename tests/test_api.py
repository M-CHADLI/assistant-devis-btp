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
    # Un devis neuf n'a pas de total : il n'a pas encore été chiffré (US-12).
    assert corps["devis"]["total_ht"] is None
    assert corps["projet_id"]


def test_un_message_alimente_le_devis(client):
    r = client.post("/api/message", json={"texte": "22 m2 de peinture dans le salon"})
    assert r.status_code == 200
    corps = r.json()
    assert corps["intent"] == "devis"
    assert len(corps["devis"]["lignes"]) == 1
    assert corps["devis"]["total_ht"] is None  # HITL-2 : pas encore chiffré

    chiffre = client.post("/api/valider-structure").json()["devis"]
    assert chiffre["total_ht"] > 0


# --- HITL-2 : valider la structure avant de voir le moindre prix (US-12) ----

def test_aucun_montant_n_est_transmis_avant_validation(client):
    """Critère US-12, au sens littéral : la réponse ne contient aucune clé de
    prix — pas même vide."""
    corps = client.post("/api/message", json={"texte": "22 m2 de peinture"}).json()
    devis = corps["devis"]

    assert devis["structure_validee"] is False
    assert devis["lignes"], "la structure, elle, doit être là"
    for ligne in devis["lignes"]:
        assert "prix_unitaire_ht" not in ligne
        assert "prix_ht" not in ligne
        assert "taux_tva" not in ligne
        assert ligne["quantite"] > 0  # quantité technique : c'est du métier, pas du prix
    for total in ("total_ht", "total_tva", "total_ttc", "acompte_30_pct"):
        assert devis[total] is None
    assert devis["ventilation_tva"] == {}


def test_la_validation_de_structure_declenche_le_chiffrage(client):
    client.post("/api/message", json={"texte": "22 m2 de peinture"})
    devis = client.post("/api/valider-structure").json()["devis"]

    assert devis["structure_validee"] is True
    assert devis["total_ht"] > 0
    assert all(l["prix_ht"] >= 0 for l in devis["lignes"])


def test_la_structure_non_validee_survit_au_rechargement_sans_prix(client):
    """Scénario dégradé US-12 : il ferme la page avant validation ; rien n'est
    chiffré, la structure est retrouvée telle quelle."""
    client.post("/api/message", json={"texte": "22 m2 de peinture"})
    devis = client.get("/api/devis").json()["devis"]
    assert devis["structure_validee"] is False
    assert devis["total_ht"] is None
    assert len(devis["lignes"]) == 1


def test_valider_une_structure_vide_est_refuse(client):
    assert client.post("/api/valider-structure").status_code == 409


def test_l_export_exige_la_validation_de_structure(client):
    client.post("/api/profil", json=PROFIL_COMPLET)
    client.post("/api/message", json={"texte": "22 m2 de peinture"})
    r = client.get("/api/export")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "structure_non_validee"


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


PROFIL_COMPLET = {
    "raison_sociale": "Karim Rénovation SARL", "siret": "81234567800017",
    "adresse": "12 rue des Lilas, 69003 Lyon", "rcs": "RCS Lyon 812 345 678",
    "ape_naf": "4334Z", "tva_intracommunautaire": "FR40812345678",
    "regime_tva": "reel",
    "decennale": {"assureur": "AXA", "numero_contrat": "DEC-99812",
                  "couverture_geographique": "France métropolitaine",
                  "valide_jusqu_au": "2027-06-30"},
    "client_nom": "Mme Dupont",
    "client_adresse_chantier": "4 impasse du Parc, 69100 Villeurbanne",
    "delai_execution": "3 semaines",
}


def test_export_refuse_tant_que_les_mentions_legales_manquent(client):
    """US-15 — cas dégradé : mieux vaut pas de devis qu'un devis non conforme."""
    client.post("/api/message", json={"texte": "22 m2 de peinture"})
    client.post("/api/valider-structure")
    r = client.get("/api/export")
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert "votre numéro SIRET" in detail["manquantes"]


def test_export_rend_un_docx(client):
    client.post("/api/profil", json=PROFIL_COMPLET)
    client.post("/api/message", json={"texte": "22 m2 de peinture"})
    client.post("/api/valider-structure")
    r = client.get("/api/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument")
    assert r.content[:2] == b"PK"  # un .docx est une archive zip


def test_le_profil_se_relit_et_signale_ce_qui_manque(client):
    vide = client.get("/api/profil").json()
    assert "votre numéro SIRET" in vide["mentions_manquantes"]

    ecrit = client.post("/api/profil", json=PROFIL_COMPLET).json()
    assert ecrit["mentions_manquantes"] == []
    assert client.get("/api/profil").json()["siret"] == "81234567800017"


def test_le_regime_de_tva_du_profil_se_lit_dans_le_devis(client):
    franchise = dict(PROFIL_COMPLET, regime_tva="franchise_293b",
                     tva_intracommunautaire="")
    client.post("/api/profil", json=franchise)
    corps = client.post("/api/message", json={"texte": "22 m2 de peinture"}).json()
    assert corps["devis"]["franchise_tva"] is True
    assert corps["devis"]["mentions_manquantes"] == []
    client.post("/api/valider-structure")
    assert client.get("/api/export").status_code == 200


def test_aucune_ligne_ne_porte_de_reference_produit_inventee(client):
    """Garde-fou structurel : le modèle n'exprime jamais de prix ni de référence."""
    client.post("/api/message", json={"texte": "22 m2 de peinture"})
    devis = client.post("/api/valider-structure").json()["devis"]
    for ligne in devis["lignes"]:
        assert ligne["prix_unitaire_ht"] > 0  # vient du catalogue, pas du modèle
    assert devis["total_ht"] > 0


def _client_hors_bornes(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "REGISTRE", Registre(racine=tmp_path))

    def faux_modele(historique, message, timeout=60):
        return {"intent": "devis", "mention": None,
                "payload": {"pieces": ["salon"],
                            "lignes": [{"lot_code": "PEINT_FINITION",
                                        "dimension": {"type": "surface", "valeur": 2200.0}}]}}

    monkeypatch.setattr(pipeline, "appeler_modele", faux_modele)
    return TestClient(main.app)


def test_une_quantite_hors_bornes_remonte_a_l_interface(tmp_path, monkeypatch):
    c = _client_hors_bornes(tmp_path, monkeypatch)
    corps = c.post("/api/message", json={"texte": "2200 m2"}).json()
    assert corps["devis"]["lignes"] == []
    assert len(corps["devis"]["a_confirmer"]) == 1
    assert corps["devis"]["a_confirmer"][0]["dimension_valeur"] == 2200.0


def test_l_artisan_confirme_par_l_api(tmp_path, monkeypatch):
    c = _client_hors_bornes(tmp_path, monkeypatch)
    c.post("/api/message", json={"texte": "2200 m2"})
    corps = c.post("/api/quantite", json={"index": 0, "action": "confirmer"}).json()
    assert len(corps["devis"]["lignes"]) == 1
    assert corps["devis"]["a_confirmer"] == []


def test_l_artisan_abandonne_par_l_api(tmp_path, monkeypatch):
    c = _client_hors_bornes(tmp_path, monkeypatch)
    c.post("/api/message", json={"texte": "2200 m2"})
    corps = c.post("/api/quantite", json={"index": 0, "action": "abandonner"}).json()
    assert corps["devis"]["lignes"] == []
    assert corps["devis"]["a_confirmer"] == []


def test_action_inconnue_est_refusee(tmp_path, monkeypatch):
    c = _client_hors_bornes(tmp_path, monkeypatch)
    c.post("/api/message", json={"texte": "2200 m2"})
    assert c.post("/api/quantite", json={"index": 0, "action": "n_importe_quoi"}).status_code == 422
    assert c.post("/api/quantite", json={"index": 9, "action": "confirmer"}).status_code == 404


def test_l_attente_survit_a_un_rechargement(tmp_path, monkeypatch):
    c = _client_hors_bornes(tmp_path, monkeypatch)
    c.post("/api/message", json={"texte": "2200 m2"})
    assert len(c.get("/api/devis").json()["devis"]["a_confirmer"]) == 1


# --- HITL-0 : relecture de la dictée (US-05) --------------------------------

@pytest.fixture
def client_relecture(client, monkeypatch):
    """La reformulation est simulée : ces tests portent sur le contrat HTTP."""
    from app.transcription import Relecture
    monkeypatch.setattr(
        main, "relire",
        lambda texte: Relecture(brut=texte, propose=f"{texte.strip()} (reformulé)"))
    return client


def test_la_relecture_ne_declenche_aucun_traitement(client_relecture):
    """Critère US-05 : aucune étape aval avant validation explicite."""
    r = client_relecture.post("/api/transcription",
                              json={"texte": "22 m2 de peinture"})
    assert r.status_code == 200
    assert r.json()["propose"] == "22 m2 de peinture (reformulé)"

    devis = client_relecture.get("/api/devis").json()["devis"]
    assert devis["lignes"] == []  # le pipeline n'a pas tourné


def test_la_validation_declenche_le_traitement_et_journalise_la_correction(
        client_relecture):
    client_relecture.post("/api/transcription", json={"texte": "2 m2 de peinture"})
    r = client_relecture.post("/api/transcription/valider",
                              json={"propose": "2 m2 de peinture (reformulé)",
                                    "texte": "22 m2 de peinture"})
    assert r.status_code == 200
    corps = r.json()
    assert corps["texte_traite"] == "22 m2 de peinture"
    assert corps["devis"]["lignes"]  # le pipeline a tourné, cette fois

    trace = corps["devis"]["corrections"][0]
    assert trace["auteur"] == "artisan"
    assert "transcription corrigée" in trace["description"]


def test_une_validation_sans_correction_ne_laisse_pas_de_trace(client_relecture):
    r = client_relecture.post("/api/transcription/valider",
                              json={"propose": "22 m2 de peinture",
                                    "texte": "22 m2 de peinture"})
    assert r.json()["devis"]["corrections"] == []


def test_l_api_expose_les_messages_de_cadrage_a_part(client):
    """L'interface doit pouvoir les annoncer en role="alert" sans deviner
    leur texte (docs/STORIES.md US-20)."""
    r = client.post("/api/message", json={"texte": "d'où vient cette fissure ?"})
    assert r.status_code == 200
    data = r.json()
    assert data["intent"] == "hors_perimetre"
    assert data["cadrages"] and data["cadrages"][0] in data["messages"]


def test_un_tour_ordinaire_ne_porte_aucun_cadrage(client):
    r = client.post("/api/message", json={"texte": "je refais le salon, 22 m² de peinture"})
    assert r.json()["cadrages"] == []


def test_une_quantite_en_attente_porte_le_nom_metier_du_lot(client, monkeypatch):
    """L'artisan arbitre sur « Peinture de finition », pas sur PEINT_FINITION."""
    def hors_bornes(historique, message, timeout=60):
        return {"intent": "devis", "mention": None,
                "payload": {"pieces": ["salon"],
                            "lignes": [{"lot_code": "PEINT_FINITION",
                                        "dimension": {"type": "surface", "valeur": 2200.0}}]}}

    monkeypatch.setattr(pipeline, "appeler_modele", hors_bornes)
    r = client.post("/api/message", json={"texte": "2200 m² de peinture"})
    attente = r.json()["devis"]["a_confirmer"][0]
    assert attente["lot_nom"] and attente["lot_nom"] != attente["lot_code"]


def test_le_tableau_de_bord_reste_lisible_modele_arrete(client, monkeypatch):
    """Scénario dégradé US-24 : les métriques se lisent dans le journal, pas
    dans le modèle."""
    from app.llm import ModeleInjoignable

    def injoignable(historique, message, timeout=60):
        raise ModeleInjoignable("service arrêté")

    monkeypatch.setattr(pipeline, "appeler_modele", injoignable)
    client.post("/api/message", json={"texte": "22 m² de peinture"})
    r = client.get("/api/metriques")
    assert r.status_code == 200
    assert len(r.json()["metriques"]) == 8
    assert client.get("/metriques").status_code == 200
