"""Référentiel métier — 4 corps de métier pilotes (docs/CADRAGE_MODELE.md §4).

Valeurs comblées pour la démo, pas sourcées ligne à ligne (décision assumée du
pivot, §6). Chaque lot porte ses rendements, ses taux de chute et ses
consommables associés — c'est la matière que le LLM restitue, jamais qu'il calcule.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Lot:
    code: str
    nom: str
    corps_metier: str
    unite: str  # unité dans laquelle le modèle exprime la dimension (m², ml, u)
    consommation_par_unite: float | None = None  # quantité technique / unité de dimension (ex: 0.2 L de peinture par m²)
    taux_chute: float = 0.0  # fraction perdue à la pose (surface/longueur uniquement)
    consommables: list[str] = field(default_factory=list)
    ordre: int = 0  # ordre d'intervention dans le chantier


REFERENTIEL: dict[str, Lot] = {
    lot.code: lot
    for lot in [
        # --- Peinture ---
        Lot("PEINT_PREP", "Préparation des supports", "peinture", "m²",
            consommation_par_unite=0.2,  # 1kg d'enduit couvre ~5 m² de reprises ponctuelles
            consommables=["enduit de rebouchage", "bande à joint", "papier de verre"], ordre=1),
        Lot("PEINT_SOUS_COUCHE", "Sous-couche", "peinture", "m²", consommation_par_unite=0.1,
            taux_chute=0.05, consommables=["bâche de protection", "ruban de masquage"], ordre=2),
        Lot("PEINT_FINITION", "Peinture de finition (2 couches)", "peinture", "m²",
            consommation_par_unite=0.2, taux_chute=0.05,
            consommables=["bâche de protection", "ruban de masquage"], ordre=3),

        # --- Sols ---
        Lot("SOL_PREP", "Préparation du support (ragréage)", "sols", "m²",
            consommation_par_unite=1.5,
            consommables=["ragréage autolissant", "primaire d'accrochage"], ordre=1),
        Lot("SOL_SOUS_COUCHE", "Sous-couche isolante", "sols", "m²",
            consommables=["film pare-vapeur"], ordre=2),
        Lot("SOL_POSE_STRATIFIE", "Pose stratifié", "sols", "m²", taux_chute=0.08,
            consommables=["barres de seuil", "cales de dilatation", "plinthes"], ordre=3),
        Lot("SOL_POSE_CARRELAGE", "Pose carrelage", "sols", "m²", taux_chute=0.10,
            consommables=["colle carrelage", "croisillons", "joint de carrelage"], ordre=3),

        # --- Plomberie (mention forte possible) ---
        Lot("PLOMB_ALIM", "Alimentation eau (tube + raccords)", "plomberie", "ml", taux_chute=0.10,
            consommables=["raccords", "colliers de fixation", "joints"], ordre=1),
        Lot("PLOMB_EVAC", "Évacuation eaux usées", "plomberie", "ml", taux_chute=0.10,
            consommables=["coudes", "manchons", "colle PVC"], ordre=2),
        Lot("PLOMB_APPAREIL", "Pose appareil sanitaire", "plomberie", "u",
            consommables=["flexibles de raccordement", "joint silicone"], ordre=3),

        # --- Électricité (mention forte) ---
        Lot("ELEC_GAINE", "Gainage et câblage", "électricité", "ml", taux_chute=0.10,
            consommables=["gaine ICTA", "fil rigide", "boîtes de dérivation"], ordre=1),
        Lot("ELEC_PRISE", "Pose prise / interrupteur", "électricité", "u",
            consommables=["boîte d'encastrement", "vis", "dominos"], ordre=2),
        Lot("ELEC_TABLEAU", "Tableau électrique", "électricité", "u",
            consommables=["disjoncteurs", "peigne d'alimentation", "étiquettes"], ordre=3),
    ]
}


# Postes qui déclenchent une mention réglementaire (docs/DISPOSITIF_AGENT.md §3.3)
MENTIONS: dict[str, str] = {
    "ELEC_TABLEAU": "forte",
    "PLOMB_ALIM": "simple",
    "PLOMB_EVAC": "simple",
}


def lots_du_corps_metier(corps_metier: str) -> list[Lot]:
    return sorted(
        (l for l in REFERENTIEL.values() if l.corps_metier == corps_metier),
        key=lambda l: l.ordre,
    )


# --- TVA (docs/CADRAGE_MODELE.md §6 — contenu réglementaire) ---

TAUX_TVA = {
    "20": "Neuf, logement < 2 ans, agrandissement, gros équipements",
    "10": "Amélioration, entretien, aménagement — logement achevé > 2 ans",
    "5.5": "Rénovation énergétique et travaux induits — logement > 2 ans",
}

DEFAULT_TAUX_TVA = "10"  # hypothèse par défaut pour la démo : rénovation d'un logement existant
