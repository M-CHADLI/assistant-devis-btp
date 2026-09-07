import pytest
from app.referentiel import (
    REFERENTIEL,
    MENTIONS,
    TAUX_TVA,
    DEFAULT_TAUX_TVA,
    lots_du_corps_metier,
)


def test_code_lot_correspond_a_cle():
    """Chaque Lot du référentiel a son code égal à la clé du dictionnaire."""
    for code, lot in REFERENTIEL.items():
        assert lot.code == code


def test_quatre_corps_metier_present():
    """Les corps de métier attendus sont bien présents dans le référentiel."""
    corps = {lot.corps_metier for lot in REFERENTIEL.values()}
    for attendu in ["peinture", "sols", "plomberie", "électricité"]:
        assert attendu in corps


def test_lots_du_corps_metier_tri_par_ordre():
    """lots_du_corps_metier('peinture') renvoie les lots triés par ordre croissant."""
    lots = lots_du_corps_metier("peinture")
    ordres = [lot.ordre for lot in lots]
    assert ordres == sorted(ordres)
    # Vérifier que tous les lots retournés ont le bon corps métier
    assert all(lot.corps_metier == "peinture" for lot in lots)


def test_lots_du_corps_metier_inconnu_vide():
    """Un corps de métier inconnu renvoie une liste vide."""
    assert lots_du_corps_metier("inconnu") == []


def test_mentions_lot_code_existe():
    """Tout lot_code référencé dans MENTIONS existe bien dans le référentiel."""
    for lot_code in MENTIONS.keys():
        assert lot_code in REFERENTIEL


def test_mentions_valeur_simple_ou_forte():
    """Les valeurs de MENTIONS sont uniquement 'simple' ou 'forte'."""
    assert set(MENTIONS.values()).issubset({"simple", "forte"})


def test_default_taux_tva_est_cle():
    """DEFAULT_TAUX_TVA doit être une clé de TAUX_TVA."""
    assert DEFAULT_TAUX_TVA in TAUX_TVA


def test_taux_chute_dans_intervalle():
    """Chaque taux de chute est compris entre 0.0 et 0.5 inclus."""
    for lot in REFERENTIEL.values():
        assert 0.0 <= lot.taux_chute <= 0.5
