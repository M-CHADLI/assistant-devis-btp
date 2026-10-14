"""Injection HTML et en-têtes de sécurité.

Deux défauts trouvés le 08/09/2026 par revue de vulnérabilité :

1. Le front assemblait du HTML en chaîne et le posait dans `innerHTML` sans
   échapper la désignation des lignes de devis. Cette désignation vient du
   modèle, donc en dernier ressort de la dictée de l'artisan ou d'un ancien
   devis déposé (US-03) : de la donnée tierce, jamais du balisage.
   `app/garde_fous.py` protège l'invite du modèle contre l'injection de
   consignes ; il ne dit rien du HTML, et ce n'est pas son rôle.
2. Aucune réponse ne portait d'en-tête de sécurité.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import EN_TETES_SECURITE, app

STATIQUE = Path(__file__).resolve().parents[1] / "app" / "static"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


# --------------------------------------------------------------------------
# 1. Échappement du balisage
# --------------------------------------------------------------------------

# Les champs qui viennent du modèle, du journal ou d'un document déposé, et qui
# atterrissent dans une chaîne posée en innerHTML. La liste est explicite : un
# champ ajouté demain n'est pas couvert par magie, il s'ajoute ici.
CHAMPS_A_ECHAPPER = [
    ("index.html", "l.designation"),
    ("index.html", "l.unite"),
    ("index.html", "a.dimension_valeur"),
    ("index.html", "a.dimension_type"),
    ("index.html", "a.valeur_existante"),
    ("index.html", "c.description"),
    ("index.html", "c.horodatage"),
    ("metriques.html", "m.libelle"),
    ("metriques.html", "m.commentaire"),
]


@pytest.mark.parametrize("page, champ", CHAMPS_A_ECHAPPER)
def test_aucun_champ_tiers_n_est_interpole_sans_echappement(page: str, champ: str) -> None:
    """`${champ}` nu dans un gabarit de chaîne est une injection HTML."""
    html = (STATIQUE / page).read_text(encoding="utf-8")
    nus = re.findall(r"\$\{\s*" + re.escape(champ) + r"\s*\}", html)
    assert not nus, (
        f"{page} : {len(nus)} interpolation(s) de {champ} sans esc(). "
        "Tout ce qui finit dans innerHTML passe par esc()."
    )


@pytest.mark.parametrize("page", ["index.html", "metriques.html"])
def test_la_fonction_d_echappement_existe(page: str) -> None:
    """Un test qui cherche l'absence de `${champ}` passerait aussi si la page
    entière disparaissait. Celui-ci vérifie que le remède est bien là."""
    html = (STATIQUE / page).read_text(encoding="utf-8")
    assert "esc(" in html, f"{page} n'a pas de fonction d'échappement"
    for caractere in ("'&'", "'<'", "'>'", "'\"'", '"\'"'):
        assert caractere in html, f"{page} : esc() ne traite pas {caractere}"


def test_l_echappement_couvre_les_guillemets_pas_seulement_les_chevrons() -> None:
    """Plusieurs valeurs atterrissent dans un attribut `aria-label`, où une
    apostrophe suffit à sortir de l'attribut sans jamais écrire de chevron."""
    html = (STATIQUE / "index.html").read_text(encoding="utf-8")
    corps = html[html.index("function esc("):]
    corps = corps[:corps.index("\n}")]
    for entite in ("&amp;", "&lt;", "&gt;", "&quot;", "&#39;"):
        assert entite in corps, f"esc() ne produit pas {entite}"


# --------------------------------------------------------------------------
# 2. En-têtes de sécurité
# --------------------------------------------------------------------------

@pytest.mark.parametrize("nom", sorted(EN_TETES_SECURITE))
def test_l_en_tete_est_pose_sur_une_reponse_servie(client: TestClient, nom: str) -> None:
    reponse = client.get("/")
    assert reponse.status_code == 200
    assert reponse.headers.get(nom) == EN_TETES_SECURITE[nom]


@pytest.mark.parametrize("nom", sorted(EN_TETES_SECURITE))
def test_l_en_tete_est_pose_aussi_sur_un_refus(client: TestClient, nom: str) -> None:
    """Cas dégradé : une page d'erreur sans en-tête serait une page sans
    protection. Le 401 est la réponse la plus fréquente d'une application
    fermée par défaut (US-23)."""
    reponse = client.get("/api/catalogue/familles")
    assert reponse.status_code == 401
    assert reponse.headers.get(nom) == EN_TETES_SECURITE[nom]


def test_la_politique_interdit_l_encadrement_et_les_greffons() -> None:
    csp = EN_TETES_SECURITE["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    assert "base-uri 'none'" in csp
    assert "default-src 'self'" in csp


def test_la_politique_dit_ce_qu_elle_ne_protege_pas() -> None:
    """`'unsafe-inline'` est encore nécessaire : le front est un fichier unique
    à script et gestionnaires `onclick=` en ligne. Ce test ne le reproche pas,
    il empêche qu'on l'oublie — le jour où le script sortira dans un fichier
    servi, il tombera et rappellera de resserrer la politique."""
    csp = EN_TETES_SECURITE["Content-Security-Policy"]
    page = (STATIQUE / "index.html").read_text(encoding="utf-8")
    assert "onclick=" in page, (
        "plus aucun gestionnaire en ligne : retirer 'unsafe-inline' de script-src"
    )
    assert "'unsafe-inline'" in csp
