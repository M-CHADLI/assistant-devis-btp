"""Moteur de devis — quantités, conditionnement, prix, TVA.

**Ces tests ne recopient aucune valeur métier.** Taux de chute, rendement,
contenance, prix et promotion sont lus dans `REFERENTIEL` et dans le catalogue
au moment du test. Une version antérieure les écrivait en dur (0,05 · 0,1 · 10 ·
34,90 · 0,10) : le jour où un rendement change, la suite tombait alors que le
code était juste, et le rouge ne disait rien du défaut.

Lire la valeur depuis la source expose au risque inverse — un test qui recopie
la formule du code ne prouve plus rien. La parade est ailleurs : chaque test
vérifie une **propriété** (la chute s'applique ici et pas là, l'emballage
s'arrondit au-dessus, la promotion descend le prix), et
`test_le_jeu_de_lots_exerce_bien_les_proprietes_testees` garantit que les lots
choisis portent encore de quoi l'exercer. Si un taux de chute tombait à zéro
dans le référentiel, c'est ce test-là qui parlerait, pas les autres en silence.
"""
from __future__ import annotations

import math

import pytest

from app.catalogue import PRIX_CONSOMMABLE_FORFAIT, resoudre_produit
from app.devis import (Devis, LotInconnu, ajouter_consommables, ajouter_ligne,
                       consommables_par_defaut)
from app.referentiel import REFERENTIEL

# Les lots sur lesquels s'appuient les tests ci-dessous, choisis pour la
# propriété qu'ils exercent. `test_le_jeu_de_lots_exerce_bien_les_proprietes_
# testees` vérifie que ce choix reste valide.
LOT_EMBALLE = "PEINT_SOUS_COUCHE"      # vendu au seau : arrondi au supérieur, promotion
LOT_AU_DETAIL = "SOL_POSE_STRATIFIE"   # vendu au m² : quantité fractionnaire
LOT_A_L_UNITE = "PLOMB_ALIM"           # dimension en unités : pas de chute


def _attendu_technique(lot_code: str, valeur: float, avec_chute: bool) -> float:
    """La quantité technique telle que le métier la calcule, sans le catalogue."""
    lot = REFERENTIEL[lot_code]
    chute = lot.taux_chute if avec_chute else 0.0
    return round(valeur * (1 + chute) * (lot.consommation_par_unite or 1.0), 2)


# --- Garde-fou du jeu de données -------------------------------------------

def test_le_jeu_de_lots_exerce_bien_les_proprietes_testees():
    """Si le référentiel ou le catalogue évoluait au point que ces lots
    n'exercent plus rien, les tests suivants passeraient sans rien prouver.
    C'est ce test qui doit rougir en premier, pas eux."""
    assert REFERENTIEL[LOT_EMBALLE].taux_chute > 0, "plus de chute à appliquer"
    assert REFERENTIEL[LOT_AU_DETAIL].taux_chute > 0
    assert REFERENTIEL[LOT_A_L_UNITE].unite == "ml"

    emballe = resoudre_produit(LOT_EMBALLE)
    assert emballe.unite_vente == "u" and emballe.contenance, "plus de conditionnement"
    assert emballe.promo_pct > 0, "plus aucune promotion : le test de remise ne prouve rien"
    assert resoudre_produit(LOT_AU_DETAIL).unite_vente in ("m²", "ml")


# --- Cas dégradé ------------------------------------------------------------

def test_un_lot_inconnu_est_refuse_et_nomme():
    """Le modèle peut inventer un `lot_code` : le moteur ne doit ni deviner ni
    laisser passer une ligne vide."""
    devis = Devis()
    with pytest.raises(LotInconnu) as erreur:
        ajouter_ligne(devis, "LOT_INEXISTANT", "surface", 10)
    assert "LOT_INEXISTANT" in str(erreur.value)


# --- Quantité technique : rendement et taux de chute ------------------------

def test_la_chute_s_applique_a_une_surface():
    ligne = ajouter_ligne(Devis(), LOT_EMBALLE, "surface", 20.0)
    assert ligne.quantite_technique == _attendu_technique(LOT_EMBALLE, 20.0, True)


def test_la_chute_ne_s_applique_pas_a_une_dimension_en_unites():
    """Cinq prises posées ne produisent pas cinq prises et demie : la chute est
    une perte de matière au mètre, pas au comptage."""
    ligne = ajouter_ligne(Devis(), LOT_A_L_UNITE, "unite", 5.0)
    assert ligne.quantite_technique == _attendu_technique(LOT_A_L_UNITE, 5.0, False)


def test_la_quantite_technique_est_exprimee_dans_l_unite_du_lot():
    ligne = ajouter_ligne(Devis(), LOT_AU_DETAIL, "surface", 10.0)
    assert ligne.unite_technique == REFERENTIEL[LOT_AU_DETAIL].unite


# --- Conditionnement : du besoin technique à la quantité vendue -------------

def test_un_produit_emballe_s_arrondit_au_conditionnement_superieur():
    """On n'achète pas 2,3 seaux. Arrondir en dessous laisserait le chantier à
    court de peinture."""
    produit = resoudre_produit(LOT_EMBALLE)
    ligne = ajouter_ligne(Devis(), LOT_EMBALLE, "surface", 20.0)
    attendu = math.ceil(ligne.quantite_technique / produit.contenance)
    assert ligne.quantite_achat == attendu
    assert float(ligne.quantite_achat).is_integer()


def test_un_produit_vendu_au_detail_n_est_pas_arrondi():
    """Le stratifié se vend au m² : arrondir au m² supérieur ferait payer au
    client une découpe qu'il n'achète pas."""
    ligne = ajouter_ligne(Devis(), LOT_AU_DETAIL, "surface", 10.0)
    assert ligne.quantite_achat == round(ligne.quantite_technique, 2)
    assert not float(ligne.quantite_achat).is_integer(), (
        "la valeur choisie doit produire une fraction, sinon le test ne montre rien")


# --- Prix : le catalogue s'accroche sur la structure ------------------------

def test_la_promotion_du_catalogue_descend_le_prix_de_la_ligne():
    produit = resoudre_produit(LOT_EMBALLE)
    ligne = ajouter_ligne(Devis(), LOT_EMBALLE, "surface", 20.0)
    plein_tarif = ligne.quantite_achat * produit.prix_unitaire_ht
    assert ligne.prix_ht == round(plein_tarif * (1 - produit.promo_pct), 2)
    assert ligne.prix_ht < plein_tarif


def test_chaque_ligne_se_recalcule_depuis_ses_propres_colonnes():
    """La propriété que le client vérifie sur le devis papier : quantité × prix
    unitaire, remise déduite, égale le total de la ligne."""
    devis = Devis()
    for lot in (LOT_EMBALLE, LOT_AU_DETAIL, LOT_A_L_UNITE):
        ajouter_ligne(devis, lot, "unite" if lot == LOT_A_L_UNITE else "surface", 12.0)
    for ligne in devis.lignes:
        promo = ligne.produit.promo_pct if ligne.produit else 0.0
        attendu = ligne.quantite_achat * ligne.prix_unitaire_ht * (1 - promo)
        assert abs(ligne.prix_ht - attendu) < 0.01, ligne


def test_le_total_ht_est_la_somme_des_lignes():
    devis = Devis()
    ajouter_ligne(devis, "PEINT_FINITION", "surface", 5)
    ajouter_ligne(devis, LOT_AU_DETAIL, "surface", 5)
    assert devis.total_ht == round(sum(l.prix_ht for l in devis.lignes), 2)


# --- TVA --------------------------------------------------------------------

def test_la_ventilation_regroupe_les_montants_par_taux():
    """Un devis de rénovation mélange les taux : la ventilation est une mention
    obligatoire, pas un confort d'affichage."""
    devis = Devis()
    ajouter_ligne(devis, "PEINT_FINITION", "surface", 5)
    ajouter_ligne(devis, "PEINT_FINITION", "surface", 5, taux_tva="20")
    ventilation = devis.ventilation_tva
    assert set(ventilation) == {"10", "20"}
    for taux, montant in ventilation.items():
        base = sum(l.prix_ht for l in devis.lignes if l.taux_tva == taux)
        assert abs(montant - base * float(taux) / 100) < 0.01


def test_le_ttc_est_le_ht_augmente_de_la_tva_ventilee():
    devis = Devis()
    ajouter_ligne(devis, "PEINT_FINITION", "surface", 5)
    ajouter_ligne(devis, LOT_AU_DETAIL, "surface", 5)
    assert abs(devis.total_ttc - (devis.total_ht + devis.total_tva)) <= 0.01


def test_l_acompte_porte_sur_le_ttc():
    """30 % du HT au lieu du TTC sous-facturerait l'acompte de la TVA."""
    devis = Devis()
    ajouter_ligne(devis, "PEINT_FINITION", "surface", 5)
    assert devis.acompte_30_pct == round(devis.total_ttc * 0.30, 2)
    assert devis.acompte_30_pct > round(devis.total_ht * 0.30, 2)


# --- Consommables oubliés ---------------------------------------------------

def test_les_consommables_ajoutes_sont_traçables_comme_tels():
    """Leur origine distingue ce que l'artisan a dicté de ce que l'assistant a
    proposé — c'est ce qui rend une correction lisible en aval."""
    devis = Devis()
    items = ["bâche de protection", "ruban de masquage"]
    lignes = ajouter_consommables(devis, "PEINT_FINITION", items)
    assert [l.nom_lot for l in lignes] == items
    assert all(l.origine == "consommable" for l in lignes)
    assert all(l.prix_ht == PRIX_CONSOMMABLE_FORFAIT for l in lignes)


def test_les_consommables_d_un_lot_inconnu_sont_refuses():
    with pytest.raises(LotInconnu):
        ajouter_consommables(Devis(), "LOT_INEXISTANT", ["colle"])


def test_les_consommables_par_defaut_viennent_du_referentiel():
    lots = ["PEINT_PREP", LOT_AU_DETAIL, LOT_A_L_UNITE]
    assert consommables_par_defaut(lots) == {
        code: REFERENTIEL[code].consommables for code in lots}
    assert all(REFERENTIEL[code].consommables for code in lots), (
        "des lots sans consommable ne prouveraient rien")
