"""Contrat de sortie de l'API (docs/STORIES.md US-22).

L'API est la frontière entre le front et le moteur, et l'artefact que le jury
peut lire sans exécuter le produit. Ces modèles la rendent contractuelle : ce
sont eux que FastAPI publie dans l'OpenAPI, et eux qui valident réellement les
réponses au moment de les sérialiser.

Un point mérite d'être signalé : **la ligne de devis a deux formes**, et non une
forme à champs optionnels. Avant la validation de structure (HITL-2, US-12),
aucune clé de prix n'existe — pas même à `null`. `LigneStructure` interdit donc
les clés de prix (`extra="forbid"`) : si un prix fuitait avant validation, la
réponse ne se sérialiserait pas. Le contrat garde l'invariant, pas seulement le
commentaire.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LigneStructure(BaseModel):
    """Ligne avant chiffrage : le métier, jamais l'argent."""
    model_config = ConfigDict(extra="forbid")

    lot_code: str
    designation: str
    quantite: float
    unite: str
    origine: str


class LigneChiffree(LigneStructure):
    """Ligne après HITL-2 : les prix viennent du catalogue, pas du modèle."""
    prix_unitaire_ht: float
    # La remise du catalogue, en pourcentage. Sans elle, le total d'une ligne
    # n'est pas recalculable par le lecteur du devis : il verrait 2 × 79,90 €
    # aboutir à 135,83 € sans explication (US-15, conformité du document).
    remise_pct: float = 0.0
    prix_ht: float
    taux_tva: float


class LigneEnAttente(BaseModel):
    """Quantité hors bornes, retenue tant que l'artisan n'a pas tranché (US-11)."""
    lot_code: str
    lot_nom: str
    dimension_type: str
    dimension_valeur: float
    borne_min: float
    borne_max: float


class CorrectionSortie(BaseModel):
    horodatage: str
    auteur: str
    description: str
    # D'où vient la correction — le triplet d'entraînement, lui, ne sort pas par
    # l'API : il ne quitte pas la machine (docs/STORIES.md US-25).
    origine: str = ""


class DevisSortie(BaseModel):
    pieces: list[str]
    lignes: list[LigneChiffree | LigneStructure]
    structure_validee: bool
    total_ht: float | None
    ventilation_tva: dict[str, float]
    total_tva: float | None
    total_ttc: float | None
    acompte_30_pct: float | None
    mentions: list[str]
    franchise_tva: bool
    mentions_manquantes: list[str]
    a_confirmer: list[LigneEnAttente]
    corrections: list[CorrectionSortie]


class ReponseDevis(BaseModel):
    projet_id: str
    devis: DevisSortie


class ReponseTour(ReponseDevis):
    """Un tour de dialogue rendu au navigateur."""
    intent: str
    messages: list[str]
    mentions: list[str]
    consommables_suggeres: dict[str, list[str]]
    # Messages de garde-fou (périmètre, injection) : listés à part pour que le
    # front les annonce en role="alert" sans reconnaître leur texte (US-20).
    cadrages: list[str]


class ReponseTourTranscrit(ReponseTour):
    texte_traite: str


class ReponseRelecture(BaseModel):
    """HITL-0 — la dictée remise en forme, à relire. Rien n'est déclenché."""
    projet_id: str
    brut: str
    propose: str
    alerte: str
    reformule: bool


class DecennaleSortie(BaseModel):
    assureur: str
    numero_contrat: str
    couverture_geographique: str
    valide_jusqu_au: str | None


class ProfilSortie(BaseModel):
    raison_sociale: str
    siret: str
    adresse: str
    rcs: str
    ape_naf: str
    tva_intracommunautaire: str
    regime_tva: str
    decennale: DecennaleSortie
    decennale_perimee: bool
    client_nom: str
    client_adresse_chantier: str
    delai_execution: str
    mentions_manquantes: list[str]


class MetriqueSortie(BaseModel):
    numero: int
    libelle: str
    seuil: float | None
    unite: str
    sens: str
    valeur: float | None
    statut: str
    commentaire: str


class MetriquesSortie(BaseModel):
    metriques: list[MetriqueSortie]
    volumes: dict[str, int]
    modeles_vus: list[str]
    depuis: str | None
    jusqu_a: str | None


class DetailBlocage(BaseModel):
    """Corps d'un 409 : ce qui bloque, et ce qu'il faut faire pour débloquer."""
    code: str = Field(description="structure_non_validee | mentions_incompletes")
    message: str
    manquantes: list[str]


class Erreur409(BaseModel):
    detail: DetailBlocage | str


class Erreur401(BaseModel):
    """Le message est le même pour toutes les causes de refus : ni « phrase
    incorrecte », ni « projet inconnu » (docs/STORIES.md US-23, OWASP A01)."""
    detail: str


class SessionOuverte(BaseModel):
    ouverte: bool
    duree_s: int


class Erreur404(BaseModel):
    detail: str
