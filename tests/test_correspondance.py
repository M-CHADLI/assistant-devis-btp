"""La couture entre le moteur de devis et la base catalogue.

Ces tests construisent leur propre base dans un répertoire temporaire, à
partir des mêmes fonctions que la chaîne de données. Ils ne lisent jamais
`catalogue/catalogue.sqlite3` : une suite qui dépend d'un artefact de travail
passe ou échoue selon ce qui traîne sur le disque, et ne prouve rien.

Ce qu'ils tiennent, dans l'ordre d'importance :

1. **Une correspondance en attente d'arbitrage ne sert jamais.** C'est la
   propriété de sûreté du fichier : chiffrer « un tableau électrique » au prix
   d'un disjoncteur produirait un devis faux *sans le signaler*.
2. **La source de prix est explicite.** Sans `BTP_CATALOGUE_SOURCE=base`, le
   moteur ne touche pas à la base, même si elle est là.
3. **Une base absente ne casse rien.** C'est un artefact reconstructible :
   son absence est l'état normal d'un dépôt fraîchement cloné.
"""
from __future__ import annotations

import pytest

from app import catalogue, catalogue_base
from app.correspondance import (ARBITRAGE_REQUIS, ETABLIE, FAMILLES_SANS_LOT,
                                TABLE, convient, en_attente_d_arbitrage,
                                famille_de, retenus_par)
from app.devis import Devis, ajouter_ligne
from app.referentiel import REFERENTIEL
from tools.donnees import agreger as ag
from tools.donnees import importer as imp


def _ligne(reference: str, libelle: str, famille: str, unite: str,
           prix: str, contenance: str = "", unite_contenance: str = "") -> dict:
    return {"reference": reference, "libelle": libelle, "famille": famille,
            "marque": "Marque", "unite_vente": unite, "contenance": contenance,
            "contenance_unite": unite_contenance, "prix_ht": prix,
            "taux_promo": "0", "ean": "", "disponibilite": "EN_STOCK",
            "date_maj": "2026-08-14"}


#: Un produit par famille citée dans la table, plus un second, moins cher, dans
#: deux familles — pour vérifier que c'est bien le moins cher qui sort.
JEU = [
    _ligne("T-PE-001", "Peinture chère 10 L", "PEINTURE_FINITION", "u", "90,00", "10", "L"),
    _ligne("T-PE-002", "Peinture sobre 10 L", "PEINTURE_FINITION", "u", "40,00", "10", "L"),
    _ligne("T-PE-003", "Sous-couche 10 L", "PEINTURE_SOUS_COUCHE", "u", "30,00", "10", "L"),
    _ligne("T-PE-004", "Enduit 1 kg", "PEINTURE_PREPARATION", "u", "6,00", "1", "kg"),
    _ligne("T-SO-001", "Ragréage 25 kg", "SOL_PREPARATION", "u", "22,00", "25", "kg"),
    _ligne("T-SO-002", "Film pare-vapeur", "SOL_SOUS_COUCHE", "u", "18,00", "25", "m2"),
    _ligne("T-SO-003", "Stratifié cher", "SOL_STRATIFIE", "m2", "30,00"),
    _ligne("T-SO-004", "Stratifié sobre", "SOL_STRATIFIE", "m2", "11,00"),
    _ligne("T-SO-005", "Carrelage", "SOL_CARRELAGE", "m2", "28,00"),
    _ligne("T-SO-006", "Parquet contrecollé", "SOL_PARQUET", "m2", "44,00"),
    _ligne("T-PL-001", "Tube PER", "PLOMBERIE_ALIMENTATION", "ml", "3,00"),
    _ligne("T-PL-002", "Tube PVC", "PLOMBERIE_EVACUATION", "ml", "8,00"),
    _ligne("T-PL-003", "Mitigeur lavabo", "PLOMBERIE_ROBINETTERIE", "u", "70,00"),
    _ligne("T-EL-001", "Câble rigide", "ELECTRICITE_CABLE", "ml", "1,20"),
    _ligne("T-EL-002", "Prise 2P+T", "ELECTRICITE_APPAREILLAGE", "u", "8,00"),
    # Moins chère que la 2P+T, et dans la même famille : c'est exactement le
    # piège que le filtre de `ELEC_PRISE` doit éviter. Une prise réseau
    # n'alimente rien.
    _ligne("T-EL-004", "Prise RJ45 cat.6", "ELECTRICITE_APPAREILLAGE", "u", "5,00"),
    _ligne("T-EL-003", "Disjoncteur 20 A", "ELECTRICITE_TABLEAU", "u", "8,49"),
]


@pytest.fixture
def base(tmp_path, monkeypatch):
    """Une base construite pour ce test, et la source de prix pointée dessus."""
    produits, _ = ag.nettoyer_produits(JEU)
    ag.joindre(produits, {}, {})
    chemin = tmp_path / "catalogue.sqlite3"
    imp.construire({"sources": [{"role": "fichier", "source": "jeu de test",
                                 "licence": "Données simulées",
                                 "lignes_brutes": len(JEU)}],
                    "produits": produits}, chemin).close()
    monkeypatch.setattr(catalogue_base, "BASE", chemin)
    monkeypatch.setenv("BTP_CATALOGUE_SOURCE", "base")
    return chemin


# --- La table dit tout, et rien de plus -------------------------------------

def test_chaque_lot_du_referentiel_a_son_entree():
    """Un lot sans entrée tomberait dans le repli sans qu'on sache si c'est
    une décision ou un oubli. La table couvre le référentiel, exactement."""
    assert set(TABLE) == set(REFERENTIEL)


def test_chaque_entree_porte_un_etat_connu_et_une_phrase():
    """Un motif de trois mots n'explique rien : il ne survivrait pas à une
    relecture dans six mois. On exige une phrase, pas une étiquette."""
    for entree in TABLE.values():
        assert entree.etat in (ETABLIE, ARBITRAGE_REQUIS)
        assert entree.motif.endswith("."), entree.lot_code
        assert len(entree.motif.split()) >= 6, entree.lot_code


def test_un_arbitrage_dit_ce_qu_il_y_a_a_trancher():
    """Le motif d'un arbitrage n'est pas une justification, c'est un dossier :
    il doit nommer les deux choses qu'on confond et l'option de sortie."""
    for entree in en_attente_d_arbitrage():
        assert "À trancher" in entree.motif, entree.lot_code


def test_l_etat_de_l_entree_est_coherent_avec_sa_cle():
    for cle, entree in TABLE.items():
        assert entree.lot_code == cle


def test_les_familles_citees_existent_toutes_en_base(base):
    cx = catalogue_base.ouvrir()
    try:
        connues = {l["code"] for l in cx.execute("SELECT code FROM famille")}
    finally:
        cx.close()
    for entree in TABLE.values():
        assert entree.famille_code in connues, entree.famille_code


def test_les_familles_sans_lot_sont_declarees_et_exactes(base):
    """Ne pas les nommer laisserait croire que la base est entièrement
    exploitée. `SOL_PARQUET` est bien peuplée, et aucun lot ne la réclame."""
    cx = catalogue_base.ouvrir()
    try:
        connues = {l["code"] for l in cx.execute("SELECT code FROM famille")}
    finally:
        cx.close()
    orphelines = connues - {e.famille_code for e in TABLE.values()}
    assert orphelines == set(FAMILLES_SANS_LOT)


# --- Une correspondance en attente d'arbitrage ne sert jamais ---------------

def test_un_arbitrage_en_attente_ne_rend_aucune_famille():
    """La propriété de sûreté du fichier. Si elle tombe, un devis peut porter
    un prix pris dans la mauvaise famille sans que rien ne le dise."""
    for entree in en_attente_d_arbitrage():
        assert famille_de(entree.lot_code) is None


def test_il_reste_des_arbitrages_et_ils_sont_nommes():
    """Le jour où la liste se vide, ce test tombe — et c'est le moment de
    rebasculer le défaut de `BTP_CATALOGUE_SOURCE` sur `base`."""
    en_attente = {c.lot_code for c in en_attente_d_arbitrage()}
    assert en_attente == {"PLOMB_APPAREIL", "ELEC_TABLEAU"}


def test_un_lot_inconnu_ne_rend_aucune_famille():
    assert famille_de("LOT_QUI_N_EXISTE_PAS") is None


def test_un_lot_en_arbitrage_garde_le_prix_simule(base):
    """Le disjoncteur du jeu vaut 8,49 € ; le tableau simulé, 249 €. Le devis
    doit porter le second — un tableau à 8,49 € serait faux, pas prudent."""
    produit = catalogue.resoudre_produit("ELEC_TABLEAU")
    assert produit.origine == "simule"
    assert produit.prix_unitaire_ht == 249.00


def test_un_appareil_sanitaire_n_est_pas_chiffre_au_prix_d_un_mitigeur(base):
    produit = catalogue.resoudre_produit("PLOMB_APPAREIL")
    assert produit.origine == "simule"
    assert "Mitigeur" not in produit.designation


# --- La source de prix est explicite ----------------------------------------

def test_sans_variable_la_base_n_est_pas_lue(base, monkeypatch):
    """La base est là, et pourtant le moteur ne la lit pas. Brancher « si le
    fichier est présent » ferait chiffrer le même chantier différemment sur
    deux machines, sans que rien ne le dise."""
    monkeypatch.delenv("BTP_CATALOGUE_SOURCE")
    assert catalogue.source() == "simule"
    assert catalogue.resoudre_produit("PEINT_FINITION").origine == "simule"


def test_avec_la_variable_le_prix_vient_de_la_base(base):
    produit = catalogue.resoudre_produit("PEINT_FINITION")
    assert produit.origine == "base"
    assert produit.reference == "T-PE-002"      # le moins cher des deux
    assert produit.prix_unitaire_ht == 40.00


def test_le_moins_cher_de_la_famille_est_celui_qui_sort(base):
    assert catalogue.resoudre_produit("SOL_POSE_STRATIFIE").reference == "T-SO-004"


def test_le_conditionnement_de_la_base_est_repris(base):
    """La contenance vient de la base, pas d'un défaut : un seau de 10 L ne se
    compte pas comme dix seaux d'un litre."""
    produit = catalogue.resoudre_produit("PEINT_FINITION")
    assert produit.contenance == 10.0
    assert produit.unite_vente == "u"


def test_l_origine_voyage_avec_le_produit(base):
    """Le réglage est global, l'origine ne l'est pas : une ligne chiffrée
    reste explicable après un changement de source."""
    de_la_base = catalogue.resoudre_produit("PEINT_FINITION")
    en_arbitrage = catalogue.resoudre_produit("ELEC_TABLEAU")
    assert (de_la_base.origine, en_arbitrage.origine) == ("base", "simule")


# --- Une base absente ne casse rien -----------------------------------------

def test_sans_base_le_moteur_retombe_sur_le_catalogue_simule(tmp_path, monkeypatch):
    """L'état d'un dépôt fraîchement cloné : la base est reconstructible, donc
    non versionnée. Le devis doit sortir quand même."""
    monkeypatch.setattr(catalogue_base, "BASE", tmp_path / "absente.sqlite3")
    monkeypatch.setenv("BTP_CATALOGUE_SOURCE", "base")
    produit = catalogue.resoudre_produit("PEINT_FINITION")
    assert produit is not None
    assert produit.origine == "simule"


def test_une_famille_vide_retombe_sur_le_catalogue_simule(tmp_path, monkeypatch):
    """Une famille déclarée mais sans produit ne doit pas rendre `None` : le
    devis perdrait sa ligne au lieu de la chiffrer autrement."""
    produits, _ = ag.nettoyer_produits(
        [_ligne("T-EL-002", "Prise 2P+T", "ELECTRICITE_APPAREILLAGE", "u", "8,00")])
    ag.joindre(produits, {}, {})
    chemin = tmp_path / "catalogue.sqlite3"
    imp.construire({"sources": [{"role": "fichier", "source": "jeu de test",
                                 "licence": "Données simulées", "lignes_brutes": 1}],
                    "produits": produits}, chemin).close()
    monkeypatch.setattr(catalogue_base, "BASE", chemin)
    monkeypatch.setenv("BTP_CATALOGUE_SOURCE", "base")
    assert catalogue.resoudre_produit("ELEC_PRISE").origine == "base"
    assert catalogue.resoudre_produit("PEINT_FINITION").origine == "simule"


# --- De bout en bout : le devis ---------------------------------------------

def test_un_devis_chiffre_sur_la_base_porte_les_prix_de_la_base(base):
    devis = Devis()
    ajouter_ligne(devis, "PEINT_FINITION", "surface", 40.0)
    ajouter_ligne(devis, "SOL_POSE_STRATIFIE", "surface", 20.0)
    assert [l.produit.origine for l in devis.lignes] == ["base", "base"]
    assert all(l.prix_ht > 0 for l in devis.lignes)


def test_le_devis_ne_perd_aucune_ligne_en_changeant_de_source(base, monkeypatch):
    """La bascule change les prix, jamais la structure. Une ligne qui
    disparaîtrait avec la source serait un devis différent, pas un devis
    rechiffré."""
    def structure() -> list[str]:
        devis = Devis()
        for lot in REFERENTIEL:
            type_dim = {"m²": "surface", "ml": "longueur", "u": "unite"}[
                REFERENTIEL[lot].unite]
            ajouter_ligne(devis, lot, type_dim, 5.0)
        return [l.lot_code for l in devis.lignes]

    avec_base = structure()
    monkeypatch.setenv("BTP_CATALOGUE_SOURCE", "simule")
    assert structure() == avec_base == list(REFERENTIEL)


def test_aucun_prix_n_est_nul_quelle_que_soit_la_source(base):
    """Un prix à zéro passerait pour une gratuité alors qu'il signalerait une
    famille manquante."""
    for lot in REFERENTIEL:
        produit = catalogue.resoudre_produit(lot)
        assert produit is not None, lot
        assert produit.prix_unitaire_ht > 0, lot


# --- Une famille hétérogène ne se prend pas en bloc -------------------------

def test_une_prise_de_communication_ne_sert_pas_de_prise_de_courant(base):
    """Le moins cher de la famille est la RJ45 à 5 €. La prendre pour une prise
    de courant serait une substitution muette : le devis afficherait un prix
    juste pour un produit faux, ce qui est pire qu'un prix faux."""
    produit = catalogue.resoudre_produit("ELEC_PRISE")
    assert produit.reference == "T-EL-002"
    assert produit.prix_unitaire_ht == 8.00


def test_le_filtre_est_ecrit_dans_la_table_et_motive():
    """Un filtre non expliqué serait une exclusion arbitraire. Chaque lot qui
    en porte un doit dire dans son motif pourquoi sa famille ne va pas en
    bloc."""
    for entree in TABLE.values():
        if entree.retient:
            assert entree.etat == ETABLIE, (
                f"{entree.lot_code} filtre une famille qu'il n'utilise pas")
            assert "homogène" in entree.motif or "mélange" in entree.motif, (
                f"{entree.lot_code} filtre sans dire pourquoi")


def test_un_filtre_vide_prend_toute_la_famille():
    """Le cas ordinaire : une famille où seules la taille ou la finition
    varient se prend en bloc."""
    assert retenus_par("PEINT_FINITION") == ()
    assert convient("Peinture acrylique mate 2.5 L", ()) is True


def test_le_filtre_ignore_la_casse_et_les_variantes_de_libelle():
    retient = retenus_par("ELEC_PRISE")
    assert convient("PRISE 2P+T 16A", retient) is True
    assert convient("Prise Étanche IP55".upper(), retient) is True
    assert convient("Prise USB-C double", retient) is False


def test_un_lot_inconnu_ne_retient_rien():
    assert retenus_par("LOT_QUI_N_EXISTE_PAS") == ()


def test_une_famille_qui_ne_contient_plus_ce_qu_on_retient_ne_rend_rien(
        tmp_path, monkeypatch):
    """Si le rayon ne contient plus que des prises réseau, le lot ne prend
    rien et retombe sur le catalogue simulé. Prendre le voisin le plus proche
    serait la substitution muette que le filtre existe pour empêcher."""
    jeu = [_ligne("T-EL-005", "Prise RJ45 cat.6", "ELECTRICITE_APPAREILLAGE",
                  "u", "5,00")]
    produits, _ = ag.nettoyer_produits(jeu)
    ag.joindre(produits, {}, {})
    chemin = tmp_path / "catalogue.sqlite3"
    imp.construire({"sources": [{"role": "fichier", "source": "jeu de test",
                                 "licence": "Données simulées",
                                 "lignes_brutes": len(jeu)}],
                    "produits": produits}, chemin).close()
    monkeypatch.setattr(catalogue_base, "BASE", chemin)
    monkeypatch.setenv("BTP_CATALOGUE_SOURCE", "base")

    produit = catalogue.resoudre_produit("ELEC_PRISE")
    assert produit is not None, "le lot doit rester chiffrable"
    assert produit.origine == "simule"
