"""Catalogue produits simulé — structure réelle, valeurs simulées.

Contrainte légale héritée de docs/SOURCES_DONNEES.md : on ne peut pas
redistribuer un vrai dump catalogue Leroy Merlin, mais la structure (référence,
prix, promo, unité de vente) est fidèle à ce qu'un vrai catalogue expose.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Produit:
    reference: str
    designation: str
    categorie: str  # correspond à un Lot.code du référentiel
    unite_vente: str
    prix_unitaire_ht: float
    promo_pct: float = 0.0  # remise en cours, 0 si aucune
    # Quantité technique couverte par une unité de vente packagée (ex: 10 pour un
    # seau de 10L, 25 pour un rouleau de 25m²). None si l'unité de vente == unité
    # du lot (achat direct au m²/ml/u, pas de conditionnement à convertir).
    contenance: float | None = None


CATALOGUE: list[Produit] = [
    # Peinture — contenance en litres (cf. Lot.consommation_par_unite en L/m²)
    Produit("LM-PE-001", "Enduit de rebouchage 1kg", "PEINT_PREP", "u", 6.90),
    Produit("LM-PE-002", "Sous-couche universelle 10L", "PEINT_SOUS_COUCHE", "u", 34.90,
            promo_pct=0.10, contenance=10),
    Produit("LM-PE-003", "Peinture acrylique mate 10L", "PEINT_FINITION", "u", 79.90,
            promo_pct=0.15, contenance=10),

    # Sols
    Produit("LM-SO-001", "Ragréage autolissant 25kg", "SOL_PREP", "u", 24.90, contenance=25),
    Produit("LM-SO-002", "Film pare-vapeur 25m²", "SOL_SOUS_COUCHE", "u", 19.90, contenance=25),
    Produit("LM-SO-003", "Stratifié pose flottante", "SOL_POSE_STRATIFIE", "m²", 16.90, promo_pct=0.20),
    Produit("LM-SO-004", "Carrelage grès cérame 60x60", "SOL_POSE_CARRELAGE", "m²", 29.90),

    # Plomberie
    Produit("LM-PL-001", "Tube PER Ø16 barre 5m", "PLOMB_ALIM", "u", 12.90, contenance=5),
    Produit("LM-PL-002", "Tube PVC évacuation Ø100", "PLOMB_EVAC", "ml", 8.90),
    Produit("LM-PL-003", "Lavabo + robinetterie", "PLOMB_APPAREIL", "u", 189.00, promo_pct=0.10),

    # Électricité
    Produit("LM-EL-001", "Gaine ICTA Ø20 (25m)", "ELEC_GAINE", "u", 22.90, contenance=25),
    Produit("LM-EL-002", "Prise 2P+T avec plaque", "ELEC_PRISE", "u", 9.90),
    Produit("LM-EL-003", "Tableau électrique 3 rangées équipé", "ELEC_TABLEAU", "u", 249.00),
]

# Consommables (fonction « oublis », docs/CADRAGE_MODELE.md §4) — prix indicatif
# forfaitaire par occurrence, pas de conditionnement à calculer pour la démo.
PRIX_CONSOMMABLE_FORFAIT = 4.90


def produits_du_lot(lot_code: str) -> list[Produit]:
    return [p for p in CATALOGUE if p.categorie == lot_code]


def resoudre_produit(lot_code: str) -> Produit | None:
    """Résolution catalogue déterministe : le premier produit du lot (démo).

    En production : critères de gamme, disponibilité, préférence artisan.
    Le modèle ne voit jamais cette fonction — il ne connaît que des `lot_code`.
    """
    produits = produits_du_lot(lot_code)
    return produits[0] if produits else None
