"""US-01 — pré-remplissage des mentions légales par le SIRET.

Ces tests portent les critères de la story, dans l'ordre où ils comptent :

1. Un SIRET mal formé est refusé **avant tout appel réseau** — et le message
   dit la correction attendue, pas seulement la faute.
2. Une indisponibilité de l'annuaire, quelle qu'en soit la cause, ne bloque
   jamais la création du compte : elle bascule en saisie manuelle.
3. Ce que l'artisan a saisi fait autorité et n'est jamais réécrit.
4. La clé d'API ne se trouve ni dans le dépôt, ni dans le code servi au
   navigateur, ni dans le journal, ni dans un message d'erreur.

Aucun de ces tests n'a besoin de réseau ni de clé : le transport est injecté.
Ce que ces tests **ne prouvent pas** est écrit à la fin du fichier.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.conftest import authentifier

from app import annuaire, main, pipeline
from app.annuaire import (Indisponible, IdentiteLegale, SiretInvalide,
                          lire_identite, normaliser_siret, rechercher)
from app.persistance import Registre

RACINE = Path(__file__).resolve().parents[1]

# SIRET réel de forme valide (clé de Luhn juste) — sert de saisie correcte.
SIRET_VALIDE = "73282932000074"
# La Poste : le seul cas français hors Luhn (somme des chiffres divisible par 5).
SIRET_LA_POSTE = "35600000000051"

REPONSE_ANNUAIRE = {
    "denomination": "MENUISERIE KARIM",
    "forme_juridique": "SASU",
    "numero_rcs": "RCS Lyon 732 829 320",
    "code_naf": "43.34Z",
    "numero_tva_intracommunautaire": "FR12732829320",
    "siege": {"adresse_ligne_1": "12 rue des Artisans",
              "code_postal": "69003", "ville": "Lyon"},
}


# --------------------------------------------------------------------------
# 1. La validation est locale, et précède le réseau
# --------------------------------------------------------------------------

def test_un_siret_bien_forme_est_normalise():
    """La forme imprimée sur le Kbis, espaces compris, est acceptée."""
    assert normaliser_siret(" 732 829 320 000 74 ") == SIRET_VALIDE


def test_le_siret_de_la_poste_echappe_a_la_cle_de_luhn():
    assert normaliser_siret(SIRET_LA_POSTE) == SIRET_LA_POSTE


@pytest.mark.parametrize("saisie", ["", "   "])
def test_un_siret_vide_demande_une_saisie_plutot_qu_une_erreur(saisie):
    with pytest.raises(SiretInvalide) as leve:
        normaliser_siret(saisie)
    assert "quatorze chiffres" in str(leve.value)


def test_neuf_chiffres_sont_reconnus_comme_un_siren():
    """Le cas le plus fréquent, et le seul qui se corrige sans le Kbis."""
    with pytest.raises(SiretInvalide) as leve:
        normaliser_siret("732829320")
    assert "SIREN" in str(leve.value)
    assert "cinq chiffres" in str(leve.value)


def test_un_message_d_erreur_enonce_la_correction_attendue():
    """RGAA 11.10 / WCAG 3.3.3 — « format invalide » ne se corrige pas."""
    with pytest.raises(SiretInvalide) as leve:
        normaliser_siret("7328293200")
    message = str(leve.value)
    assert "Il manque 4 chiffres" in message
    assert "quatorze" in message


def test_une_lettre_est_nommee_pour_etre_retiree():
    with pytest.raises(SiretInvalide) as leve:
        normaliser_siret("7328293200007X")
    assert "« X »" in str(leve.value)


def test_une_cle_de_controle_fausse_est_detectee():
    """C'est ce test qui justifie la clé de Luhn : quatorze chiffres ne
    suffisent pas à faire un SIRET, et un chiffre inversé se voit ici plutôt
    qu'après un aller-retour réseau."""
    with pytest.raises(SiretInvalide) as leve:
        normaliser_siret("73282932000075")
    assert "clé de contrôle" in str(leve.value)


def test_aucun_appel_n_est_emis_pour_un_siret_mal_forme(client, monkeypatch):
    appels: list[str] = []

    def transport_espion(siret, cle):  # pragma: no cover - ne doit pas être appelé
        appels.append(siret)
        return REPONSE_ANNUAIRE

    monkeypatch.setattr(annuaire, "_transport_http", transport_espion)
    r = client.post("/api/profil/siret", json={"siret": "123"})
    assert r.status_code == 422
    assert appels == [], "un SIRET mal formé a déclenché un appel réseau"


# --------------------------------------------------------------------------
# 2. L'indisponibilité ne bloque jamais l'inscription
# --------------------------------------------------------------------------

def test_sans_cle_configuree_la_recherche_bascule_en_saisie_manuelle(monkeypatch):
    monkeypatch.delenv(annuaire.VARIABLE_CLE, raising=False)
    resultat = rechercher(SIRET_VALIDE)
    assert isinstance(resultat, Indisponible)
    assert resultat.motif == "cle_absente"
    assert "à la main" in resultat.explication


@pytest.mark.parametrize("code,motif", [(404, "inconnu"), (402, "quota"),
                                        (503, "injoignable")])
def test_le_vrai_transport_traduit_les_codes_http_sans_citer_l_url(code, motif,
                                                                  monkeypatch):
    import urllib.error
    import urllib.request

    url_secrete = "https://api.exemple/entreprise?api_token=CLE-TRES-SECRETE"

    def ouvrir(url, timeout=None):
        raise urllib.error.HTTPError(url_secrete, code, "boum", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", ouvrir)
    with pytest.raises(annuaire._EchecAnnuaire) as leve:
        annuaire._transport_http(SIRET_VALIDE, "CLE-TRES-SECRETE")
    assert leve.value.motif == motif
    assert "CLE-TRES-SECRETE" not in str(leve.value)
    assert "api_token" not in str(leve.value)


def test_un_transport_qui_explose_ne_remonte_pas():
    """« L'inscription passe toujours » ne souffre pas d'exception — y compris
    une exception à laquelle personne n'a pensé."""
    def transport_absurde(siret, cle):
        raise RuntimeError("bibliothèque cassée")

    resultat = rechercher(SIRET_VALIDE, transport=transport_absurde, cle="x")
    assert isinstance(resultat, Indisponible)
    assert resultat.motif == "injoignable"


def test_une_reponse_vide_est_declaree_illisible_et_non_trouvee():
    resultat = rechercher(SIRET_VALIDE, transport=lambda s, c: {}, cle="x")
    assert isinstance(resultat, Indisponible)
    assert resultat.motif == "illisible"


def test_un_champ_absent_de_l_annuaire_reste_vide_et_n_est_pas_invente():
    """La correspondance des clés JSON n'a pas été vérifiée contre un appel
    réel : le code doit tolérer l'absence, jamais la combler."""
    identite = lire_identite({"denomination": "SEULE"}, SIRET_VALIDE)
    assert identite.raison_sociale == "SEULE"
    assert identite.rcs == ""
    assert identite.adresse == ""
    assert identite.ape_naf == ""


def test_une_adresse_de_siege_incomplete_ne_fait_pas_une_adresse_complete():
    identite = lire_identite({"siege": {"code_postal": "69003"}}, SIRET_VALIDE)
    assert identite.adresse == "69003"
    identite = lire_identite({"siege": "pas un objet"}, SIRET_VALIDE)
    assert identite.adresse == ""


# --------------------------------------------------------------------------
# 3. La route : pré-remplissage, autorité de l'artisan, bascule annoncée
# --------------------------------------------------------------------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "REGISTRE", Registre(racine=tmp_path))
    monkeypatch.setattr(pipeline, "appeler_modele",
                        lambda h, m, timeout=60: {"intent": "reponse",
                                                  "mention": None,
                                                  "payload": {"texte": "ok"}})
    c = TestClient(main.app)
    authentifier(c)
    return c


@pytest.fixture
def annuaire_qui_repond(monkeypatch):
    monkeypatch.setenv(annuaire.VARIABLE_CLE, "cle-de-test")
    monkeypatch.setattr(annuaire, "_transport_http",
                        lambda siret, cle: dict(REPONSE_ANNUAIRE))


def test_un_siret_valide_preremplit_les_champs_legaux(client, annuaire_qui_repond):
    r = client.post("/api/profil/siret", json={"siret": "732 829 320 00074"})
    assert r.status_code == 200
    corps = r.json()
    assert corps["origine"] == "annuaire"
    assert corps["motif"] is None
    profil = corps["profil"]
    assert profil["raison_sociale"] == "MENUISERIE KARIM"
    assert profil["rcs"] == "RCS Lyon 732 829 320"
    assert profil["ape_naf"] == "43.34Z"
    assert profil["adresse"] == "12 rue des Artisans, 69003 Lyon"
    assert profil["siret"] == SIRET_VALIDE


def test_les_champs_preremplis_portent_l_origine_annuaire(client, annuaire_qui_repond):
    r = client.post("/api/profil/siret", json={"siret": SIRET_VALIDE})
    origines = r.json()["profil"]["origines"]
    assert origines["raison_sociale"] == "annuaire"
    assert origines["ape_naf"] == "annuaire"
    # Le SIRET, lui, vient de la saisie : c'est l'artisan qui l'a tapé.
    assert origines["siret"] == "artisan"


def test_la_correction_de_l_artisan_prime_sur_l_annuaire(client, annuaire_qui_repond):
    """Critère central d'US-01 : « sa modification prime »."""
    client.post("/api/profil/siret", json={"siret": SIRET_VALIDE})
    # L'artisan corrige l'adresse : son siège diffère de l'adresse de
    # correspondance, c'est le scénario nominal de la story.
    profil = client.get("/api/profil").json()
    profil["adresse"] = "4 impasse du Chantier, 69007 Lyon"
    client.post("/api/profil", json={
        "raison_sociale": profil["raison_sociale"], "siret": profil["siret"],
        "adresse": profil["adresse"], "rcs": profil["rcs"],
        "ape_naf": profil["ape_naf"],
        "tva_intracommunautaire": profil["tva_intracommunautaire"],
        "regime_tva": profil["regime_tva"], "decennale": profil["decennale"],
        "client_nom": "", "client_adresse_chantier": "", "delai_execution": ""})

    apres = client.get("/api/profil").json()
    assert apres["origines"]["adresse"] == "artisan"
    # Une seconde recherche ne doit pas la réécrire.
    r = client.post("/api/profil/siret", json={"siret": SIRET_VALIDE})
    assert "adresse" in r.json()["champs_conserves"]
    assert r.json()["profil"]["adresse"] == "4 impasse du Chantier, 69007 Lyon"
    assert "conservé" in r.json()["explication"]


def test_une_valeur_de_l_annuaire_laissee_telle_quelle_reste_ecrasable(
        client, annuaire_qui_repond, monkeypatch):
    """Accepter sans relire n'est pas décider : enregistrer le profil sans
    toucher à un champ pré-rempli ne le transforme pas en saisie d'artisan."""
    client.post("/api/profil/siret", json={"siret": SIRET_VALIDE})
    profil = client.get("/api/profil").json()
    client.post("/api/profil", json={
        "raison_sociale": profil["raison_sociale"], "siret": profil["siret"],
        "adresse": profil["adresse"], "rcs": profil["rcs"],
        "ape_naf": profil["ape_naf"],
        "tva_intracommunautaire": profil["tva_intracommunautaire"],
        "regime_tva": profil["regime_tva"], "decennale": profil["decennale"],
        "client_nom": "", "client_adresse_chantier": "", "delai_execution": ""})
    assert client.get("/api/profil").json()["origines"]["raison_sociale"] == "annuaire"

    monkeypatch.setattr(annuaire, "_transport_http",
                        lambda s, c: dict(REPONSE_ANNUAIRE,
                                          denomination="MENUISERIE KARIM ET FILS"))
    r = client.post("/api/profil/siret", json={"siret": SIRET_VALIDE})
    assert r.json()["profil"]["raison_sociale"] == "MENUISERIE KARIM ET FILS"
    assert r.json()["champs_conserves"] == []


def test_l_indisponibilite_rend_200_et_garde_le_siret_saisi(client, monkeypatch):
    """Un 5xx ici ferait échouer une inscription parce qu'un tiers est en panne."""
    monkeypatch.delenv(annuaire.VARIABLE_CLE, raising=False)
    r = client.post("/api/profil/siret", json={"siret": SIRET_VALIDE})
    assert r.status_code == 200
    corps = r.json()
    assert corps["origine"] == "saisie_manuelle"
    assert corps["motif"] == "cle_absente"
    assert "à la main" in corps["explication"]
    # Le SIRET saisi est retenu : le formulaire manuel n'a pas à le redemander.
    assert corps["profil"]["siret"] == SIRET_VALIDE


def test_l_indisponibilite_n_efface_pas_ce_qui_etait_deja_saisi(client, monkeypatch):
    """Scénario 2 de la story : « sans perdre ce qui a déjà été saisi »."""
    monkeypatch.delenv(annuaire.VARIABLE_CLE, raising=False)
    client.post("/api/profil", json={
        "raison_sociale": "MENUISERIE KARIM", "siret": "", "adresse": "",
        "rcs": "", "ape_naf": "", "tva_intracommunautaire": "",
        "regime_tva": "reel",
        "decennale": {"assureur": "", "numero_contrat": "",
                      "couverture_geographique": "", "valide_jusqu_au": None},
        "client_nom": "", "client_adresse_chantier": "", "delai_execution": ""})
    r = client.post("/api/profil/siret", json={"siret": SIRET_VALIDE})
    assert r.json()["profil"]["raison_sociale"] == "MENUISERIE KARIM"


def test_un_annuaire_muet_sur_un_champ_le_signale_a_l_artisan(client, monkeypatch):
    monkeypatch.setenv(annuaire.VARIABLE_CLE, "cle-de-test")
    monkeypatch.setattr(annuaire, "_transport_http",
                        lambda s, c: {"denomination": "SEULE"})
    r = client.post("/api/profil/siret", json={"siret": SIRET_VALIDE})
    corps = r.json()
    assert corps["origine"] == "annuaire"
    assert "complétez" in corps["explication"]
    assert corps["profil"]["rcs"] == ""


def test_l_origine_survit_au_rechargement_du_projet(client, annuaire_qui_repond):
    """Sans persistance des origines, un rechargement ferait passer un champ
    de l'annuaire pour une saisie d'artisan — et le figerait."""
    client.post("/api/profil/siret", json={"siret": SIRET_VALIDE})
    projet_id = client.get("/api/devis").json()["projet_id"]
    # On vide le cache mémoire pour forcer la relecture du fichier : c'est le
    # trajet qu'emprunte un redémarrage du serveur.
    main.REGISTRE._cache.clear()
    relu = main.REGISTRE.obtenir(projet_id)
    assert relu.profil.origine_de("raison_sociale") == "annuaire"
    assert relu.profil.origine_de("siret") == "artisan"


def test_le_siret_est_refuse_avec_un_message_rattachable_au_champ(client):
    r = client.post("/api/profil/siret", json={"siret": "42"})
    assert r.status_code == 422
    assert "Il manque" in r.json()["detail"]


def test_la_route_exige_une_session(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "REGISTRE", Registre(racine=tmp_path))
    anonyme = TestClient(main.app)
    r = anonyme.post("/api/profil/siret", json={"siret": SIRET_VALIDE})
    assert r.status_code == 401


# --------------------------------------------------------------------------
# 4. Aucun secret d'API dans le dépôt ni dans le code client
# --------------------------------------------------------------------------

def test_la_cle_est_lue_dans_l_environnement_jamais_ecrite_dans_le_code():
    """Le nom de la variable est dans le code, sa valeur ne l'est jamais.

    Le contrôle est syntaxique et non textuel : on relit l'arbre de `app/` et
    on refuse toute chaîne littérale assignée à un nom qui sent la clé. Une
    recherche de sous-chaîne se contournerait par accident, pas celle-ci.
    """
    import ast

    suspects = ("cle", "clef", "token", "api_key", "secret", "password",
                "mot_de_passe")
    for chemin in sorted((RACINE / "app").rglob("*.py")):
        arbre = ast.parse(chemin.read_text(encoding="utf-8"), filename=str(chemin))
        for noeud in ast.walk(arbre):
            if not isinstance(noeud, ast.Assign):
                continue
            noms = [c.id.lower() for c in noeud.targets if isinstance(c, ast.Name)]
            # `VARIABLE_CLE = "BTP_PAPPERS_CLE"` déclare le **nom** d'une
            # variable d'environnement, pas une clé. C'est la seule exception,
            # et elle est nommée plutôt que laissée à une heuristique.
            if any(n.startswith("variable_") for n in noms):
                continue
            if not any(s in n for n in noms for s in suspects):
                continue
            valeur = noeud.value
            assert not (isinstance(valeur, ast.Constant)
                        and isinstance(valeur.value, str)
                        and valeur.value.strip()), (
                f"{chemin.name}:{noeud.lineno} — une clé littérale ?")

    module = (RACINE / "app" / "annuaire.py").read_text(encoding="utf-8")
    assert "os.environ.get(VARIABLE_CLE)" in module
    assert "api_token" not in annuaire.POINT_ENTREE


def test_la_cle_ne_franchit_pas_la_frontiere_du_navigateur(client,
                                                           annuaire_qui_repond):
    r = client.post("/api/profil/siret", json={"siret": SIRET_VALIDE})
    assert "cle-de-test" not in r.text
    page = (RACINE / "app" / "static" / "index.html").read_text(encoding="utf-8")
    assert "api_token" not in page
    assert "pappers" not in page.lower(), (
        "le front ne doit pas connaître l'annuaire : il parle au serveur")


def test_la_cle_n_apparait_pas_au_journal(monkeypatch, tmp_path):
    from app.observabilite import Journal

    journal = Journal(chemin=tmp_path / "journal.jsonl")
    monkeypatch.setattr(annuaire, "JOURNAL", journal)
    rechercher(SIRET_VALIDE, transport=lambda s, c: dict(REPONSE_ANNUAIRE),
               cle="CLE-TRES-SECRETE")
    contenu = (tmp_path / "journal.jsonl").read_text(encoding="utf-8")
    assert "CLE-TRES-SECRETE" not in contenu
    ligne = json.loads(contenu.strip().splitlines()[-1])
    assert ligne["evenement"] == "annuaire_interroge"
    assert ligne["resultat"] == "trouve"


# --------------------------------------------------------------------------
# Ce que ces tests ne prouvent pas
# --------------------------------------------------------------------------
#
# Aucun appel réel n'a été passé à l'annuaire : aucune clé n'est configurée sur
# cette machine. Le nom des clés JSON lues (`denomination`, `numero_rcs`,
# `code_naf`, `siege`) vient de la documentation publiée, pas d'une réponse
# observée. Ce qui est prouvé ici, c'est que le code **tolère** de se tromper :
# un champ absent reste vide, une réponse vide bascule en saisie manuelle, et
# rien n'est inventé. La correspondance elle-même reste à vérifier le jour où
# une clé sera configurée — c'est écrit dans `docs/produit/STORIES.md`, US-01.
