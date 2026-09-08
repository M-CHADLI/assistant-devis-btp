"""Chaîne de données catalogue — nettoyage, normalisation, jointure, base.

**Ces tests n'appellent aucun réseau.** Les trois extractions (fichier, API
ADEME, scraping Wikipédia) ont leur propre exécution, hors suite : un test qui
dépend d'un service distant échoue le jour où ce service tousse, et le rouge ne
dit alors rien du code. Ce qui est testé ici, c'est ce que le projet écrit :
les règles de nettoyage, la jointure, le schéma et les requêtes.

Les jeux d'entrée sont construits sur place, avec les défauts qu'un export réel
porte — prix à virgule, unité en capitales, référence vide, doublon. Chaque
test vérifie une **propriété** : la ligne fautive est rejetée *et comptée*, la
valeur est ramenée à une forme unique, le manque est déclaré au lieu d'être
comblé.
"""
from __future__ import annotations

import pytest

from tools.donnees import agreger as ag
from tools.donnees import importer as imp
from tools.donnees import requetes as rq

FAMILLE = "PEINTURE_FINITION"      # correspondance « proxy », densité absente
FAMILLE_EXACTE = "SOL_PARQUET"     # correspondance « exacte », tout renseigné


def _ligne(**surcharge) -> dict[str, str]:
    """Une ligne d'export valide, que chaque test abîme à sa façon."""
    base = {
        "reference": "LM-PE-001", "libelle": "Peinture mate blanc 10 L",
        "famille": FAMILLE, "marque": "Dulux", "unite_vente": "u",
        "contenance": "10", "contenance_unite": "L", "prix_ht": "34,90",
        "taux_promo": "10", "ean": "3269620000001",
        "disponibilite": "EN_STOCK", "date_maj": "2026-08-14",
    }
    return base | surcharge


# --- Nettoyage : ce qui est rejeté, et dit -----------------------------------

@pytest.mark.parametrize("surcharge, motif", [
    ({"reference": "  "}, "référence absente"),
    ({"prix_ht": ""}, "prix absent ou illisible"),
    ({"prix_ht": "gratuit"}, "prix absent ou illisible"),
    ({"prix_ht": "-12,00"}, "prix négatif ou nul"),
    ({"disponibilite": "ARRET"}, "produit en arrêt de commercialisation"),
    ({"unite_vente": "palette"}, "unité de vente inconnue"),
    ({"famille": "JARDINAGE"}, "famille hors périmètre"),
    ({"date_maj": "hier"}, "date de mise à jour illisible"),
])
def test_une_ligne_fautive_est_rejetee_et_son_motif_compte(surcharge, motif):
    """Un script d'agrégation qui perd des lignes en silence est indétectable
    jusqu'au jour où le devis est faux. Le motif compte autant que le rejet."""
    retenus, rejets = ag.nettoyer_produits([_ligne(**surcharge)])
    assert retenus == []
    assert rejets == {motif: 1}


def test_une_ligne_saine_traverse_le_nettoyage():
    retenus, rejets = ag.nettoyer_produits([_ligne()])
    assert len(retenus) == 1 and rejets == {}


# --- Normalisation : une seule forme en sortie -------------------------------

@pytest.mark.parametrize("brut", ["34,90", "34.90 €", " 34,90 ", "34.9"])
def test_le_prix_est_ramene_a_un_nombre_quelle_que_soit_son_ecriture(brut):
    """L'export mélange les conventions. Le devis n'en connaît qu'une."""
    retenus, _ = ag.nettoyer_produits([_ligne(prix_ht=brut)])
    assert retenus[0]["prix_ht"] == pytest.approx(34.9, abs=0.01)


@pytest.mark.parametrize("brut", ["m2", "M2", "m²"])
def test_les_ecritures_d_une_meme_unite_convergent(brut):
    retenus, _ = ag.nettoyer_produits(
        [_ligne(famille="SOL_STRATIFIE", unite_vente=brut)])
    assert retenus[0]["unite_vente"] == "m²"


def test_la_date_est_ramenee_en_iso_et_reste_comparable():
    """Deux formats dans le même fichier : sans ISO, « le plus récent » ne veut
    rien dire, et c'est cette comparaison qui départage les doublons."""
    retenus, _ = ag.nettoyer_produits(
        [_ligne(date_maj="14/08/2026"), _ligne(reference="X", date_maj="2026-08-14")])
    assert {p["date_maj"] for p in retenus} == {"2026-08-14"}


def test_un_libelle_tout_en_capitales_revient_en_casse_de_phrase():
    retenus, _ = ag.nettoyer_produits([_ligne(libelle="PEINTURE  MATE   BLANC")])
    assert retenus[0]["libelle"] == "Peinture mate blanc"


def test_le_taux_de_promotion_devient_une_fraction():
    """Le moteur de devis multiplie par (1 - taux) : un « 10 » non converti
    rendrait le produit gratuit et neuf fois remboursé."""
    retenus, _ = ag.nettoyer_produits([_ligne(taux_promo="10")])
    assert retenus[0]["taux_promo"] == pytest.approx(0.10)


def test_le_doublon_de_reference_garde_la_ligne_la_plus_recente():
    """Sur un export fournisseur, la dernière mise à jour fait foi."""
    retenus, rejets = ag.nettoyer_produits([
        _ligne(prix_ht="30,00", date_maj="2026-01-05"),
        _ligne(prix_ht="34,90", date_maj="2026-08-14"),
    ])
    assert len(retenus) == 1
    assert retenus[0]["prix_ht"] == pytest.approx(34.9)
    assert rejets == {"doublon de référence": 1}


# --- Facteurs d'émission -----------------------------------------------------

def _facteur(**surcharge) -> dict:
    base = {"Nom_base_français": "Cuivre", "Nom_attribut_français": None,
            "Code_de_la_catégorie": "Achats de biens > Métaux et produits métalliques",
            "Unité_français": "kgCO2e/kg", "Total_poste_non_décomposé": 3.0}
    return base | surcharge


def test_les_categories_hors_materiaux_sont_ecartees():
    """La recherche plein texte de l'API ramène de l'agro-alimentaire et du
    traitement de déchets. Rien de tout cela n'entre dans un devis de chantier."""
    facteurs, rejets = ag.normaliser_facteurs([
        _facteur(Code_de_la_catégorie="Achats de biens > Produits agro-alimentaires")])
    assert facteurs == {} and rejets == {"catégorie hors matériaux": 1}


def test_les_unites_non_massiques_sont_ecartees():
    """Un facteur en kgCO2e/kWh ne se convertit pas en kgCO2e/kg : il ne parle
    pas de la même grandeur. Le convertir de force fabriquerait un chiffre."""
    facteurs, rejets = ag.normaliser_facteurs([_facteur(Unité_français="kgCO2e/kWh")])
    assert facteurs == {} and rejets == {"unité non massique": 1}


def test_les_tonnes_sont_ramenees_au_kilogramme():
    facteurs, _ = ag.normaliser_facteurs(
        [_facteur(Unité_français="kgCO2e/tonne", Total_poste_non_décomposé=3000.0)])
    assert facteurs[("Cuivre", None)]["facteur_kgco2e_par_kg"] == pytest.approx(3.0)


def test_plusieurs_valeurs_donnent_une_mediane_et_gardent_leur_etendue():
    """La Base Carbone publie plusieurs procédés pour un même matériau. En
    retenir une seule serait un choix caché ; la médiane est publiée avec son
    étendue pour que l'écart reste visible."""
    facteurs, _ = ag.normaliser_facteurs([
        _facteur(Total_poste_non_décomposé=v) for v in (1.0, 3.0, 10.0)])
    resultat = facteurs[("Cuivre", None)]
    assert resultat["facteur_kgco2e_par_kg"] == pytest.approx(3.0)
    assert resultat["nombre_de_valeurs"] == 3
    assert (resultat["valeur_min"], resultat["valeur_max"]) == (1.0, 10.0)


# --- Masses volumiques -------------------------------------------------------

@pytest.mark.parametrize("brut, attendu", [
    ("2 700", 2700.0),
    ("2 700–2 800", 2750.0),
    ("610 - 980", 795.0),
    ("2 200 (armé 2 500)", 2200.0),
])
def test_les_masses_volumiques_ecrites_en_toutes_lettres_sont_lues(brut, attendu):
    """La source est encyclopédique, pas tabulaire : intervalles, parenthèses et
    espaces insécables. Une valeur illisible est rejetée, jamais devinée."""
    densites, _ = ag.normaliser_densites(
        [{"materiau": "béton[3]", "masse_volumique_brut": brut,
          "famille_source": "materiau_usuel"}])
    assert densites["béton"]["masse_volumique_kg_m3"] == pytest.approx(attendu)


def test_une_masse_volumique_illisible_est_rejetee():
    densites, rejets = ag.normaliser_densites(
        [{"materiau": "mousse", "masse_volumique_brut": "variable",
          "famille_source": "materiau_usuel"}])
    assert densites == {} and rejets == {"masse volumique illisible": 1}


# --- Jointure : le manque est déclaré, jamais comblé -------------------------

def test_la_jointure_declare_le_manque_au_lieu_de_l_inventer():
    """La source scrapée ne publie aucune masse volumique de peinture.
    Interpoler une densité plausible fabriquerait une donnée que rien ne
    soutient : le champ reste vide et porte sa réserve."""
    produits, _ = ag.nettoyer_produits([_ligne()])
    ag.joindre(produits, {}, {})
    produit = produits[0]
    assert produit["masse_volumique_kg_m3"] is None
    assert produit["source_densite"] is None
    assert produit["reserve_correspondance"], "un manque sans motif n'est pas déclaré"


def test_la_qualite_de_correspondance_accompagne_chaque_produit():
    """Rapprocher une peinture d'un « Vernis Acrylique » est un proxy, pas une
    identité. L'aval doit pouvoir faire la différence."""
    produits, _ = ag.nettoyer_produits(
        [_ligne(), _ligne(reference="LM-SO-050", famille=FAMILLE_EXACTE,
                          unite_vente="m2")])
    ag.joindre(produits, {}, {})
    qualites = {p["famille"]: p["qualite_correspondance"] for p in produits}
    assert qualites == {FAMILLE: "proxy", FAMILLE_EXACTE: "exacte"}


def test_chaque_famille_de_la_table_de_correspondance_est_motivee():
    """Une correspondance « proxy » ou « absente » sans réserve écrite serait
    un choix non justifié au milieu du jeu de données."""
    for code, regle in ag.CORRESPONDANCES.items():
        assert regle["qualite"] in ("exacte", "proxy", "absente"), code
        if regle["qualite"] != "exacte":
            assert regle["reserve"], f"{code} : correspondance non motivée"


# --- Base SQLite -------------------------------------------------------------

@pytest.fixture
def chemin_base(tmp_path):
    """Une base construite depuis un jeu agrégé minimal, en deux familles."""
    produits, _ = ag.nettoyer_produits([
        _ligne(),
        _ligne(reference="LM-PE-002", prix_ht="50,00", taux_promo="0"),
        _ligne(reference="LM-SO-050", famille=FAMILLE_EXACTE, unite_vente="m2",
               prix_ht="26,00", taux_promo="0", contenance=""),
    ])
    ag.joindre(produits, {("Bois d'oeuvre (construction)", None): {
        "facteur_kgco2e_par_kg": 0.0367, "nombre_de_valeurs": 1,
        "valeur_min": 0.0367, "valeur_max": 0.0367}}, {"chêne": {
        "masse_volumique_kg_m3": 750.0, "etendue": [700, 800],
        "famille_source": "bois"}})
    jeu = {"sources": [{"role": "fichier", "source": "export simulé",
                        "licence": "Données simulées", "lignes_brutes": 3}],
           "produits": produits}
    chemin = tmp_path / "catalogue.sqlite3"
    imp.construire(jeu, chemin).close()
    return chemin


@pytest.fixture
def base(chemin_base):
    """L'accès de l'application : en lecture, lignes comme dictionnaires."""
    cx = rq.ouvrir(chemin_base)
    yield cx
    cx.close()


@pytest.mark.parametrize("valeurs, contrainte", [
    (("X", "x", "INCONNUE", "m", "u", None, None, 1.0, 0.0, None, "2026-01-01"),
     "clé étrangère"),
    (("X", "x", FAMILLE, "m", "palette", None, None, 1.0, 0.0, None, "2026-01-01"),
     "unité de vente"),
    (("X", "x", FAMILLE, "m", "u", None, None, -1.0, 0.0, None, "2026-01-01"),
     "prix positif"),
    (("X", "x", FAMILLE, "m", "u", None, None, 1.0, 1.5, None, "2026-01-01"),
     "taux de promotion"),
])
def test_le_schema_refuse_une_ligne_incoherente(chemin_base, valeurs, contrainte):
    """Les contraintes ne sont pas décoratives : elles arrêtent au niveau de la
    base ce qu'un bogue d'agrégation laisserait passer. Elles sont éprouvées sur
    une connexion **en écriture** — sur la connexion en lecture seule, le refus
    viendrait du mode d'ouverture et ne prouverait rien du schéma."""
    import sqlite3
    cx = sqlite3.connect(chemin_base)
    cx.execute("PRAGMA foreign_keys = ON")
    try:
        with pytest.raises(sqlite3.IntegrityError):
            cx.execute("INSERT INTO produit VALUES (?,?,?,?,?,?,?,?,?,?,?)", valeurs)
    finally:
        cx.close()


def test_la_base_est_ouverte_en_lecture_seule(base):
    """Le jeu de données agrégé fait foi ; la base n'en est qu'une projection.
    Une écriture directe la ferait diverger de sa source sans trace."""
    with pytest.raises(Exception):
        base.execute("DELETE FROM produit")


def test_le_classement_se_fait_sur_le_prix_remise_pas_sur_le_prix_affiche(base):
    """Un produit à 50 € sans remise reste derrière un produit à 34,90 € remisé :
    c'est le prix payé qui ordonne, pas le prix barré."""
    produits = rq.produits_de_famille(base, FAMILLE)
    prix = [p["prix_remise_ht"] for p in produits]
    assert prix == sorted(prix)
    moins_cher = rq.moins_cher_de_famille(base, FAMILLE)
    assert moins_cher["prix_remise_ht"] == prix[0]
    assert moins_cher["prix_remise_ht"] < moins_cher["prix_ht"], (
        "sans remise dans le jeu, ce test ne prouverait rien")


def test_une_famille_vide_ne_renvoie_rien_plutot_qu_une_erreur(base):
    assert rq.produits_de_famille(base, "JARDINAGE") == []
    assert rq.moins_cher_de_famille(base, "JARDINAGE") is None
    assert rq.produit(base, "REFERENCE-INEXISTANTE") is None


def test_une_reference_hostile_est_traitee_comme_une_chaine(base):
    """Le `lot_code` peut venir d'un modèle de langage. Les paramètres liés
    font que même une chaîne SQL reste une valeur, jamais du code."""
    assert rq.produit(base, "'; DROP TABLE produit; --") is None
    assert base.execute("SELECT count(*) FROM produit").fetchone()[0] == 3


def test_la_synthese_compte_toutes_les_familles_y_compris_les_vides(base):
    """Jointure externe : une famille sans produit doit apparaître à zéro, sinon
    le trou de catalogue est invisible."""
    synthese = {f["code"]: f for f in rq.synthese_par_famille(base)}
    assert set(synthese) == {FAMILLE, FAMILLE_EXACTE}
    assert synthese[FAMILLE]["nombre_de_produits"] == 2
    assert synthese[FAMILLE]["prix_min"] <= synthese[FAMILLE]["prix_max"]


def test_les_familles_incompletes_sont_interrogeables(base):
    """Requête d'honnêteté : le manque doit pouvoir être demandé à la base, pas
    seulement lu dans un rapport d'exécution."""
    incompletes = {f["code"]: f for f in rq.familles_incompletes(base)}
    assert FAMILLE in incompletes, "la peinture n'a pas de densité : elle doit sortir"
    assert incompletes[FAMILLE]["densite_manquante"] == 1
    assert FAMILLE_EXACTE not in incompletes


def test_la_tracabilite_des_sources_survit_a_l_import(base):
    """Licence et provenance voyagent avec la donnée : une base qui les perd
    n'est plus republiable."""
    sources = rq.tracabilite(base)
    assert sources and all(s["licence"] for s in sources)
