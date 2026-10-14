"""Schéma de sortie unique — docs/produit/CADRAGE_MODELE.md §6.

Un seul schéma partagé par les 6 capacités : le modèle signale sa tâche via
`intent`, le code route derrière. Aucun champ prix ni référence produit —
le modèle ne peut pas halluciner ce qu'il n'a pas la possibilité d'exprimer
(garde-fou structurel, docs/produit/DISPOSITIF_AGENT.md §3.2).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Intent = Literal["clarification", "lots", "quantitatif", "devis", "consommables", "reponse"]
Mention = Literal["simple", "forte"] | None


class Dimension(BaseModel):
    type: Literal["surface", "longueur", "unite"]
    valeur: float = Field(gt=0)


class LigneDevis(BaseModel):
    lot_code: str  # doit exister dans app.referentiel.REFERENTIEL — validé au routage
    dimension: Dimension
    commentaire: str | None = None


class PayloadDevis(BaseModel):
    pieces: list[str] = Field(default_factory=list)
    lignes: list[LigneDevis] = Field(default_factory=list)


class PayloadClarification(BaseModel):
    questions: list[str]


class PayloadConsommables(BaseModel):
    lot_code: str
    items: list[str]


class PayloadReponse(BaseModel):
    texte: str


class SortieModele(BaseModel):
    """L'enveloppe unique produite par le modèle à chaque tour."""
    intent: Intent
    payload: dict  # validé finement selon `intent` par app.pipeline
    mention: Mention = None
