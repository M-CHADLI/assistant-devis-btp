"""Empaquetage — ce que l'image ne doit jamais contenir, ni faire.

Ces tests ne construisent pas l'image : ils lisent le `Dockerfile` et le
`.dockerignore`. C'est délibéré. Construire prend plusieurs minutes et exige un
démon Docker ; la suite doit rester exécutable sur n'importe quel poste. Ce que
ces tests attrapent, ce sont les régressions silencieuses — la ligne
`USER artisan` qu'on supprime pour déboguer et qu'on oublie de remettre, le
`donnees/` qui disparaît du `.dockerignore` et fait entrer des coordonnées
clients dans une image publiable.

La construction réelle, elle, est éprouvée par `.github/workflows/livraison.yml`,
qui démarre le conteneur et interroge deux routes.
"""
from __future__ import annotations

from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
DOCKERFILE = (RACINE / "Dockerfile").read_text(encoding="utf-8")
DOCKERIGNORE = (RACINE / ".dockerignore").read_text(encoding="utf-8")
LIVRAISON = (RACINE / ".github/workflows/livraison.yml").read_text(encoding="utf-8")

# Les lignes utiles, sans commentaires : une consigne écrite en commentaire ne
# s'exécute pas, et plusieurs tests ci-dessous s'y laisseraient prendre.
INSTRUCTIONS = [ligne.strip() for ligne in DOCKERFILE.splitlines()
                if ligne.strip() and not ligne.lstrip().startswith("#")]


# --- Ce que l'image ne doit pas emporter ------------------------------------

@pytest.mark.parametrize("exclu, motif", [
    ("donnees/", "coordonnées et devis clients"),
    (".env", "secrets d'exécution"),
    (".git/", "historique complet du dépôt"),
])
def test_le_contexte_de_construction_exclut_ce_qui_ne_doit_pas_etre_publie(exclu, motif):
    assert exclu in DOCKERIGNORE, f"{exclu} doit rester hors de l'image : {motif}"


def test_aucun_secret_n_est_ecrit_en_dur_dans_l_image():
    """Un `ENV BTP_MOT_DE_PASSE=…` ferait entrer une empreinte dans une couche
    d'image, où elle resterait lisible même après suppression."""
    for interdit in ("BTP_MOT_DE_PASSE", "BTP_CLE_SESSION", "GLADIA_API_KEY"):
        assert not any(ligne.startswith(("ENV ", "ARG ")) and interdit in ligne
                       for ligne in INSTRUCTIONS), f"{interdit} ne doit pas être figé"


# --- Ce que l'image doit garantir -------------------------------------------

def test_l_image_ne_tourne_pas_en_root():
    utilisateurs = [l for l in INSTRUCTIONS if l.startswith("USER ")]
    assert utilisateurs, "aucune instruction USER : le conteneur tournerait en root"
    assert utilisateurs[-1].split()[1] != "root"


def test_les_dependances_sont_figees_par_le_lock():
    """Sans `--frozen`, uv résoudrait les versions au moment de la construction :
    deux images du même commit pourraient différer."""
    sync = [l for l in INSTRUCTIONS if "uv sync" in l]
    assert sync, "aucune installation de dépendances"
    assert all("--frozen" in l for l in sync)


def test_la_construction_ne_refait_aucune_collecte():
    """La chaîne de données va chercher l'ADEME et Wikipédia. Rejouer cela à
    chaque construction rendrait l'image dépendante de la disponibilité de deux
    sources tierces — et non reproductible."""
    for collecte in ("extraire_api", "extraire_scraping", "donnees.agreger"):
        assert collecte not in DOCKERFILE, f"{collecte} n'a rien à faire à la construction"
    assert "tools.donnees.importer" in DOCKERFILE, (
        "la base doit être construite dans l'image, sinon l'API livrée répond 503")


def test_la_sonde_de_sante_interroge_un_chemin_ouvert():
    """Une sonde sur une route authentifiée mesurerait l'authentification, pas
    la santé : elle rendrait le conteneur éternellement `unhealthy`."""
    assert "HEALTHCHECK" in DOCKERFILE
    sonde = DOCKERFILE.split("HEALTHCHECK", 1)[1].split("CMD", 2)[2]
    assert "/api/" not in sonde


# --- Ce que la chaîne de livraison doit vérifier ----------------------------

def test_la_livraison_ne_publie_pas_une_pull_request():
    assert "github.event_name == 'push'" in LIVRAISON


def test_la_publication_attend_l_empaquetage_eprouve():
    assert "needs: empaquetage" in LIVRAISON


def test_la_livraison_verifie_qu_une_route_fermee_le_reste():
    """C'est la régression la plus coûteuse : livrer une image dont l'API
    répond sans session."""
    assert '"401"' in LIVRAISON
