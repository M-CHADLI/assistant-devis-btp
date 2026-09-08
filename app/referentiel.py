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

# Le texte qui accompagne chaque niveau. Il vit ici, et pas dans l'interface :
# le front recevait jusqu'ici des phrases dont il devait *deviner* la sévérité
# en cherchant un emoji dans la chaîne (US-18). La sévérité est une donnée, elle
# voyage comme telle ; le texte n'est plus qu'un libellé.
TEXTE_MENTION: dict[str, str] = {
    "forte": ("Ce point relève d'un domaine réglementé — je t'informe, mais "
              "fais valider par un professionnel avant travaux."),
    "simple": "Point de vigilance : à vérifier avant de te lancer.",
}


# --- Bornes de plausibilité (docs/DISPOSITIF_AGENT.md §3.2) ---
#
# Une dictée sur chantier produit des erreurs de saisie : « 220 m² » pour
# « 22 m² », un point décimal avalé, une unité confondue. Le modèle n'a aucun
# moyen de le savoir — le code, si. Ces bornes ne rejettent rien : elles
# déclenchent une demande de confirmation à l'artisan (US-11).
#
# Elles décrivent un logement résidentiel, cible du chantier pilote. Un
# artisan qui travaille sur un plateau de bureaux confirmera une fois.
BORNES_PAR_UNITE: dict[str, tuple[float, float]] = {
    "surface": (0.5, 400.0),   # m² — d'un WC à une grande maison
    "longueur": (0.5, 300.0),  # ml — plinthes, gaines, canalisations
    "unite": (1.0, 60.0),      # u  — points électriques, appareils sanitaires
}

# Bornes plus serrées là où l'unité générique est trop permissive.
BORNES_PAR_LOT: dict[str, tuple[float, float]] = {
    "ELEC_TABLEAU": (1.0, 3.0),      # un logement a un tableau, deux au plus
    "PLOMB_APPAREIL": (1.0, 20.0),   # appareils sanitaires
    "SOL_POSE_CARRELAGE": (0.5, 200.0),
}


def bornes(lot_code: str, type_dimension: str) -> tuple[float, float]:
    """Bornes applicables à une dimension, du plus spécifique au plus général."""
    if lot_code in BORNES_PAR_LOT:
        return BORNES_PAR_LOT[lot_code]
    return BORNES_PAR_UNITE.get(type_dimension, (0.0, float("inf")))


def est_plausible(lot_code: str, type_dimension: str, valeur: float) -> bool:
    mini, maxi = bornes(lot_code, type_dimension)
    return mini <= valeur <= maxi


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
