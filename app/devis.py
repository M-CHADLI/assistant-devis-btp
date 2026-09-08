"""Moteur de devis — 100 % déterministe (CLAUDE.md : « le modèle décrit, il ne
calcule jamais »). Consomme les lignes structurées produites par le modèle
(lot_code + dimension), résout le catalogue, calcule quantités et prix,
ventile la TVA. Aucune fonction ici n'est jamais appelée par le modèle.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.catalogue import Produit, resoudre_produit, PRIX_CONSOMMABLE_FORFAIT
from app.referentiel import REFERENTIEL, MENTIONS, TAUX_TVA, DEFAULT_TAUX_TVA


class LotInconnu(Exception):
    pass


@dataclass
class LigneChiffree:
    lot_code: str
    nom_lot: str
    produit: Produit | None
    quantite_achat: float
    prix_unitaire_ht: float
    prix_ht: float
    taux_tva: str
    origine: str = "modèle"  # "modèle" | "consommable" | "défaut"
    # HITL-2 (docs/STORIES.md US-12) : une ligne existe d'abord **sans prix**.
    # `quantite_technique` est ce que le métier sait dire (m², litres, ml) sans
    # ouvrir le catalogue ; `quantite_achat` et les prix n'apparaissent qu'au
    # chiffrage, après validation de la structure par l'artisan.
    quantite_technique: float = 0.0
    unite_technique: str = ""
    chiffree: bool = False
    # Dimension source (docs/DISPOSITIF_AGENT.md §2.3 — traçabilité) : permet de
    # détecter une reconfirmation orale identique et de l'ignorer (idempotence).
    dimension_type: str | None = None
    dimension_valeur: float | None = None


@dataclass
class Devis:
    lignes: list[LigneChiffree] = field(default_factory=list)
    mentions: set[str] = field(default_factory=set)

    @property
    def chiffre(self) -> bool:
        """Vrai quand toutes les lignes portent un prix. Un devis vide n'est pas
        « chiffré » : il n'y a rien à chiffrer."""
        return bool(self.lignes) and all(l.chiffree for l in self.lignes)

    @property
    def total_ht(self) -> float:
        return round(sum(l.prix_ht for l in self.lignes), 2)

    @property
    def ventilation_tva(self) -> dict[str, float]:
        """Montant de TVA dû, par taux — un devis réel mélange plusieurs taux."""
        par_taux: dict[str, float] = {}
        for l in self.lignes:
            montant_tva = l.prix_ht * (float(l.taux_tva) / 100)
            par_taux[l.taux_tva] = round(par_taux.get(l.taux_tva, 0.0) + montant_tva, 2)
        return par_taux

    @property
    def total_tva(self) -> float:
        return round(sum(self.ventilation_tva.values()), 2)

    @property
    def total_ttc(self) -> float:
        return round(self.total_ht + self.total_tva, 2)

    @property
    def acompte_30_pct(self) -> float:
        return round(self.total_ttc * 0.30, 2)


def _quantite_technique(lot_code: str, type_dimension: str, valeur: float) -> tuple[float, str]:
    """La quantité que le métier sait calculer **sans le catalogue** : rendement,
    taux de chute, unité du lot. Aucun produit n'est résolu ici — c'est ce qui
    permet de montrer une structure sans prix (docs/STORIES.md US-12)."""
    lot = REFERENTIEL.get(lot_code)
    if lot is None:
        raise LotInconnu(f"lot_code inconnu du référentiel : {lot_code!r}")

    taux_chute = lot.taux_chute if type_dimension in ("surface", "longueur") else 0.0
    valeur_avec_chute = valeur * (1 + taux_chute)
    return round(valeur_avec_chute * (lot.consommation_par_unite or 1.0), 2), lot.unite


def _conditionner(quantite_technique: float, produit: Produit) -> float:
    """Du besoin technique à la quantité vendue : contenance et conditionnement."""
    par_contenance = quantite_technique / (produit.contenance or 1.0)
    if produit.unite_vente in ("m²", "ml"):
        # Vente au détail : quantité fractionnelle acceptée.
        return round(par_contenance, 2)
    # Vente packagée ("u") : on arrondit au conditionnement supérieur.
    return math.ceil(par_contenance)


def chiffrer_ligne(ligne: LigneChiffree) -> LigneChiffree:
    """Accroche le volatil (catalogue, prix, promo) sur le stable (la structure).

    Idempotent : rechiffrer une ligne déjà chiffrée ne la change pas."""
    if ligne.chiffree:
        return ligne
    produit = resoudre_produit(ligne.lot_code)
    if produit is None:
        ligne.quantite_achat = ligne.quantite_technique
    else:
        ligne.quantite_achat = _conditionner(ligne.quantite_technique, produit)
    ligne.produit = produit
    ligne.prix_unitaire_ht = produit.prix_unitaire_ht if produit else 0.0
    promo = produit.promo_pct if produit else 0.0
    ligne.prix_ht = round(ligne.quantite_achat * ligne.prix_unitaire_ht * (1 - promo), 2)
    ligne.chiffree = True
    return ligne


def chiffrer(devis: Devis) -> Devis:
    """HITL-2 franchi : l'artisan a validé la structure, on peut chiffrer."""
    for ligne in devis.lignes:
        chiffrer_ligne(ligne)
    return devis


def ajouter_ligne(devis: Devis, lot_code: str, type_dimension: str, valeur: float,
                   taux_tva: str = DEFAULT_TAUX_TVA,
                   chiffrer_maintenant: bool = True) -> LigneChiffree:
    """Ajoute une ligne au devis.

    `chiffrer_maintenant=False` s'arrête à la structure : ni requête catalogue,
    ni prix. C'est le mode utilisé tant que l'artisan n'a pas validé la structure
    (HITL-2) — « on fait valider ce qui est stable avant d'y accrocher ce qui est
    volatil » (docs/DISPOSITIF_AGENT.md §1.4).
    """
    quantite_technique, unite = _quantite_technique(lot_code, type_dimension, valeur)
    lot = REFERENTIEL[lot_code]
    ligne = LigneChiffree(
        lot_code=lot_code, nom_lot=lot.nom, produit=None,
        quantite_achat=0.0, prix_unitaire_ht=0.0, prix_ht=0.0, taux_tva=taux_tva,
        quantite_technique=quantite_technique, unite_technique=unite,
        dimension_type=type_dimension, dimension_valeur=valeur,
    )
    if chiffrer_maintenant:
        chiffrer_ligne(ligne)
    devis.lignes.append(ligne)
    if lot_code in MENTIONS:
        devis.mentions.add(MENTIONS[lot_code])
    return ligne


def ajouter_consommables(devis: Devis, lot_code: str, items: list[str],
                          taux_tva: str = DEFAULT_TAUX_TVA,
                          chiffrer_maintenant: bool = True) -> list[LigneChiffree]:
    """Fonction « consommables oubliés » — prix forfaitaire par occurrence.

    Le forfait est un prix : il n'apparaît qu'après validation de la structure,
    comme les autres (US-12)."""
    if lot_code not in REFERENTIEL:
        raise LotInconnu(f"lot_code inconnu du référentiel : {lot_code!r}")
    ajoutees = []
    for item in items:
        ligne = LigneChiffree(
            lot_code=lot_code, nom_lot=item, produit=None,
            quantite_achat=1 if chiffrer_maintenant else 0.0,
            prix_unitaire_ht=PRIX_CONSOMMABLE_FORFAIT if chiffrer_maintenant else 0.0,
            prix_ht=PRIX_CONSOMMABLE_FORFAIT if chiffrer_maintenant else 0.0,
            taux_tva=taux_tva, origine="consommable",
            quantite_technique=1.0, unite_technique="u",
            chiffree=chiffrer_maintenant,
        )
        devis.lignes.append(ligne)
        ajoutees.append(ligne)
    return ajoutees


def consommables_par_defaut(lots_presents: list[str]) -> dict[str, list[str]]:
    """Ce que le référentiel sait déjà, pour rattraper les oublis (fonction « wow »)."""
    return {code: REFERENTIEL[code].consommables for code in lots_presents
            if code in REFERENTIEL and REFERENTIEL[code].consommables}
