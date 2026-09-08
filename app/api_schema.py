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


class MentionSortie(BaseModel):
    """Une mention réglementaire du tour : sa sévérité, puis son libellé.

    La sévérité est publiée comme donnée et non déduite du texte : le front la
    lit dans `niveau` au lieu de chercher un emoji dans la phrase, et un
    changement de formulation ne change plus la couleur d'un avertissement
    (docs/STORIES.md US-18).
    """
    niveau: str = Field(description="simple | forte")
    texte: str


class LigneEnAttente(BaseModel):
    """Ligne retenue tant que l'artisan n'a pas tranché (US-11, US-06)."""
    lot_code: str
    lot_nom: str
    dimension_type: str
    dimension_valeur: float
    borne_min: float
    borne_max: float
    motif: str = Field(default="hors_bornes",
                       description="hors_bornes | contradiction")
    # Renseigné pour une contradiction seulement : la valeur déjà au devis, que
    # l'artisan doit pouvoir comparer à celle qu'il vient de dicter.
    valeur_existante: float | None = None


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
    # Les niveaux (« simple », « forte ») accumulés sur le devis, pas des
    # phrases : le libellé est choisi à l'affichage.
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
    mentions: list[MentionSortie]
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
    origines: dict[str, str] = Field(
        default_factory=dict,
        description="artisan | annuaire, par champ légal (US-01)")


class RechercheSiretSortie(BaseModel):
    """Réponse au pré-remplissage par SIRET (US-01).

    `origine` vaut `annuaire` ou `saisie_manuelle` : il n'y a pas de troisième
    issue, et surtout pas d'échec — une indisponibilité de l'annuaire bascule
    en saisie manuelle, elle ne refuse jamais l'inscription.
    """
    origine: str = Field(description="annuaire | saisie_manuelle")
    motif: str | None = Field(
        default=None,
        description="cle_absente | injoignable | inconnu | quota | illisible")
    explication: str = Field(
        description="Phrase destinée à l'artisan : dit toujours la suite")
    champs: dict[str, str] = Field(
        default_factory=dict,
        description="Valeurs proposées, sous les noms de champs du profil")
    champs_conserves: list[str] = Field(
        default_factory=list,
        description="Champs non écrasés parce que l'artisan les a saisis")
    profil: ProfilSortie


class Erreur422Siret(BaseModel):
    """SIRET mal formé : refusé **avant tout appel réseau**.

    Le message énonce la correction attendue, pas seulement la faute, et
    `champ` permet au front de le rattacher au bon `aria-describedby`.
    """
    detail: str
    champ: str = "siret"


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


# --------------------------------------------------------------------------
# Jeu de données catalogue (docs/CHAINE_DONNEES.md)
# --------------------------------------------------------------------------

class SourceDonnees(BaseModel):
    """La provenance d'un lot de données, et sa licence.

    Elle voyage avec le jeu de données parce qu'un jeu republié sans licence
    n'est pas republiable : le destinataire ne sait pas ce qu'il a le droit
    d'en faire."""
    role: str = Field(description="fichier, api_rest ou scraping")
    nom: str
    licence: str
    lignes_brutes: int


class ProduitCatalogue(BaseModel):
    """Un produit vendable, enrichi de ce que les sources publiques donnent.

    Les deux champs de matière peuvent être `null` : la source ne couvre pas
    tout, et `qualite_correspondance` dit à quel point le rapprochement est
    solide. Un client de l'API qui les ignorerait prendrait un proxy pour une
    mesure — c'est précisément ce que la chaîne refuse de laisser faire."""
    reference: str
    libelle: str
    famille_code: str
    marque: str
    unite_vente: str
    contenance: float | None = None
    contenance_unite: str | None = None
    prix_ht: float
    taux_promo: float
    prix_remise_ht: float
    ean: str | None = None
    date_maj: str
    matiere: str
    qualite_correspondance: str = Field(description="exacte, proxy ou absente")
    facteur_kgco2e_par_kg: float | None = None
    masse_volumique_kg_m3: float | None = None


class FamilleSynthese(BaseModel):
    """Une famille et sa fourchette de prix, remise déduite."""
    code: str
    matiere: str
    qualite_correspondance: str
    nombre_de_produits: int
    prix_min: float | None = None
    prix_max: float | None = None
    prix_moyen: float | None = None


class FamilleIncomplete(BaseModel):
    """Un manque, exposé comme une donnée et non caché comme un défaut."""
    code: str
    matiere: str
    qualite_correspondance: str
    reserve: str | None = None
    facteur_manquant: bool
    densite_manquante: bool


class Erreur503(BaseModel):
    """La base du catalogue est un artefact reconstructible, donc absent d'un
    dépôt fraîchement cloné. Le message porte la commande qui la fabrique."""
    detail: str
