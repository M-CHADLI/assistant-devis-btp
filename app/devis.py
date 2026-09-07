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
    # Dimension source (docs/DISPOSITIF_AGENT.md §2.3 — traçabilité) : permet de
    # détecter une reconfirmation orale identique et de l'ignorer (idempotence).
    dimension_type: str | None = None
    dimension_valeur: float | None = None


@dataclass
class Devis:
    lignes: list[LigneChiffree] = field(default_factory=list)
    mentions: set[str] = field(default_factory=set)

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


def _quantite_achat(lot_code: str, type_dimension: str, valeur: float) -> tuple[float, Produit | None]:
    lot = REFERENTIEL.get(lot_code)
    if lot is None:
        raise LotInconnu(f"lot_code inconnu du référentiel : {lot_code!r}")

    taux_chute = lot.taux_chute if type_dimension in ("surface", "longueur") else 0.0
    valeur_avec_chute = valeur * (1 + taux_chute)
    quantite_technique = valeur_avec_chute * (lot.consommation_par_unite or 1.0)

    produit = resoudre_produit(lot_code)
    if produit is None:
        return round(quantite_technique, 2), None

    contenance = produit.contenance or 1.0
    quantite_technique_par_contenance = quantite_technique / contenance

    if produit.unite_vente in ("m²", "ml"):
        # Vente au détail : quantité fractionnelle acceptée.
        return round(quantite_technique_par_contenance, 2), produit
    # Vente packagée ("u") : on arrondit au conditionnement supérieur.
    return math.ceil(quantite_technique_par_contenance), produit


def ajouter_ligne(devis: Devis, lot_code: str, type_dimension: str, valeur: float,
                   taux_tva: str = DEFAULT_TAUX_TVA) -> LigneChiffree:
    quantite, produit = _quantite_achat(lot_code, type_dimension, valeur)
    prix_unitaire = produit.prix_unitaire_ht if produit else 0.0
    promo = produit.promo_pct if produit else 0.0
    prix_ht = round(quantite * prix_unitaire * (1 - promo), 2)

    lot = REFERENTIEL[lot_code]
    ligne = LigneChiffree(
        lot_code=lot_code, nom_lot=lot.nom, produit=produit,
        quantite_achat=quantite, prix_unitaire_ht=prix_unitaire,
        prix_ht=prix_ht, taux_tva=taux_tva,
        dimension_type=type_dimension, dimension_valeur=valeur,
    )
    devis.lignes.append(ligne)
    if lot_code in MENTIONS:
        devis.mentions.add(MENTIONS[lot_code])
    return ligne


def ajouter_consommables(devis: Devis, lot_code: str, items: list[str],
                          taux_tva: str = DEFAULT_TAUX_TVA) -> list[LigneChiffree]:
    """Fonction « consommables oubliés » — prix forfaitaire par occurrence."""
    if lot_code not in REFERENTIEL:
        raise LotInconnu(f"lot_code inconnu du référentiel : {lot_code!r}")
    ajoutees = []
    for item in items:
        ligne = LigneChiffree(
            lot_code=lot_code, nom_lot=item, produit=None,
            quantite_achat=1, prix_unitaire_ht=PRIX_CONSOMMABLE_FORFAIT,
            prix_ht=PRIX_CONSOMMABLE_FORFAIT, taux_tva=taux_tva, origine="consommable",
        )
        devis.lignes.append(ligne)
        ajoutees.append(ligne)
    return ajoutees


def consommables_par_defaut(lots_presents: list[str]) -> dict[str, list[str]]:
    """Ce que le référentiel sait déjà, pour rattraper les oublis (fonction « wow »)."""
    return {code: REFERENTIEL[code].consommables for code in lots_presents
            if code in REFERENTIEL and REFERENTIEL[code].consommables}
