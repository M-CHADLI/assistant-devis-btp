"""US-23 — l'accès est authentifié, et le refus ne raconte rien.

Ces tests traversent le vrai chemin HTTP : pas de dépendance neutralisée, pas de
mode ouvert. C'est la condition pour qu'ils prouvent quelque chose.
"""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app import main
from app.authentification import (DUREE_JETON_S, MAX_TENTATIVES, MESSAGE_REFUS,
                                  NOM_COOKIE, Configuration, Refus, empreinte,
                                  phrase_correcte)
from app.persistance import Registre
from tests.conftest import PHRASE_TEST, authentifier


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "REGISTRE", Registre(racine=tmp_path))
    return TestClient(main.app)


# --------------------------------------------------------------------------
# Fermé par défaut
# --------------------------------------------------------------------------

def test_toute_route_hors_accueil_exige_un_jeton(client):
    """La propriété qui compte : un endpoint ajouté demain est protégé sans que
    personne n'y pense. On la vérifie route par route, pas sur un échantillon."""
    verifiees = 0
    for route in main.app.routes:
        chemin = getattr(route, "path", "")
        if not chemin or chemin in main.CHEMINS_LIBRES or "{" in chemin:
            continue
        for methode in sorted(getattr(route, "methods", set()) or {"GET"}):
            if methode in {"HEAD", "OPTIONS"}:
                continue
            reponse = client.request(methode, chemin, json={})
            assert reponse.status_code == 401, f"{methode} {chemin} n'est pas protégé"
            verifiees += 1
    assert verifiees >= 10, "le balayage des routes n'a rien testé"


def test_la_page_d_accueil_reste_ouverte(client):
    assert client.get("/").status_code == 200


def test_la_documentation_de_l_api_est_fermee(client):
    """`/docs` et `/openapi.json` décrivent l'API : ils ne sont pas la page
    d'accueil, donc ils sont fermés (docs/produit/STORIES.md US-23)."""
    assert client.get("/openapi.json").status_code == 401
    assert client.get("/docs").status_code == 401


# --------------------------------------------------------------------------
# Ouverture de session
# --------------------------------------------------------------------------

def test_la_bonne_phrase_ouvre_une_session(client):
    reponse = client.post("/api/session", json={"phrase": PHRASE_TEST})
    assert reponse.status_code == 200 and reponse.json()["ouverte"] is True
    assert reponse.json()["duree_s"] == DUREE_JETON_S
    assert client.get("/api/devis").status_code == 200


def test_le_cookie_de_session_est_httponly_et_samesite_strict(client):
    entete = client.post("/api/session",
                         json={"phrase": PHRASE_TEST}).headers["set-cookie"]
    assert "HttpOnly" in entete
    assert "SameSite=strict" in entete or "samesite=strict" in entete.lower()


def test_la_mauvaise_phrase_ne_dit_pas_pourquoi(client):
    """Phrase fausse et appel sans jeton rendent le **même** message : rien ne
    permet de distinguer « la phrase est fausse » de « il en faut une »."""
    refus_phrase = client.post("/api/session", json={"phrase": "au hasard"})
    refus_jeton = client.get("/api/devis")
    assert refus_phrase.status_code == refus_jeton.status_code == 401
    assert refus_phrase.json()["detail"] == refus_jeton.json()["detail"] == MESSAGE_REFUS


def test_fermer_la_session_reverrouille(client):
    authentifier(client)
    assert client.get("/api/devis").status_code == 200
    client.delete("/api/session")
    assert client.get("/api/devis").status_code == 401


def test_un_projet_inconnu_repond_401_et_non_404(client):
    """OWASP A01 : le contrôle d'accès passe avant la recherche de ressource, donc
    rien ne fuit sur ce qui existe ou non."""
    client.cookies.set("projet", "0123456789abcdef")
    assert client.get("/api/devis").status_code == 401


# --------------------------------------------------------------------------
# Jetons — durée bornée, signature vérifiée
# --------------------------------------------------------------------------

def test_un_jeton_perime_est_refuse():
    config = Configuration(empreinte_phrase=empreinte("x"))
    jeton = config.emettre(maintenant=time.time() - DUREE_JETON_S - 10)
    with pytest.raises(Refus):
        config.verifier(jeton)


def test_un_jeton_dont_la_charge_est_retouchee_est_refuse(client):
    authentifier(client)
    jeton = client.cookies[NOM_COOKIE]
    corps, signature = jeton.rsplit(".", 1)
    client.cookies.set(NOM_COOKIE, corps[:-2] + "AA." + signature)
    assert client.get("/api/devis").status_code == 401


def test_un_jeton_signe_par_une_autre_cle_est_refuse():
    empreinte_partagee = empreinte("x")
    emetteur = Configuration(empreinte_phrase=empreinte_partagee, cle_signature=b"a" * 32)
    verificateur = Configuration(empreinte_phrase=empreinte_partagee, cle_signature=b"b" * 32)
    with pytest.raises(Refus):
        verificateur.verifier(emetteur.emettre())


def test_la_duree_de_vie_est_bornee():
    config = Configuration(empreinte_phrase=empreinte("x"))
    charge = config.verifier(config.emettre())
    assert 0 < charge["exp"] - time.time() <= DUREE_JETON_S


# --------------------------------------------------------------------------
# Tentatives, journalisation, secrets
# --------------------------------------------------------------------------

def test_les_tentatives_sont_limitees(client):
    for _ in range(MAX_TENTATIVES):
        assert client.post("/api/session", json={"phrase": "faux"}).status_code == 401
    trop = client.post("/api/session", json={"phrase": "faux"})
    assert trop.status_code == 429
    # Même la bonne phrase attend : sinon la limite ne limite rien.
    assert client.post("/api/session", json={"phrase": PHRASE_TEST}).status_code == 429
    main.AUTH.oublier("testclient")


def test_une_session_reussie_remet_le_compteur_a_zero(client):
    client.post("/api/session", json={"phrase": "faux"})
    authentifier(client)
    assert main.AUTH.tentative_permise("testclient")


def test_l_echec_est_journalise_sans_la_phrase_essayee(tmp_path, monkeypatch):
    from app.observabilite import Journal

    journal = Journal(tmp_path / "j.jsonl")
    monkeypatch.setattr("app.authentification.JOURNAL", journal)
    config = Configuration(empreinte_phrase=empreinte("x"))
    config.enregistrer_echec("10.0.0.1")
    evenements = list(journal.evenements())
    assert evenements[-1]["evenement"] == "authentification_refusee"
    # Rien d'autre que le type, l'heure et l'origine : la phrase essayée n'a
    # aucune raison d'être dans un journal.
    assert set(evenements[-1]) == {"evenement", "horodatage", "origine"}


def test_aucune_phrase_par_defaut_dans_le_code(monkeypatch):
    """Sans phrase configurée, chaque démarrage en tire une nouvelle : il n'existe
    aucune valeur par défaut à trouver dans le dépôt."""
    monkeypatch.delenv("BTP_MOT_DE_PASSE", raising=False)
    monkeypatch.delenv("BTP_CLE_SESSION", raising=False)
    premiere, seconde = Configuration(), Configuration()
    assert premiere.phrase_engendree and seconde.phrase_engendree
    assert premiere.phrase_engendree != seconde.phrase_engendree
    assert premiere.cle != seconde.cle


def test_l_empreinte_ne_contient_pas_la_phrase():
    trace = empreinte("betonniere-orange")
    assert "betonniere" not in trace and trace.startswith("scrypt$")


def test_deux_empreintes_de_la_meme_phrase_different():
    """Sel aléatoire : deux installations avec la même phrase n'ont pas la même
    empreinte, donc une table précalculée ne sert à rien."""
    a, b = empreinte("meme-phrase"), empreinte("meme-phrase")
    assert a != b
    assert phrase_correcte("meme-phrase", a) and phrase_correcte("meme-phrase", b)


def test_une_empreinte_malformee_refuse_tout():
    for cassee in ("", "n'importe quoi", "md5$sel$valeur", "scrypt$pas-du-b64$x"):
        assert phrase_correcte("meme-phrase", cassee) is False
