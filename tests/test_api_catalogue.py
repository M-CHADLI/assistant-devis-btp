"""Mise à disposition du jeu de données par l'API (référentiel C5).

Ces tests construisent leur propre base, dans un répertoire temporaire, à
partir des mêmes fonctions que la chaîne. Ils ne lisent jamais
`catalogue/catalogue.sqlite3` : une suite qui dépend d'un artefact de travail
passe ou échoue selon ce qui traîne sur le disque, ce qui ne prouve rien.

Le cas de la base **absente** est testé au même titre que les autres. C'est
l'état d'un dépôt fraîchement cloné — la base est reconstructible, donc non
versionnée — et l'API doit alors répondre une erreur qui porte la commande à
lancer, pas une trace d'exception.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import authentifier

from app import catalogue_base, main
from tools.donnees import agreger as ag
from tools.donnees import importer as imp

FAMILLE = "PEINTURE_FINITION"      # correspondance proxy, densité absente
FAMILLE_EXACTE = "SOL_PARQUET"     # correspondance exacte, tout renseigné


def _jeu() -> dict:
    lignes = [
        {"reference": "LM-PE-001", "libelle": "Peinture mate blanc 10 L",
         "famille": FAMILLE, "marque": "Dulux", "unite_vente": "u",
         "contenance": "10", "contenance_unite": "L", "prix_ht": "40,00",
         "taux_promo": "30", "ean": "3269620000001",
         "disponibilite": "EN_STOCK", "date_maj": "2026-08-14"},
        {"reference": "LM-PE-002", "libelle": "Peinture satin blanc 10 L",
         "famille": FAMILLE, "marque": "Tollens", "unite_vente": "u",
         "contenance": "10", "contenance_unite": "L", "prix_ht": "32,00",
         "taux_promo": "0", "ean": "3269620000002",
         "disponibilite": "EN_STOCK", "date_maj": "2026-08-14"},
        {"reference": "LM-SO-050", "libelle": "Parquet chêne massif",
         "famille": FAMILLE_EXACTE, "marque": "Tarkett", "unite_vente": "m2",
         "contenance": "", "contenance_unite": "", "prix_ht": "62,00",
         "taux_promo": "0", "ean": "3269620000050",
         "disponibilite": "EN_STOCK", "date_maj": "2026-08-14"},
    ]
    produits, _ = ag.nettoyer_produits(lignes)
    ag.joindre(produits, {("Bois d'oeuvre (construction)", None): {
        "facteur_kgco2e_par_kg": 0.0367, "nombre_de_valeurs": 1,
        "valeur_min": 0.0367, "valeur_max": 0.0367}},
        {"chêne": {"masse_volumique_kg_m3": 750.0, "etendue": [700, 800],
                   "famille_source": "bois"}})
    return {"sources": [{"role": "fichier", "source": "export simulé",
                         "licence": "Données simulées", "lignes_brutes": 3}],
            "produits": produits}


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Un client authentifié, devant une base construite pour ce test."""
    chemin = tmp_path / "catalogue.sqlite3"
    imp.construire(_jeu(), chemin).close()
    monkeypatch.setattr(catalogue_base, "BASE", chemin)
    c = TestClient(main.app)
    authentifier(c)
    return c


@pytest.fixture
def client_sans_base(tmp_path, monkeypatch):
    monkeypatch.setattr(catalogue_base, "BASE", tmp_path / "absente.sqlite3")
    c = TestClient(main.app)
    authentifier(c)
    return c


# --- Accès -------------------------------------------------------------------

@pytest.mark.parametrize("chemin", [
    "/api/catalogue/sources", "/api/catalogue/familles",
    f"/api/catalogue/familles/{FAMILLE}/produits",
    "/api/catalogue/produits/LM-PE-001", "/api/catalogue/manques",
])
def test_le_jeu_de_donnees_n_est_pas_accessible_sans_session(chemin):
    """Le jeu est derrière la même porte que le reste. Un jeu de données
    ouvert au public serait un choix, pas un oubli — ce n'en est pas un."""
    assert TestClient(main.app).get(chemin).status_code == 401


# --- Cas dégradé : la base n'a pas été construite ----------------------------

@pytest.mark.parametrize("chemin", [
    "/api/catalogue/sources", "/api/catalogue/familles",
    f"/api/catalogue/familles/{FAMILLE}/produits",
    "/api/catalogue/produits/LM-PE-001", "/api/catalogue/manques",
])
def test_sans_base_l_api_repond_503_avec_la_commande_a_lancer(client_sans_base, chemin):
    """C'est l'état d'un dépôt fraîchement cloné. Le message doit suffire à
    s'en sortir sans lire le code."""
    reponse = client_sans_base.get(chemin)
    assert reponse.status_code == 503
    assert "tools.donnees.importer" in reponse.json()["detail"]


# --- Traçabilité -------------------------------------------------------------

def test_chaque_source_expose_sa_licence(client):
    """Un jeu republié sans licence n'est pas republiable : le destinataire ne
    sait pas ce qu'il a le droit d'en faire."""
    sources = client.get("/api/catalogue/sources").json()
    assert sources and all(s["licence"] and s["nom"] for s in sources)


# --- Familles et produits ----------------------------------------------------

def test_la_synthese_donne_les_effectifs_et_les_fourchettes(client):
    familles = {f["code"]: f for f in client.get("/api/catalogue/familles").json()}
    assert familles[FAMILLE]["nombre_de_produits"] == 2
    assert familles[FAMILLE]["prix_min"] <= familles[FAMILLE]["prix_max"]


def test_les_produits_sont_classes_sur_le_prix_remise(client):
    """40 € remisés de 30 % passent devant 32 € sans promotion : c'est le prix
    payé qui ordonne, pas le prix affiché."""
    produits = client.get(f"/api/catalogue/familles/{FAMILLE}/produits").json()
    assert [p["reference"] for p in produits] == ["LM-PE-001", "LM-PE-002"]
    assert produits[0]["prix_ht"] > produits[1]["prix_ht"], (
        "sans cette inversion, le test ne distinguerait pas les deux tris")


def test_une_famille_inconnue_est_un_404_pas_une_liste_vide(client):
    """Le client doit pouvoir distinguer « cette famille n'existe pas » de
    « elle est vide » — sans quoi une faute de frappe passe inaperçue."""
    reponse = client.get("/api/catalogue/familles/JARDINAGE/produits")
    assert reponse.status_code == 404
    assert "JARDINAGE" in reponse.json()["detail"]


def test_une_reference_inconnue_est_un_404(client):
    assert client.get("/api/catalogue/produits/LM-XX-999").status_code == 404


def test_une_reference_hostile_ne_casse_ni_la_base_ni_la_reponse(client):
    """Les paramètres liés valent aussi depuis l'extérieur."""
    assert client.get("/api/catalogue/produits/'; DROP TABLE produit; --"
                      ).status_code == 404
    assert client.get(f"/api/catalogue/familles/{FAMILLE}/produits").json()


# --- Le contrat porte l'incertitude ------------------------------------------

def test_un_produit_expose_sa_qualite_de_correspondance(client):
    """C'est ce champ qui empêche un consommateur de l'API de prendre un proxy
    pour une mesure."""
    produit = client.get("/api/catalogue/produits/LM-SO-050").json()
    assert produit["qualite_correspondance"] == "exacte"
    assert produit["masse_volumique_kg_m3"] == pytest.approx(750.0)

    approximatif = client.get("/api/catalogue/produits/LM-PE-001").json()
    assert approximatif["qualite_correspondance"] == "proxy"
    assert approximatif["masse_volumique_kg_m3"] is None, (
        "aucune source publique ne donne la densité d'une peinture : le champ "
        "doit rester vide, jamais être comblé")


def test_les_manques_sont_exposes_avec_leur_motif(client):
    """Un trou sans motif n'est pas une donnée, c'est un défaut d'affichage."""
    manques = {f["code"]: f for f in client.get("/api/catalogue/manques").json()}
    assert FAMILLE in manques
    assert manques[FAMILLE]["densite_manquante"] is True
    assert manques[FAMILLE]["reserve"], "le manque doit être motivé par écrit"
    assert FAMILLE_EXACTE not in manques


def test_les_points_de_terminaison_du_jeu_figurent_dans_l_openapi(client):
    """C5 demande une documentation au standard : elle doit décrire ces
    routes-là, pas seulement exister."""
    chemins = client.get("/openapi.json").json()["paths"]
    attendus = {"/api/catalogue/sources", "/api/catalogue/familles",
                "/api/catalogue/familles/{code}/produits",
                "/api/catalogue/produits/{reference}", "/api/catalogue/manques"}
    assert attendus <= set(chemins)
    for chemin in attendus:
        operation = chemins[chemin]["get"]
        assert operation["summary"] and operation["tags"] == ["Jeu de données"]
        assert "503" in operation["responses"]
