"""US-17 — repartir d'un devis pour un chantier voisin.

Story de confort, mais elle touche deux choses qui ne le sont pas : l'identité
du devis (numéro et date) et la frontière entre structure et prix.

Le test le plus important du fichier est
`test_la_copie_revient_sans_le_moindre_prix` : recopier le chiffrage de la
semaine dernière et le présenter comme celui d'aujourd'hui produirait
exactement le prix faux que tout le projet s'interdit.
"""
from __future__ import annotations

import datetime as dt
import io

import pytest
from docx import Document
from fastapi.testclient import TestClient

from tests.conftest import authentifier

from app import main, pipeline
from app.devis import ajouter_ligne, chiffrer, numero_de_devis
from app.persistance import Registre
from app.pipeline import Correction, Escalade
from app.profil import Client, Decennale, ProfilArtisan


@pytest.fixture
def registre(tmp_path) -> Registre:
    return Registre(racine=tmp_path)


def remplir(session) -> None:
    """Un chantier complet : mentions légales, client, deux lots chiffrés,
    une correction et une escalade."""
    session.profil = ProfilArtisan(
        raison_sociale="Karim Rénovation SARL", siret="81234567800017",
        adresse="12 rue des Lilas, 69003 Lyon", rcs="RCS Lyon 812 345 678",
        ape_naf="4334Z", tva_intracommunautaire="FR40812345678",
        decennale=Decennale(assureur="AXA", numero_contrat="DEC-99812",
                            couverture_geographique="France métropolitaine",
                            valide_jusqu_au=dt.date(2027, 6, 30)),
    )
    session.client = Client(nom="Mme Dupont",
                            adresse_chantier="4 impasse du Parc, 69100 Villeurbanne")
    session.delai_execution = "3 semaines"
    session.pieces = ["salon"]
    session.lots_presents = ["PEINT_FINITION", "SOL_POSE_STRATIFIE"]
    ajouter_ligne(session.devis, "PEINT_FINITION", "surface", 42.0)
    ajouter_ligne(session.devis, "SOL_POSE_STRATIFIE", "surface", 21.0)
    chiffrer(session.devis)
    session.structure_validee = True
    session.corrections.append(Correction(
        horodatage="2026-09-01T10:00:00", auteur="artisan",
        description="surface du salon", origine="quantite",
        entree="le salon fait 40", sortie_modele="40", corrige="42"))
    session.escalades.append(Escalade(
        horodatage="2026-09-01T10:05:00", motif="demande_humain", detail="—"))
    session.historique.append({"role": "user", "content": "je refais le salon de Mme Dupont"})


# --- Identité du devis ------------------------------------------------------

def test_deux_projets_du_meme_jour_ne_portent_pas_le_meme_numero():
    """Le défaut que cette story met au jour : l'export écrivait un `-001`
    figé, donc deux devis émis le même jour portaient le même numéro."""
    jour = dt.date(2026, 9, 8)
    assert numero_de_devis("a1b2c3d4", jour) != numero_de_devis("e5f6a7b8", jour)


def test_le_numero_dit_le_jour_et_le_projet():
    numero = numero_de_devis("a1b2c3d4e5f6", dt.date(2026, 9, 8))
    assert numero == "DEV-20260908-a1b2c3"


def test_un_projet_neuf_recoit_son_identite(registre):
    projet_id, session = registre.creer()
    assert session.numero_devis.endswith(projet_id[:6])
    assert session.date_emission == dt.date.today().isoformat()


def test_l_identite_ne_bouge_pas_d_une_relecture_a_l_autre(registre):
    projet_id, session = registre.creer()
    session.date_emission = "2026-01-15"
    session.numero_devis = "DEV-20260115-abcdef"
    registre.enregistrer(projet_id, session)
    registre._cache.clear()
    assert registre.obtenir(projet_id).numero_devis == "DEV-20260115-abcdef"


def test_un_projet_ecrit_avant_la_version_5_recoit_une_identite_une_seule_fois(registre):
    """Sans cela, un devis ouvert avant cette story changerait de numéro à
    chaque export — donc changerait de document."""
    projet_id, session = registre.creer()
    session.numero_devis = ""
    session.date_emission = ""
    registre.enregistrer(projet_id, session)
    registre._cache.clear()

    attribue = registre.obtenir(projet_id).numero_devis
    assert attribue
    registre._cache.clear()
    assert registre.obtenir(projet_id).numero_devis == attribue  # relu, pas refait


def test_le_docx_porte_le_numero_du_projet(registre):
    from app.export import generer_docx
    projet_id, session = registre.creer()
    remplir(session)
    contenu = generer_docx(session.devis, session.pieces, session.profil,
                           session.client, session.delai_execution,
                           numero_devis=session.numero_devis)
    texte = "\n".join(p.text for p in Document(io.BytesIO(contenu)).paragraphs)
    assert session.numero_devis in texte
    assert "-001" not in texte


# --- Ce que la copie reprend, et ce qu'elle laisse --------------------------

def test_la_copie_reprend_les_mentions_legales_et_le_chantier(registre):
    source_id, source = registre.creer()
    remplir(source)
    registre.enregistrer(source_id, source)

    _, copie = registre.dupliquer(source_id)
    assert copie.profil.siret == "81234567800017"
    assert copie.profil.decennale.numero_contrat == "DEC-99812"
    assert copie.client.nom == "Mme Dupont"
    assert copie.delai_execution == "3 semaines"
    assert copie.pieces == ["salon"]
    assert [l.lot_code for l in copie.devis.lignes] == ["PEINT_FINITION",
                                                        "SOL_POSE_STRATIFIE"]
    assert [l.dimension_valeur for l in copie.devis.lignes] == [42.0, 21.0]


def test_la_copie_revient_sans_le_moindre_prix(registre):
    """Le catalogue est volatil, la structure ne l'est pas.

    Un prix recopié serait présenté comme celui d'aujourd'hui sans l'être :
    c'est le prix faux que tout le projet s'interdit.
    """
    source_id, source = registre.creer()
    remplir(source)
    registre.enregistrer(source_id, source)
    assert source.devis.total_ht > 0     # la source, elle, est bien chiffrée

    _, copie = registre.dupliquer(source_id)
    assert copie.devis.total_ht == 0.0
    assert not copie.devis.chiffre
    for ligne in copie.devis.lignes:
        assert ligne.produit is None
        assert ligne.prix_ht == 0.0
        assert ligne.prix_unitaire_ht == 0.0
        assert not ligne.chiffree


def test_la_copie_doit_repasser_par_la_validation_de_structure(registre):
    """HITL-2 : les surfaces vont changer, c'est le but de la duplication."""
    source_id, source = registre.creer()
    remplir(source)
    registre.enregistrer(source_id, source)
    assert source.structure_validee

    _, copie = registre.dupliquer(source_id)
    assert copie.structure_validee is False


def test_le_journal_de_corrections_ne_suit_pas(registre):
    """Critère de validation de la story, mot pour mot.

    Recopier les corrections gonflerait le signal qualité (US-25) de doublons
    qui n'ont jamais été dictés.
    """
    source_id, source = registre.creer()
    remplir(source)
    registre.enregistrer(source_id, source)

    _, copie = registre.dupliquer(source_id)
    assert copie.corrections == []
    assert copie.escalades == []


def test_l_historique_des_dictees_ne_suit_pas(registre):
    """Il porte le nom de l'autre client."""
    source_id, source = registre.creer()
    remplir(source)
    registre.enregistrer(source_id, source)

    _, copie = registre.dupliquer(source_id)
    assert copie.historique == []


def test_la_copie_porte_un_numero_distinct_et_une_date_du_jour(registre):
    source_id, source = registre.creer()
    remplir(source)
    source.numero_devis = "DEV-20260115-abcdef"
    source.date_emission = "2026-01-15"
    registre.enregistrer(source_id, source)

    projet_id, copie = registre.dupliquer(source_id)
    assert projet_id != source_id
    assert copie.numero_devis != source.numero_devis
    assert copie.date_emission == dt.date.today().isoformat()


def test_modifier_la_copie_ne_touche_pas_a_l_original(registre):
    """Une copie de surface partagerait le profil et le devis : corriger l'un
    corrigerait l'autre, en silence."""
    source_id, source = registre.creer()
    remplir(source)
    registre.enregistrer(source_id, source)

    _, copie = registre.dupliquer(source_id)
    copie.profil.raison_sociale = "Autre entreprise"
    copie.client.nom = "M. Martin"
    copie.devis.lignes.clear()
    copie.pieces.append("cuisine")

    assert source.profil.raison_sociale == "Karim Rénovation SARL"
    assert source.client.nom == "Mme Dupont"
    assert len(source.devis.lignes) == 2
    assert source.pieces == ["salon"]


def test_l_original_reste_lisible_apres_duplication(registre):
    source_id, source = registre.creer()
    remplir(source)
    registre.enregistrer(source_id, source)

    registre.dupliquer(source_id)
    registre._cache.clear()
    relu = registre.obtenir(source_id)
    assert relu.devis.total_ht > 0
    assert len(relu.corrections) == 1


def test_dupliquer_un_projet_neuf_donne_un_projet_neuf(registre):
    """Cas limite : rien à reprendre n'est pas une erreur."""
    source_id, _ = registre.creer()
    projet_id, copie = registre.dupliquer(source_id)
    assert projet_id != source_id
    assert copie.devis.lignes == []


# --- La route ---------------------------------------------------------------

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


def ouvrir(client) -> str:
    """Ouvre un projet côté serveur et rend son identifiant.

    Le cookie de projet n'est posé qu'en réponse à une requête : le lire avant
    d'en avoir émis une rendrait `None`.
    """
    client.get("/api/devis")
    return client.cookies.get("projet_id")


def test_la_route_bascule_le_navigateur_sur_la_copie(client):
    source_id = ouvrir(client)
    remplir(main.REGISTRE.obtenir(source_id))
    main.REGISTRE.enregistrer(source_id, main.REGISTRE.obtenir(source_id))

    r = client.post("/api/projet/dupliquer")
    assert r.status_code == 200
    corps = r.json()
    assert corps["source_projet_id"] == source_id
    assert corps["projet_id"] != source_id
    assert client.cookies.get("projet_id") == corps["projet_id"]


def test_la_route_dit_ce_qui_n_a_pas_suivi(client):
    """Une copie silencieusement amputée ferait croire à l'artisan qu'il tient
    son chiffrage."""
    corps = client.post("/api/projet/dupliquer").json()
    assert any("prix" in p for p in corps["non_repris"])
    assert any("validation de structure" in p for p in corps["non_repris"])
    assert any("corrections" in p for p in corps["non_repris"])
    assert corps["repris"]


def test_la_reponse_ne_porte_aucun_prix(client):
    """La copie n'est pas validée : avant HITL-2, aucune clé de prix
    n'existe dans la réponse (US-12)."""
    source_id = ouvrir(client)
    remplir(main.REGISTRE.obtenir(source_id))

    devis = client.post("/api/projet/dupliquer").json()["devis"]
    assert devis["structure_validee"] is False
    for ligne in devis["lignes"]:
        assert "prix_unitaire_ht" not in ligne
        assert "prix_ht" not in ligne


def test_le_devis_courant_apres_duplication_est_la_copie(client):
    source_id = ouvrir(client)
    remplir(main.REGISTRE.obtenir(source_id))

    client.post("/api/projet/dupliquer")
    devis = client.get("/api/devis").json()["devis"]
    assert devis["structure_validee"] is False


def test_l_export_de_la_copie_est_refuse_tant_que_rien_n_est_valide(client):
    source_id = ouvrir(client)
    remplir(main.REGISTRE.obtenir(source_id))
    client.post("/api/projet/dupliquer")

    r = client.get("/api/export")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "structure_non_validee"


def test_le_journal_ne_porte_pas_le_nom_du_client_duplique(client):
    from app.observabilite import JOURNAL
    source_id = ouvrir(client)
    remplir(main.REGISTRE.obtenir(source_id))

    client.post("/api/projet/dupliquer")
    trace = str(JOURNAL.evenements())
    assert "projet_duplique" in trace
    assert "Dupont" not in trace


def test_la_duplication_exige_une_session():
    anonyme = TestClient(main.app)
    assert anonyme.post("/api/projet/dupliquer").status_code == 401
