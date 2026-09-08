"""Le catalogue vu par le moteur de devis — deux sources, une seule interface.

**Source `simule`** (par défaut) : la liste `CATALOGUE` ci-dessous. Contrainte
légale héritée de `docs/SOURCES_DONNEES.md` : on ne peut pas redistribuer un
vrai dump catalogue Leroy Merlin, mais la structure (référence, prix, promo,
unité de vente) est fidèle à ce qu'un vrai catalogue expose.

**Source `base`** : la base construite par la chaîne de données
(`docs/CHAINE_DONNEES.md`), lue par `app/catalogue_base.py`, atteinte par la
table de correspondance de `app/correspondance.py`.

Le choix est **explicite**, jamais implicite : `BTP_CATALOGUE_SOURCE=base`.
Brancher automatiquement la base « si elle est là » rendrait le prix d'un devis
dépendant de la présence d'un fichier reconstructible et non versionné — le
même chantier chiffrerait différemment sur deux machines, sans que rien ne le
dise. Un devis doit pouvoir s'expliquer ; d'où `Produit.origine`, qui voyage
avec le prix et dit d'où il vient.

Le défaut reste `simule` tant que les correspondances marquées
`ARBITRAGE_REQUIS` ne sont pas tranchées : voir `app/correspondance.py`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from app import catalogue_base
from app.correspondance import convient, famille_de, retenus_par


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
    #: D'où vient ce prix : `simule` (la liste ci-dessous) ou `base` (la chaîne
    #: de données). Porté par le produit et non déduit d'un réglage global,
    #: pour qu'une ligne de devis reste explicable une fois le réglage changé.
    origine: str = "simule"


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


def source() -> str:
    """La source de prix demandée : `simule` (défaut) ou `base`.

    Lue à l'appel et non à l'import : figée au chargement du module, elle ne
    serait plus modifiable, ni par un test ni par un déploiement.
    """
    return os.environ.get("BTP_CATALOGUE_SOURCE", "simule")


def _depuis_la_base(lot_code: str) -> Produit | None:
    """Le moins cher de la famille correspondante, ou `None`.

    `None` couvre tout ce qui empêche d'obtenir un prix **réel** : pas de
    correspondance établie pour ce lot, base absente (c'est un artefact
    reconstructible), ou famille vide. L'appelant retombe alors sur le
    catalogue simulé — jamais sur un prix approché.

    La connexion est ouverte et refermée à chaque appel. C'est délibéré :
    l'application sert ses requêtes dans un groupe de fils d'exécution, et une
    connexion SQLite partagée entre fils est une source de pannes rares, donc
    difficiles à reproduire. La base tient en 49 Ko et s'ouvre en lecture
    seule ; le coût est sans commune mesure avec le risque.
    """
    famille = famille_de(lot_code)
    if famille is None:
        return None
    try:
        cx = catalogue_base.ouvrir()
    except FileNotFoundError:
        return None
    retient = retenus_par(lot_code)
    try:
        if retient:
            # Le rayon est déjà trié du moins cher au plus cher : le premier
            # qui convient est le moins cher qui convient. Aucun ne convient
            # rend `None`, et le lot retombe sur le catalogue simulé — une
            # famille qui ne contient plus ce que le lot désigne doit se
            # signaler, pas se remplacer par son plus proche voisin.
            ligne = next(
                (l for l in catalogue_base.produits_de_famille(cx, famille)
                 if convient(l["libelle"], retient)), None)
        else:
            ligne = catalogue_base.moins_cher_de_famille(cx, famille)
    finally:
        cx.close()
    if ligne is None:
        return None
    return Produit(
        reference=ligne["reference"],
        designation=ligne["libelle"],
        categorie=lot_code,
        unite_vente=ligne["unite_vente"],
        prix_unitaire_ht=ligne["prix_ht"],
        promo_pct=ligne["taux_promo"],
        contenance=ligne["contenance"],
        origine="base",
    )


def resoudre_produit(lot_code: str) -> Produit | None:
    """Résolution catalogue déterministe. Le modèle ne voit jamais cette
    fonction — il ne connaît que des `lot_code`.

    Source `base` : le **moins cher** de la famille, prix remisé compris
    (`moins_cher_de_famille`). C'est une hypothèse de démonstration, pas une
    règle métier : un artisan choisit une gamme, une disponibilité, parfois un
    fournisseur imposé par le client. Elle a l'avantage d'être reproductible et
    d'être écrite ici plutôt que devinée.

    Source `simule` : le premier produit du lot. « Premier » n'a de sens que
    parce que la liste est courte et écrite à la main.
    """
    if source() == "base":
        produit = _depuis_la_base(lot_code)
        if produit is not None:
            return produit
        # Repli documenté : on préfère un prix simulé assumé à un prix réel
        # pris dans la mauvaise famille.
    produits = produits_du_lot(lot_code)
    return produits[0] if produits else None
