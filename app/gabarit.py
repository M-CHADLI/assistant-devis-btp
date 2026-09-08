"""Gabarit de devis extrait d'un ancien document de l'artisan (US-03).

Un artisan n'envoie pas à son client un document qui ne ressemble pas aux
siens : l'adoption tient à ce détail. Déposer un ancien devis permet de
reprendre **l'ordre de ses blocs et ses intitulés d'usage**.

**Le document déposé ne passe jamais par le modèle.** L'OCR est une API
externe (`docs/CADRAGE_MODELE.md` §6) : `gpt-oss` est purement textuel, et
faire entrer un modèle vision dans le projet en ferait un second projet.
L'analyse du Markdown obtenu est ensuite du **Python déterministe** — même
frontière que partout ailleurs : le modèle décrit, le code décide.

Quatre partis pris, qui sont les critères d'US-03 rendus exécutables :

- **Rien du document déposé n'est conservé.** C'est la décision structurante
  de ce module. Un ancien devis porte le nom, l'adresse et les montants d'un
  *autre* client que celui du chantier en cours ; en retenir la moindre bribe
  ferait entrer une donnée personnelle d'un tiers dans le profil, sans base
  légale et sans que personne ne le sache. Le gabarit ne retient donc que
  **deux choses, toutes deux écrites ici** : quels blocs de `BLOCS` ont été
  reconnus, dans quel ordre, et lequel de **nos propres** synonymes chacun a
  rencontré. Aucune chaîne venue du fichier n'est stockée — c'est vérifiable
  mot à mot, et `tests/test_gabarit.py` le vérifie.
- **Un gabarit réordonne et renomme, il ne retire jamais.** Un bloc absent du
  document déposé reste émis à sa place par défaut. Laisser un gabarit
  supprimer un bloc reviendrait à laisser un ancien devis mal fichu retirer
  des mentions obligatoires du devis suivant, et produire un document
  inopposable sans que l'artisan le voie (`docs/STORIES.md` US-15).
- **Un échec d'OCR ne dégrade pas l'export.** Panne, illisibilité, clé
  absente, document qui n'est pas un devis : tous retombent sur le gabarit par
  défaut, en nommant le motif. Le module ne lève donc pas d'exception réseau,
  il retourne un `Indisponible`.
- **Le fichier sort de la machine, et cela se dit avant le dépôt.** C'est le
  seul endroit du produit où une donnée personnelle est transmise à un tiers.
  L'interface l'annonce avant que l'artisan choisisse son fichier, et
  `docs/RGPD.md` porte le traitement.

Réserve honnête sur la correspondance des champs : la ligne de requête
(`POST` sur le point d'entrée, jeton en en-tête `Authorization: Bearer`) est
reprise des exemples publiés, et la forme de la réponse (`pages[].markdown`,
`confidence_scores`) de la référence d'API publiée. **Ni l'une ni l'autre
n'ont été vérifiées contre un appel réel** — aucune clé n'est configurée sur
cette machine. Le code en tire la conséquence : tout champ absent ou
inattendu se résout en un motif et un repli, jamais en une exception.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

POINT_ENTREE = "https://api.mistral.ai/v1/ocr"
MODELE_OCR = "mistral-ocr-latest"
VARIABLE_CLE = "BTP_OCR_CLE"

# L'OCR d'un PDF de plusieurs pages est lent : un délai de cinq secondes comme
# celui de l'annuaire ferait échouer le cas nominal.
DELAI_SECONDES = 30.0

# Un devis d'artisan tient en une ou deux pages. Ce plafond n'est pas une
# limite technique de l'OCR (qui accepte bien davantage) mais une garde : il
# évite qu'un dépôt accidentel de plusieurs mégaoctets parte chez le tiers.
TAILLE_MAX_OCTETS = 8 * 1024 * 1024

# En deçà, l'OCR n'a rien lu d'exploitable : une photo floue rend quelques
# dizaines de caractères de bruit. Mieux vaut le dire que d'en tirer un
# gabarit dégradé.
LONGUEUR_MINIMALE = 200

# Score de confiance en deçà duquel on refuse de conclure. La référence d'API
# le documente par page ; les modèles anciens ne le renvoient pas du tout,
# auquel cas on s'en remet à la longueur du texte plutôt que d'inventer un
# score.
SEUIL_CONFIANCE = 0.65

# Types acceptés, reconnus au contenu et non à l'extension : un fichier
# renommé `.pdf` n'est pas un PDF, et c'est l'octet qui fait foi.
_SIGNATURES = (
    (b"%PDF-", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)


class DepotInvalide(ValueError):
    """Le fichier déposé ne peut pas être traité, et pourquoi.

    Comme pour le SIRET (US-01), le message énonce **la correction attendue**
    plutôt que la faute : « prenez la photo en JPEG ou en PNG » se corrige,
    « type de fichier non supporté » ne se corrige pas.
    """


@dataclass(frozen=True)
class Indisponible:
    """Aucun gabarit n'a pu être tiré du dépôt — jamais une exception.

    `motif` est destiné au code et au journal ; `explication` est la phrase
    lue par l'artisan, et elle dit toujours ce qui se passe ensuite.
    """
    motif: str
    explication: str


# Le vocabulaire du gabarit. Chaque bloc porte ses synonymes **connus, écrits
# ici** : le gabarit retient lequel a été reconnu, jamais le texte du
# document. C'est ce qui rend vérifiable la promesse « rien du fichier déposé
# n'est conservé » — tout ce qu'un gabarit contient se lit dans ce
# dictionnaire.
#
# L'ordre des clés est l'ordre par défaut : celui qu'`app/export.py` produit
# aujourd'hui, et celui sur lequel on retombe quand rien n'est reconnu.
BLOCS: dict[str, tuple[str, ...]] = {
    "identification": ("identification", "devis n°", "numéro de devis",
                       "référence", "objet"),
    "prestataire": ("prestataire", "entreprise", "émetteur", "l'entreprise",
                    "coordonnées de l'entreprise", "vos coordonnées"),
    "client": ("client et chantier", "client", "destinataire",
               "maître d'ouvrage", "coordonnées du client", "chantier"),
    "postes": ("détail des postes", "détail", "désignation", "prestations",
               "travaux", "postes", "descriptif"),
    "montants": ("montants", "totaux", "récapitulatif", "total", "montant"),
    "mentions": ("mentions particulières", "mentions", "conditions",
                 "conditions générales", "assurance", "garanties"),
    "accord": ("accord du client", "bon pour accord", "signature",
               "acceptation", "acceptation du devis"),
}

# Libellé par défaut de chaque bloc, celui de l'export actuel.
LIBELLES_PAR_DEFAUT: dict[str, str] = {
    "identification": "Identification",
    "prestataire": "Prestataire",
    "client": "Client et chantier",
    "postes": "Détail des postes",
    "montants": "Montants",
    "mentions": "Mentions particulières",
    "accord": "Accord du client",
}

# Sans ces deux-là, le document n'est pas un devis : il n'y a ni ce qui est
# facturé ni combien. Un courrier d'entreprise coche « prestataire » et
# « client » sans être pour autant un devis.
# Ces synonymes reconnaissent un bloc sans pouvoir en faire un titre : « devis
# n° » est un marqueur qui se lit dans la ligne, pas un intitulé de section.
# Les rencontrer identifie le bloc et laisse son libellé par défaut.
SYNONYMES_NON_TITRABLES = frozenset({
    "devis n°", "numéro de devis", "l'entreprise", "vos coordonnées",
})

BLOCS_DECISIFS = ("postes", "montants")
BLOCS_MINIMUM = 3


@dataclass(frozen=True)
class Gabarit:
    """Ordre des blocs et intitulés d'usage — et rien d'autre.

    `blocs` liste des clés de `BLOCS`, `intitules` associe à certaines d'entre
    elles un des synonymes de `BLOCS`. Les deux se lisent intégralement dans
    ce module : aucune valeur ne vient du fichier déposé.
    """
    blocs: tuple[str, ...] = ()
    intitules: dict[str, str] = field(default_factory=dict)

    @property
    def par_defaut(self) -> bool:
        return not self.blocs

    def ordre(self) -> tuple[str, ...]:
        """Tous les blocs, ceux du gabarit d'abord, les autres à leur place.

        Un gabarit réordonne et renomme ; il ne retire pas. Un bloc que
        l'ancien devis ne portait pas reste émis, sans quoi un document mal
        fichu ferait disparaître des mentions obligatoires du devis suivant.
        """
        reste = [c for c in BLOCS if c not in self.blocs]
        return tuple(self.blocs) + tuple(reste)

    def libelle(self, bloc: str) -> str:
        """Le titre à imprimer : celui de l'artisan s'il a été reconnu."""
        synonyme = self.intitules.get(bloc)
        if not synonyme or synonyme in SYNONYMES_NON_TITRABLES:
            return LIBELLES_PAR_DEFAUT[bloc]
        return synonyme[:1].upper() + synonyme[1:]

    def en_dict(self) -> dict:
        return {"blocs": list(self.blocs), "intitules": dict(self.intitules)}

    @classmethod
    def depuis_dict(cls, brut: dict | None) -> "Gabarit":
        """Relit un gabarit persisté en **revalidant** son vocabulaire.

        Un fichier de profil est éditable à la main et vit sur un montage
        synchronisé : relire sans filtrer laisserait entrer par le disque ce
        que la promesse interdit d'y mettre par le réseau.
        """
        if not isinstance(brut, dict):
            return cls()
        blocs = tuple(b for b in (brut.get("blocs") or []) if b in BLOCS)
        # Un intitulé sans son bloc est du poids mort : on ne garde que ceux
        # des blocs effectivement retenus, et seulement nos propres synonymes.
        intitules = {
            bloc: syn
            for bloc, syn in (brut.get("intitules") or {}).items()
            if bloc in blocs and syn in BLOCS.get(bloc, ())
        }
        return cls(blocs=blocs, intitules=intitules)


GABARIT_PAR_DEFAUT = Gabarit()


class PasUnDevis(ValueError):
    """Le document a été lu, mais ce n'est pas un devis.

    Porte les blocs reconnus, pour que le message dise ce qui a été cherché et
    non trouvé plutôt qu'un refus opaque.
    """

    def __init__(self, reconnus: tuple[str, ...]) -> None:
        self.reconnus = reconnus
        super().__init__("document sans structure de devis")

    @property
    def explication(self) -> str:
        attendus = "un détail des postes et des montants"
        if not self.reconnus:
            return (
                f"Ce document ne ressemble pas à un devis : on y cherchait "
                f"{attendus}, sans en trouver. Déposez un de vos anciens "
                f"devis, ou continuez avec la mise en page par défaut."
            )
        vus = ", ".join(LIBELLES_PAR_DEFAUT[b].lower() for b in self.reconnus)
        return (
            f"Ce document porte bien {vus}, mais on y cherchait aussi "
            f"{attendus} sans les trouver — ce n'est probablement pas un "
            f"devis. Déposez-en un, ou continuez avec la mise en page par "
            f"défaut."
        )


_EXPLICATIONS = {
    "cle_absente":
        "La lecture automatique de devis n'est pas configurée sur cette "
        "installation. Vos devis seront produits avec la mise en page par "
        "défaut, qui est complète et conforme.",
    "injoignable":
        "Le service de lecture n'a pas répondu. Vos devis restent produits "
        "avec la mise en page par défaut — vous pourrez réessayer plus tard.",
    "quota":
        "Le quota de lecture de documents est épuisé. Vos devis restent "
        "produits avec la mise en page par défaut.",
    "trop_gros":
        "Le service a refusé le fichier, trop volumineux pour lui. "
        "Réessayez avec un devis d'une ou deux pages.",
    "illisible":
        "La lecture n'a presque rien donné : la photo est probablement trop "
        "floue, trop sombre ou de travers. Reprenez-la à plat et en pleine "
        "lumière, ou continuez avec la mise en page par défaut, qui est "
        "complète et conforme.",
    "inattendu":
        "Le service de lecture a répondu quelque chose d'inattendu. Vos "
        "devis restent produits avec la mise en page par défaut.",
}


def _indisponible(motif: str) -> Indisponible:
    return Indisponible(motif=motif, explication=_EXPLICATIONS[motif])


class _EchecOcr(Exception):
    """Panne interne au transport, portant un motif et **jamais une URL**."""

    def __init__(self, motif: str) -> None:
        super().__init__(motif)
        self.motif = motif


def reconnaitre_type(octets: bytes) -> str:
    """Le type MIME lu dans les premiers octets, ou `DepotInvalide`.

    Reconnaître au contenu plutôt qu'à l'extension évite d'envoyer chez un
    tiers un fichier dont on ne sait rien parce qu'il s'appelait `.pdf`.
    """
    if not octets:
        raise DepotInvalide(
            "Le fichier déposé est vide. Vérifiez qu'il s'est bien enregistré, "
            "puis déposez-le à nouveau.")
    for signature, type_mime in _SIGNATURES:
        if octets.startswith(signature):
            return type_mime
    raise DepotInvalide(
        "Ce fichier n'est ni un PDF ni une photo. Déposez le PDF de votre "
        "devis, ou photographiez-le en JPEG ou en PNG.")


def valider_depot(octets: bytes) -> str:
    """Tout ce qui se vérifie **avant** de faire sortir le fichier.

    Même principe qu'US-01 : un dépôt qu'on sait refuser n'a aucune raison de
    coûter un aller-retour, ni de faire sortir de la machine un fichier qui
    sera rejeté de toute façon.
    """
    type_mime = reconnaitre_type(octets)
    if len(octets) > TAILLE_MAX_OCTETS:
        mega = TAILLE_MAX_OCTETS // (1024 * 1024)
        raise DepotInvalide(
            f"Ce fichier pèse {len(octets) / 1024 / 1024:.1f} Mo, au-delà des "
            f"{mega} Mo acceptés. Déposez le devis seul, sans les photos du "
            f"chantier, ou réduisez la qualité de l'image.")
    return type_mime


def _transport_http(octets: bytes, type_mime: str, cle: str) -> dict:
    """Le seul endroit où la clé et l'URL existent.

    Aucune exception d'`urllib` ne franchit cette fonction : leur texte cite
    l'URL et les en-têtes, donc la clé. Elles sont converties en motif.

    Le document part encodé dans le corps de la requête, jamais par une URL
    publique : le fichier vit sur un montage synchronisé, et l'exposer par un
    lien le rendrait lisible par qui l'aurait deviné.
    """
    donnees = base64.b64encode(octets).decode("ascii")
    champ = "image_url" if type_mime.startswith("image/") else "document_url"
    corps = json.dumps({
        "model": MODELE_OCR,
        "document": {
            "type": champ,
            champ: f"data:{type_mime};base64,{donnees}",
        },
        "confidence_scores_granularity": "page",
    }).encode("utf-8")
    requete = urllib.request.Request(
        POINT_ENTREE, data=corps, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {cle}"})
    try:
        with urllib.request.urlopen(requete, timeout=DELAI_SECONDES) as reponse:
            return json.loads(reponse.read().decode("utf-8"))
    except urllib.error.HTTPError as erreur:
        if erreur.code in (401, 402, 403, 429):
            raise _EchecOcr("quota") from None
        if erreur.code in (413, 422):
            raise _EchecOcr("trop_gros") from None
        raise _EchecOcr("injoignable") from None
    except json.JSONDecodeError:
        raise _EchecOcr("inattendu") from None
    except Exception:
        raise _EchecOcr("injoignable") from None


def lire_markdown(reponse: dict) -> tuple[str, float | None]:
    """Le texte des pages et le score de confiance, ou l'absence de score.

    Un score absent n'est **pas** un mauvais score : les modèles anciens n'en
    renvoient pas. On retourne `None`, et l'appelant s'en remet à la longueur
    du texte plutôt que de conclure d'un chiffre inventé.
    """
    pages = reponse.get("pages")
    if not isinstance(pages, list):
        raise _EchecOcr("inattendu")
    textes: list[str] = []
    scores: list[float] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        markdown = page.get("markdown")
        if isinstance(markdown, str):
            textes.append(markdown)
        confiance = page.get("confidence_scores")
        if isinstance(confiance, dict):
            valeur = confiance.get("average_page_confidence_score")
            if isinstance(valeur, (int, float)):
                scores.append(float(valeur))
    return "\n".join(textes), (min(scores) if scores else None)


def _titres(markdown: str) -> list[str]:
    """Les intitulés du document, dans l'ordre où ils se lisent.

    Un devis d'artisan n'est pas toujours structuré en titres Markdown : les
    blocs sont souvent des lignes en gras, ou en majuscules. On prend les
    trois formes, parce que ne prendre que `#` reviendrait à ne reconnaître
    que les devis déjà produits par un logiciel.
    """
    trouves: list[str] = []
    for ligne_brute in markdown.splitlines():
        ligne = ligne_brute.strip()
        if not ligne:
            continue
        if ligne.startswith("#"):
            trouves.append(ligne.lstrip("#").strip())
            continue
        sans_gras = ligne.strip("*_").strip()
        if ligne.startswith(("**", "__")) and sans_gras:
            trouves.append(sans_gras)
            continue
        lettres = [c for c in ligne if c.isalpha()]
        if lettres and len(ligne) <= 60 and all(c.isupper() for c in lettres):
            trouves.append(ligne)
    return trouves


def analyser(markdown: str) -> Gabarit:
    """Le gabarit tiré du texte — ordre des blocs et synonymes reconnus.

    Rien de ce que porte le résultat ne vient de `markdown` : la fonction ne
    fait qu'y **chercher** des chaînes de `BLOCS` et retenir lesquelles. Un
    intitulé du document qui contiendrait un nom de client ou un montant n'a
    donc aucun chemin vers le gabarit.

    Le synonyme le plus long l'emporte, sinon « détail des postes » serait
    reconnu comme « détail » et l'artisan verrait son intitulé raccourci.
    """
    ordre: list[str] = []
    intitules: dict[str, str] = {}
    for titre in _titres(markdown):
        minuscule = titre.casefold()
        candidats = [
            (bloc, syn)
            for bloc, synonymes in BLOCS.items()
            for syn in synonymes
            if syn in minuscule
        ]
        if not candidats:
            continue
        bloc, synonyme = max(candidats, key=lambda c: len(c[1]))
        if bloc in ordre:
            continue
        ordre.append(bloc)
        intitules[bloc] = synonyme
    return Gabarit(blocs=tuple(ordre), intitules=intitules)


def verifier_que_c_est_un_devis(gabarit: Gabarit) -> None:
    """Lève `PasUnDevis` si la structure ne peut pas être celle d'un devis."""
    reconnus = gabarit.blocs
    assez = len(reconnus) >= BLOCS_MINIMUM
    decisif = any(bloc in reconnus for bloc in BLOCS_DECISIFS)
    if not (assez and decisif):
        raise PasUnDevis(reconnus)


def cle_configuree() -> bool:
    return bool(os.environ.get(VARIABLE_CLE, "").strip())


def extraire(octets: bytes, *,
             transport: Callable[[bytes, str, str], dict] | None = None,
             cle: str | None = None) -> Gabarit | Indisponible:
    """Du fichier déposé au gabarit, ou au motif qui l'a empêché.

    Ne lève que `DepotInvalide` (le dépôt est refusé avant tout appel) et
    `PasUnDevis` (le document a été lu, il faut le dire à l'artisan). Toute
    autre panne devient un `Indisponible` : un service tiers en défaut ne doit
    pas empêcher de faire des devis.
    """
    type_mime = valider_depot(octets)
    cle = cle if cle is not None else os.environ.get(VARIABLE_CLE, "").strip()
    if not cle:
        return _indisponible("cle_absente")
    appel = transport or _transport_http
    try:
        reponse = appel(octets, type_mime, cle)
        markdown, confiance = lire_markdown(reponse)
    except _EchecOcr as echec:
        return _indisponible(echec.motif)
    except Exception:
        return _indisponible("injoignable")

    if len(markdown.strip()) < LONGUEUR_MINIMALE:
        return _indisponible("illisible")
    if confiance is not None and confiance < SEUIL_CONFIANCE:
        return _indisponible("illisible")

    gabarit = analyser(markdown)
    verifier_que_c_est_un_devis(gabarit)
    return gabarit


def vocabulaire() -> set[str]:
    """Tout ce qu'un gabarit peut contenir. Sert au test de la promesse."""
    mots = set(BLOCS)
    for synonymes in BLOCS.values():
        mots.update(synonymes)
    return mots
