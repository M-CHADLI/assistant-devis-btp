import math
import pytest
from app.devis import (
    Devis,
    ajouter_ligne,
    ajouter_consommables,
    consommables_par_defaut,
    LotInconnu,
)
from app.catalogue import PRIX_CONSOMMABLE_FORFAIT


def test_ajouter_ligne_lot_inconnu_levre_exception():
    """Ajouter une ligne avec un lot inconnu doit lever LotInconnu."""
    devis = Devis()
    with pytest.raises(LotInconnu):
        ajouter_ligne(devis, "LOT_INEXISTANT", "surface", 10)


def test_ajouter_ligne_peinture_finition_quantite_entiere():
    """Une ligne de peinture finition (unité "u") donne une quantité entière positive."""
    devis = Devis()
    ligne = ajouter_ligne(devis, "PEINT_FINITION", "surface", 10)
    assert isinstance(ligne.quantite_achat, int)
    assert ligne.quantite_achat > 0
    # le produit doit être vendu à l'unité "u"
    assert ligne.produit is not None and ligne.produit.unite_vente == "u"


def test_ajouter_ligne_detail_produit_quantite_non_arrondie():
    """Un produit vendu au détail (m² ou ml) ne doit pas être arrondi au supérieur."""
    devis = Devis()
    valeur = 10.0
    ligne = ajouter_ligne(devis, "SOL_POSE_STRATIFIE", "surface", valeur)
    # le produit a une unité de vente "m²"
    assert ligne.produit is not None and ligne.produit.unite_vente == "m²"
    # calcul attendu
    taux_chute = 0.08
    attendu = round(valeur * (1 + taux_chute), 2)
    assert math.isclose(ligne.quantite_achat, attendu, rel_tol=0, abs_tol=1e-9)
    # s'assurer que ce n'est pas un ceil
    assert ligne.quantite_achat == attendu and not isinstance(ligne.quantite_achat, int)


def test_taux_chute_applique_au_calcul():
    """Le taux de chute doit être appliqué pour les dimensions 'surface' ou 'longueur'."""
    devis = Devis()
    valeur = 20.0
    ligne = ajouter_ligne(devis, "PEINT_SOUS_COUCHE", "surface", valeur)
    # calcul manuel
    taux_chute = 0.05
    consommation = 0.1
    contenance = 10
    quantite_tech = valeur * (1 + taux_chute) * consommation
    quantite_par_contenance = quantite_tech / contenance
    attendu = math.ceil(quantite_par_contenance)
    assert ligne.quantite_achat == attendu


def test_taux_chute_pas_applique_pour_dimension_unite():
    """Le taux de chute ne doit pas s'appliquer quand la dimension est de type 'unite'."""
    devis = Devis()
    valeur = 5.0
    ligne = ajouter_ligne(devis, "PLOMB_ALIM", "unite", valeur)
    # aucun taux de chute appliqué ; la quantité doit être arrondie au conditionnement du produit
    from app.catalogue import resoudre_produit
    produit = resoudre_produit("PLOMB_ALIM")
    contenance = produit.contenance or 1.0
    attendu = math.ceil(valeur / contenance)
    assert ligne.quantite_achat == attendu


def test_prix_ht_avec_promo():
    """Le prix HT doit tenir compte de la remise promo du produit."""
    devis = Devis()
    valeur = 20.0
    ligne = ajouter_ligne(devis, "PEINT_SOUS_COUCHE", "surface", valeur)
    # calcul attendu
    taux_chute = 0.05
    consommation = 0.1
    contenance = 10
    quantite_tech = valeur * (1 + taux_chute) * consommation
    quantite_par_contenance = quantite_tech / contenance
    quantite = math.ceil(quantite_par_contenance)
    prix_unitaire = 34.90
    promo = 0.10
    attendu = round(quantite * prix_unitaire * (1 - promo), 2)
    assert ligne.prix_ht == attendu


def test_total_ht_somme_des_lignes():
    """Le total HT doit être la somme des prix HT des lignes du devis."""
    devis = Devis()
    ajouter_ligne(devis, "PEINT_FINITION", "surface", 5)
    ajouter_ligne(devis, "SOL_POSE_STRATIFIE", "surface", 5)
    total = sum(l.prix_ht for l in devis.lignes)
    assert devis.total_ht == round(total, 2)


def test_ventilation_tva_regroupe_par_taux():
    """La ventilation TVA doit regrouper les montants par taux différent."""
    devis = Devis()
    # ligne avec taux par défaut (10)
    ajouter_ligne(devis, "PEINT_FINITION", "surface", 5)
    # ligne avec taux 20
    ajouter_ligne(devis, "PEINT_FINITION", "surface", 5, taux_tva="20")
    ventilation = devis.ventilation_tva
    assert set(ventilation.keys()) == {"10", "20"}
    # vérifier le calcul du montant TVA pour chaque taux
    for ligne in devis.lignes:
        montant_tva = round(ligne.prix_ht * (float(ligne.taux_tva) / 100), 2)
        assert ventilation[ligne.taux_tva] >= montant_tva  # la somme inclut ce montant


def test_total_ttc_coherence():
    """total_ttc doit être total_ht + total_tva (tolérance 0.01)."""
    devis = Devis()
    ajouter_ligne(devis, "PEINT_FINITION", "surface", 5)
    ajouter_ligne(devis, "SOL_POSE_STRATIFIE", "surface", 5)
    assert abs(devis.total_ttc - (devis.total_ht + devis.total_tva)) <= 0.01


def test_acompte_30_pct():
    """L'acompte de 30 % du TTC doit être calculé correctement (tolérance 0.01)."""
    devis = Devis()
    ajouter_ligne(devis, "PEINT_FINITION", "surface", 5)
    expected = round(devis.total_ttc * 0.30, 2)
    assert devis.acompte_30_pct == expected


def test_ajouter_consommables_cree_lignes_consommable():
    """ajouter_consommables doit ajouter une ligne par item avec origine 'consommable'."""
    devis = Devis()
    items = ["ciment", "sable"]
    lignes = ajouter_consommables(devis, "PEINT_FINITION", items)
    assert len(lignes) == len(items)
    for ligne, item in zip(lignes, items):
        assert ligne.origine == "consommable"
        assert ligne.nom_lot == item
        assert ligne.prix_ht == PRIX_CONSOMMABLE_FORFAIT


def test_consommables_par_defaut_retourne_correct():
    """consommables_par_defaut renvoie les consommables associés aux lots présents."""
    lots = ["PEINT_PREP", "SOL_POSE_STRATIFIE", "PLOMB_ALIM"]
    result = consommables_par_defaut(lots)
    from app.referentiel import REFERENTIEL
    expected = {code: REFERENTIEL[code].consommables for code in lots}
    assert result == expected
