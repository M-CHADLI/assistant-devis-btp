"""Profil de l'artisan et identité du client — les données légales du devis.

Un devis BTP non conforme est inopposable : ce n'est pas un devis. Les mentions
qui font sa validité ne peuvent **ni être devinées, ni être produites par le
modèle** (docs/produit/CADRAGE_MODELE.md §6). Elles sont déclarées une fois au profil,
et le code les reporte sur chaque document.

Le régime de TVA n'est pas une variante d'affichage. En franchise en base
(article 293 B du CGI), le devis ne porte **aucune** ligne de TVA et affiche la
mention légale correspondante : un devis d'auto-entrepreneur qui affiche une TVA
est un devis faux (docs/produit/STORIES.md, US-02).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import StrEnum

from app.gabarit import Gabarit

MENTION_293B = "TVA non applicable, art. 293 B du CGI"


class RegimeTVA(StrEnum):
    REEL = "reel"
    FRANCHISE_293B = "franchise_293b"


@dataclass
class Decennale:
    """Assurance décennale — obligatoire pour tout travaux de construction."""
    assureur: str = ""
    numero_contrat: str = ""
    couverture_geographique: str = ""
    valide_jusqu_au: dt.date | None = None

    def perimee(self, a_la_date: dt.date | None = None) -> bool:
        """Vraie si l'attestation est expirée à la date donnée.

        Une échéance inconnue n'est **pas** traitée comme périmée : c'est un
        champ manquant, signalé comme tel, pas une expiration inventée.
        """
        if self.valide_jusqu_au is None:
            return False
        return self.valide_jusqu_au < (a_la_date or dt.date.today())


# Les champs légaux susceptibles d'être pré-remplis par l'annuaire (US-01).
# Le régime de TVA et la décennale n'en font pas partie : aucun annuaire ne les
# connaît, ils restent déclaratifs (US-02).
CHAMPS_PREREMPLISSABLES = (
    "raison_sociale", "siret", "adresse", "rcs", "ape_naf",
    "tva_intracommunautaire",
)

ORIGINE_ARTISAN = "artisan"
ORIGINE_ANNUAIRE = "annuaire"


@dataclass
class ProfilArtisan:
    raison_sociale: str = ""
    siret: str = ""
    adresse: str = ""
    rcs: str = ""
    ape_naf: str = ""
    tva_intracommunautaire: str = ""
    regime_tva: RegimeTVA = RegimeTVA.REEL
    decennale: Decennale = field(default_factory=Decennale)

    # Origine de chaque champ légal (`docs/produit/DISPOSITIF_AGENT.md` §2.3). Absent
    # du dictionnaire vaut `artisan` : par défaut, ce qui est dans le profil y
    # a été mis à la main, et c'est la lecture la plus prudente — elle protège
    # la saisie plutôt que le pré-remplissage.
    origines: dict[str, str] = field(default_factory=dict)

    # Mise en page reprise d'un ancien devis de l'artisan (US-03). Vide vaut
    # « mise en page par défaut » : c'est une mémoire utilisateur révocable
    # (`docs/produit/DISPOSITIF_AGENT.md` §2.2), et la révoquer se fait en la vidant.
    gabarit: Gabarit = field(default_factory=Gabarit)

    @property
    def en_franchise(self) -> bool:
        return self.regime_tva is RegimeTVA.FRANCHISE_293B

    def origine_de(self, champ: str) -> str:
        return self.origines.get(champ, ORIGINE_ARTISAN)

    def fait_autorite(self, champ: str) -> bool:
        """Vrai si l'artisan a posé cette valeur — donc si nul ne l'écrase.

        Un champ vide ne fait jamais autorité : ne rien avoir saisi n'est pas
        une décision, et refuser de le remplir pour cette raison reviendrait à
        faire retaper à l'artisan ce qu'on sait déjà.
        """
        return (bool(getattr(self, champ, "").strip())
                and self.origine_de(champ) == ORIGINE_ARTISAN)


@dataclass
class Client:
    """Le client final n'est pas utilisateur du produit (CLAUDE.md).

    Il n'a ni compte ni écran ; seules ses coordonnées sont saisies, parce que
    les mentions obligatoires BTP les exigent.
    """
    nom: str = ""
    adresse_chantier: str = ""


# Libellés lisibles par l'artisan, pas noms de champs : ce sont eux qui
# remontent à l'interface quand l'export est refusé.
_LIBELLES_ARTISAN = {
    "raison_sociale": "la raison sociale de votre entreprise",
    "siret": "votre numéro SIRET",
    "adresse": "l'adresse de votre entreprise",
    "rcs": "votre numéro RCS",
    "ape_naf": "votre code APE/NAF",
    "tva_intracommunautaire": "votre numéro de TVA intracommunautaire",
}
_LIBELLES_DECENNALE = {
    "assureur": "l'assureur de votre décennale",
    "numero_contrat": "le numéro de contrat de votre décennale",
    "couverture_geographique": "la couverture géographique de votre décennale",
}
_LIBELLES_CLIENT = {
    "nom": "le nom du client",
    "adresse_chantier": "l'adresse du chantier",
}


def champs_manquants(profil: ProfilArtisan, client: Client,
                     delai_execution: str = "") -> list[str]:
    """Les mentions légales absentes, en clair.

    Sert le cas dégradé d'US-15 : **une donnée légale manquante bloque
    l'export** plutôt que de produire un document non conforme. Retourner une
    liste vide vaut autorisation d'exporter.

    Le numéro de TVA intracommunautaire n'est exigé qu'en régime réel : un
    artisan en franchise n'en a pas nécessairement, et l'exiger de lui
    bloquerait un export pourtant conforme.
    """
    manquants: list[str] = []

    for champ, libelle in _LIBELLES_ARTISAN.items():
        if champ == "tva_intracommunautaire" and profil.en_franchise:
            continue
        if not getattr(profil, champ).strip():
            manquants.append(libelle)

    for champ, libelle in _LIBELLES_DECENNALE.items():
        if not getattr(profil.decennale, champ).strip():
            manquants.append(libelle)

    for champ, libelle in _LIBELLES_CLIENT.items():
        if not getattr(client, champ).strip():
            manquants.append(libelle)

    if not delai_execution.strip():
        manquants.append("le délai d'exécution des travaux")

    return manquants
