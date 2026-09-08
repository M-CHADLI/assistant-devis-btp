"""Pré-remplissage des mentions légales à partir du SIRET (US-01).

Un devis BTP porte une dizaine de mentions d'identité obligatoires. Les faire
saisir à la main, c'est garantir des devis faux et un abandon à l'inscription.
L'annuaire des entreprises les restitue à partir du seul SIRET
(`docs/CADRAGE_MODELE.md` §6).

**Ce module n'est pas une brique d'IA et ne doit jamais être présenté comme
telle.** C'est un appel HTTP à un annuaire public, plus une validation de
somme de contrôle. Le modèle n'y touche pas.

Trois partis pris, qui sont les critères d'US-01 rendus exécutables :

- **La validation du SIRET est locale et précède tout appel réseau.** Un
  numéro mal formé n'a aucune raison de coûter un aller-retour, ni de faire
  fuiter un identifiant vers un tiers pour rien.
- **L'indisponibilité ne bloque jamais la création du compte.** Toute panne —
  clé absente, annuaire injoignable, SIRET inconnu — se résout en une bascule
  vers la saisie manuelle, avec son motif en clair. C'est pourquoi ce module
  ne lève pas d'exception réseau : il retourne un `Indisponible`.
- **La clé d'API ne sort jamais d'ici.** Elle est lue dans l'environnement,
  jamais écrite au dépôt, jamais renvoyée au navigateur, jamais journalisée,
  et jamais laissée dans le message d'une exception — l'URL qui la porte est
  construite et détruite dans la même fonction, et aucune erreur d'`urllib`
  n'est propagée telle quelle, précisément parce qu'elle citerait l'URL.

Réserve honnête sur la correspondance des champs : le nom des clés JSON
(`denomination`, `forme_juridique`, `numero_rcs`, `code_naf`, `siege`) est
repris de la documentation publiée de l'annuaire, **il n'a pas été vérifié
contre un appel réel** — aucune clé n'est configurée sur cette machine. Le
code en tire la conséquence : chaque champ absent devient une chaîne vide et
laisse la main à l'artisan, plutôt que de faire échouer la lecture.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

from app.observabilite import JOURNAL

POINT_ENTREE = "https://api.pappers.fr/v2/entreprise"
DELAI_SECONDES = 5.0
VARIABLE_CLE = "BTP_PAPPERS_CLE"

# SIRET de La Poste : historiquement exclu de la clé de Luhn, sa validité tient
# à ce que la somme de ses chiffres soit divisible par 5. Le cas est rare mais
# réel, et le traiter coûte trois lignes.
_PREFIXE_LA_POSTE = "356000000"


class SiretInvalide(ValueError):
    """Le numéro saisi ne peut pas être un SIRET.

    Le message énonce **la correction attendue**, pas seulement la faute :
    « il en manque trois » se corrige, « format invalide » ne se corrige pas
    (RGAA 11.10, WCAG 3.3.3).
    """


def normaliser_siret(brut: str) -> str:
    """Rend le SIRET en quatorze chiffres, ou dit ce qu'il faut corriger.

    Les espaces et points sont tolérés : c'est ainsi qu'un SIRET est imprimé
    sur un Kbis, et refuser la forme lue sur le papier serait refuser la
    saisie normale.
    """
    nettoye = "".join(c for c in (brut or "") if not c.isspace() and c != ".")
    if not nettoye:
        raise SiretInvalide(
            "Saisissez votre numéro SIRET : quatorze chiffres, "
            "tels qu'ils figurent sur votre Kbis.")
    if not nettoye.isdigit():
        indesirables = [f"« {c} »" for c in sorted({c for c in nettoye
                                                    if not c.isdigit()})]
        liste = (indesirables[0] if len(indesirables) == 1
                 else ", ".join(indesirables[:-1]) + " et " + indesirables[-1])
        raise SiretInvalide(
            f"Un SIRET ne contient que des chiffres — retirez {liste}.")
    if len(nettoye) == 9:
        # Cas le plus fréquent, et le seul qui se corrige sans le Kbis : le
        # SIREN identifie l'entreprise, le SIRET l'établissement.
        raise SiretInvalide(
            "Ces neuf chiffres sont votre SIREN. Ajoutez les cinq chiffres de "
            "l'établissement qui le suivent sur votre Kbis pour former le "
            "SIRET.")
    if len(nettoye) != 14:
        manque = 14 - len(nettoye)
        if manque > 0:
            raise SiretInvalide(
                f"Il manque {manque} chiffre{'s' if manque > 1 else ''} : un "
                f"SIRET en compte quatorze, vous en avez saisi {len(nettoye)}.")
        raise SiretInvalide(
            f"Il y a {-manque} chiffre{'s' if -manque > 1 else ''} de trop : un "
            f"SIRET en compte quatorze, vous en avez saisi {len(nettoye)}.")
    if not _cle_de_controle_juste(nettoye):
        raise SiretInvalide(
            "Ce numéro a bien quatorze chiffres, mais sa clé de contrôle ne "
            "tombe pas juste — un chiffre a dû être inversé. Recopiez-le "
            "depuis votre Kbis.")
    return nettoye


def _cle_de_controle_juste(siret: str) -> bool:
    if siret.startswith(_PREFIXE_LA_POSTE):
        return sum(int(c) for c in siret) % 5 == 0
    total = 0
    # Quatorze chiffres, longueur paire : les rangs pairs depuis la gauche sont
    # exactement les rangs pairs depuis la droite, ceux que Luhn double.
    for rang, chiffre in enumerate(int(c) for c in siret):
        if rang % 2 == 0:
            chiffre *= 2
            if chiffre > 9:
                chiffre -= 9
        total += chiffre
    return total % 10 == 0


@dataclass(frozen=True)
class IdentiteLegale:
    """Ce que l'annuaire sait, et que l'artisan n'aura pas à retaper.

    Aucun champ n'est obligatoire : un annuaire incomplet vaut mieux qu'une
    lecture qui échoue, et l'artisan complétera. Les champs vides sont
    exactement ceux que le formulaire laissera à sa charge.
    """
    siret: str
    raison_sociale: str = ""
    forme_juridique: str = ""
    rcs: str = ""
    ape_naf: str = ""
    adresse: str = ""
    tva_intracommunautaire: str = ""

    def champs(self) -> dict[str, str]:
        """Les valeurs sous les noms de champs du profil (`app/profil.py`)."""
        return {
            "raison_sociale": self.raison_sociale,
            "siret": self.siret,
            "adresse": self.adresse,
            "rcs": self.rcs,
            "ape_naf": self.ape_naf,
            "tva_intracommunautaire": self.tva_intracommunautaire,
        }


@dataclass(frozen=True)
class Indisponible:
    """L'annuaire n'a rien pu dire, et pourquoi — jamais une exception.

    `motif` est destiné au code et au journal ; `explication` est la phrase
    lue par l'artisan, et elle dit toujours ce qui se passe ensuite, parce que
    c'est la seule information qui lui serve.
    """
    motif: str
    explication: str

    champs: dict[str, str] = field(default_factory=dict)


_EXPLICATIONS = {
    "cle_absente":
        "Le pré-remplissage automatique n'est pas configuré sur cette "
        "installation. Saisissez vos informations légales à la main : "
        "elles ne vous seront demandées qu'une fois.",
    "injoignable":
        "L'annuaire des entreprises n'a pas répondu. Saisissez vos "
        "informations légales à la main, rien n'est perdu.",
    "inconnu":
        "Ce SIRET n'est pas connu de l'annuaire — il peut être trop récent. "
        "Saisissez vos informations légales à la main.",
    "quota":
        "Le quota d'interrogation de l'annuaire est épuisé. Saisissez vos "
        "informations légales à la main.",
    "illisible":
        "L'annuaire a répondu quelque chose d'inattendu. Saisissez vos "
        "informations légales à la main.",
}


def _indisponible(motif: str) -> Indisponible:
    return Indisponible(motif=motif, explication=_EXPLICATIONS[motif])


class _EchecAnnuaire(Exception):
    """Panne interne au transport, portant un motif et **jamais une URL**."""

    def __init__(self, motif: str) -> None:
        super().__init__(motif)
        self.motif = motif


def _transport_http(siret: str, cle: str) -> dict:
    """Le seul endroit où la clé et l'URL existent.

    Aucune exception d'`urllib` ne franchit cette fonction : leur texte cite
    l'URL appelée, donc la clé. Elles sont converties en motif.
    """
    url = f"{POINT_ENTREE}?" + urllib.parse.urlencode(
        {"api_token": cle, "siret": siret})
    try:
        with urllib.request.urlopen(url, timeout=DELAI_SECONDES) as reponse:
            return json.loads(reponse.read().decode("utf-8"))
    except urllib.error.HTTPError as erreur:
        if erreur.code == 404:
            raise _EchecAnnuaire("inconnu") from None
        if erreur.code in (401, 402, 403, 429):
            raise _EchecAnnuaire("quota") from None
        raise _EchecAnnuaire("injoignable") from None
    except json.JSONDecodeError:
        raise _EchecAnnuaire("illisible") from None
    except Exception:
        raise _EchecAnnuaire("injoignable") from None


def _texte(valeur: object) -> str:
    return valeur.strip() if isinstance(valeur, str) else ""


def _adresse_du_siege(brut: dict) -> str:
    """Recompose une adresse postale d'un bloc dont on ignore la forme exacte.

    Si l'annuaire fournit déjà une adresse d'un tenant, on la prend ; sinon on
    assemble ce qui est présent. Un bloc absent donne une chaîne vide, pas une
    adresse partielle qui aurait l'air complète.
    """
    siege = brut.get("siege")
    if not isinstance(siege, dict):
        return ""
    entiere = _texte(siege.get("adresse_complete"))
    if entiere:
        return entiere
    morceaux = [
        _texte(siege.get("adresse_ligne_1")),
        _texte(siege.get("adresse_ligne_2")),
        " ".join(m for m in (_texte(siege.get("code_postal")),
                             _texte(siege.get("ville"))) if m),
    ]
    return ", ".join(m for m in morceaux if m)


def lire_identite(brut: dict, siret: str) -> IdentiteLegale:
    """Traduit la réponse de l'annuaire en champs de profil."""
    return IdentiteLegale(
        siret=siret,
        raison_sociale=_texte(brut.get("denomination"))
        or _texte(brut.get("nom_entreprise")),
        forme_juridique=_texte(brut.get("forme_juridique")),
        rcs=_texte(brut.get("numero_rcs")),
        ape_naf=_texte(brut.get("code_naf")),
        adresse=_adresse_du_siege(brut),
        tva_intracommunautaire=_texte(
            brut.get("numero_tva_intracommunautaire")),
    )


def cle_configuree() -> bool:
    return bool((os.environ.get(VARIABLE_CLE) or "").strip())


def rechercher(
    siret: str,
    *,
    transport: Callable[[str, str], dict] | None = None,
    cle: str | None = None,
) -> IdentiteLegale | Indisponible:
    """Interroge l'annuaire pour un SIRET **déjà normalisé**.

    Ne lève jamais pour une cause réseau : le seul appelant est un formulaire
    d'inscription, et une inscription qui échoue parce qu'un tiers est en
    panne est une inscription perdue.

    `transport` est injectable pour que les tests décrivent la panne qu'ils
    veulent, sans réseau ni clé.
    """
    effective = cle if cle is not None else (os.environ.get(VARIABLE_CLE) or "")
    if transport is None and not effective.strip():
        JOURNAL.enregistrer("annuaire_interroge", siret=siret,
                            resultat="cle_absente")
        return _indisponible("cle_absente")

    appel = transport or _transport_http
    try:
        brut = appel(siret, effective)
    except _EchecAnnuaire as echec:
        JOURNAL.enregistrer("annuaire_interroge", siret=siret,
                            resultat=echec.motif)
        return _indisponible(echec.motif)
    except Exception:
        # Un transport de test qui casse ne doit pas non plus remonter : la
        # règle « l'inscription passe toujours » ne souffre pas d'exception.
        JOURNAL.enregistrer("annuaire_interroge", siret=siret,
                            resultat="injoignable")
        return _indisponible("injoignable")

    if not isinstance(brut, dict) or not brut:
        JOURNAL.enregistrer("annuaire_interroge", siret=siret,
                            resultat="illisible")
        return _indisponible("illisible")

    identite = lire_identite(brut, siret)
    JOURNAL.enregistrer("annuaire_interroge", siret=siret, resultat="trouve",
                        champs_remplis=sum(1 for v in identite.champs().values() if v))
    return identite
