"""US-23 — l'accès est authentifié, et aucun secret n'est dans le dépôt.

Un devis porte l'identité légale d'une entreprise et les coordonnées d'un client.
Le laisser derrière un simple cookie de projet, c'est laisser n'importe qui ouvrir
l'application et créer des devis au nom de l'artisan.

**Un seul compte.** Le produit s'adresse à un artisan, sur sa machine : il n'y a
pas d'annuaire d'utilisateurs à ce stade (US-01 reste à faire). L'authentification
porte donc sur une phrase de passe unique, pas sur un couple identifiant/mot de
passe — ce qui supprime au passage toute énumération de comptes.

**Aucun secret en dur, et pas de mode ouvert non plus.** La phrase de passe n'est
jamais stockée en clair : seule son empreinte scrypt vit dans l'environnement
(`BTP_MOT_DE_PASSE`). Si l'environnement n'en porte pas, le module **en tire une
au hasard au démarrage et l'affiche sur la console** : l'application reste
utilisable pour une démo, sans qu'aucun secret n'entre au dépôt et sans qu'un
« mode sans authentification » existe quelque part dans le code — le chemin
non authentifié n'existe pas, donc personne ne peut l'activer par erreur.

Mesures OWASP retenues, une par une (Top 10 2021) :

- **A01 Broken Access Control** — la vérification du jeton passe *avant* toute
  recherche de ressource : un appel sans jeton reçoit 401 sans jamais révéler
  qu'un projet existe. Un jeton n'ouvre que les projets de sa session.
- **A02 Cryptographic Failures** — phrase de passe dérivée par `scrypt`
  (n=2¹⁴, r=8, p=1, sel de 16 octets), jamais conservée en clair ; jeton signé en
  HMAC-SHA256 ; toutes les comparaisons de secrets en temps constant
  (`hmac.compare_digest`).
- **A05 Security Misconfiguration** — cookie `httponly`, `samesite=strict`, et
  `secure` dès que la requête est en HTTPS ; clé de signature tirée au hasard au
  démarrage si l'environnement n'en fournit pas, ce qui invalide les jetons au
  redémarrage plutôt que de réutiliser une clé par défaut.
- **A07 Identification and Authentication Failures** — durée de vie bornée à
  12 heures (une journée de chantier, pas davantage) inscrite *dans* le jeton
  signé, donc non prolongeable côté client ; tentatives limitées à 5 par fenêtre
  de 5 minutes et par adresse.
- **A09 Security Logging and Monitoring Failures** — chaque échec est journalisé
  dans `app.observabilite`, **sans jamais recopier la phrase essayée**.
- **CSRF** (hors Top 10 mais réel ici) — `samesite=strict` sur le cookie, et une
  API qui n'accepte que du JSON : un formulaire tiers ne peut pas la déclencher.

Ce que ce dispositif **ne fait pas**, dit franchement : pas de comptes multiples,
pas de rotation de clé, pas de révocation individuelle d'un jeton avant son
échéance. Un artisan, une machine, une journée.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from app.observabilite import JOURNAL

NOM_COOKIE = "btp_jeton"
DUREE_JETON_S = 12 * 3600  # une journée de chantier

# Limitation des tentatives : 5 essais par fenêtre glissante de 5 minutes.
MAX_TENTATIVES = 5
FENETRE_TENTATIVES_S = 300

# Paramètres scrypt — coût mémoire volontaire, c'est ce qui rend une attaque par
# dictionnaire coûteuse même avec du matériel dédié.
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P, _LONGUEUR = 2 ** 14, 8, 1, 32

MESSAGE_REFUS = "authentification requise"


class Refus(Exception):
    """Rejet d'accès. Le message est volontairement le même pour toutes les
    causes : ni « projet inconnu », ni « phrase incorrecte »."""


def _b64(brut: bytes) -> str:
    return base64.urlsafe_b64encode(brut).decode("ascii").rstrip("=")


def _debase64(texte: str) -> bytes:
    return base64.urlsafe_b64decode(texte + "=" * (-len(texte) % 4))


# --------------------------------------------------------------------------
# Phrase de passe
# --------------------------------------------------------------------------

def empreinte(phrase: str, sel: bytes | None = None) -> str:
    """« scrypt$sel$empreinte » — la phrase elle-même ne sort jamais d'ici."""
    sel = sel or secrets.token_bytes(16)
    brut = hashlib.scrypt(phrase.encode("utf-8"), salt=sel, n=_SCRYPT_N,
                          r=_SCRYPT_R, p=_SCRYPT_P, dklen=_LONGUEUR)
    return f"scrypt${_b64(sel)}${_b64(brut)}"


def phrase_correcte(phrase: str, empreinte_attendue: str) -> bool:
    """Comparaison en temps constant : la durée de la réponse ne dit rien du
    nombre de caractères devinés."""
    try:
        marqueur, sel_b64, attendu = empreinte_attendue.split("$")
    except (ValueError, AttributeError):
        return False
    if marqueur != "scrypt":
        return False
    try:
        calcule = hashlib.scrypt(phrase.encode("utf-8"), salt=_debase64(sel_b64),
                                 n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P,
                                 dklen=_LONGUEUR)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(_b64(calcule), attendu)


class Configuration:
    """L'état d'authentification du processus. Instancié une fois au démarrage.

    Ni la phrase ni la clé ne sont écrites sur disque : au redémarrage, une
    nouvelle phrase est tirée et les jetons émis avant deviennent invalides.
    C'est le comportement voulu — un secret qui survit sans qu'on l'ait choisi
    est un secret qu'on finit par oublier dans un dépôt."""

    def __init__(self, empreinte_phrase: str | None = None,
                 cle_signature: bytes | None = None) -> None:
        self.phrase_engendree: str | None = None
        empreinte_env = empreinte_phrase or os.environ.get("BTP_MOT_DE_PASSE", "")
        if not empreinte_env:
            self.phrase_engendree = _phrase_lisible()
            empreinte_env = empreinte(self.phrase_engendree)
        self.empreinte = empreinte_env
        cle_env = os.environ.get("BTP_CLE_SESSION", "")
        self.cle = cle_signature or (cle_env.encode("utf-8") if cle_env
                                     else secrets.token_bytes(32))
        self._tentatives: dict[str, list[float]] = {}

    # -- jetons ------------------------------------------------------------

    def emettre(self, maintenant: float | None = None) -> str:
        charge = {"sub": "artisan", "exp": int((maintenant or time.time()) + DUREE_JETON_S),
                  "jti": secrets.token_hex(8)}
        corps = _b64(json.dumps(charge, separators=(",", ":")).encode("utf-8"))
        signature = hmac.new(self.cle, corps.encode("ascii"), hashlib.sha256).digest()
        return f"{corps}.{_b64(signature)}"

    def verifier(self, jeton: str | None, maintenant: float | None = None) -> dict:
        """Rend la charge du jeton, ou lève `Refus`. Aucune information sur la
        cause : signature fausse et jeton périmé se ressemblent de l'extérieur."""
        if not jeton or "." not in jeton:
            raise Refus(MESSAGE_REFUS)
        corps, signature = jeton.rsplit(".", 1)
        attendue = hmac.new(self.cle, corps.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64(attendue), signature):
            raise Refus(MESSAGE_REFUS)
        try:
            charge = json.loads(_debase64(corps))
        except (ValueError, TypeError):
            raise Refus(MESSAGE_REFUS)
        # L'échéance est *dans* la partie signée : un client qui la retouche
        # casse la signature.
        if float(charge.get("exp", 0)) <= (maintenant or time.time()):
            raise Refus(MESSAGE_REFUS)
        return charge

    # -- limitation des tentatives ----------------------------------------

    def tentative_permise(self, origine: str, maintenant: float | None = None) -> bool:
        instant = maintenant or time.time()
        recentes = [t for t in self._tentatives.get(origine, [])
                    if instant - t < FENETRE_TENTATIVES_S]
        self._tentatives[origine] = recentes
        return len(recentes) < MAX_TENTATIVES

    def enregistrer_echec(self, origine: str, maintenant: float | None = None) -> None:
        self._tentatives.setdefault(origine, []).append(maintenant or time.time())
        # Jamais la phrase essayée : un journal n'est pas un coffre.
        JOURNAL.enregistrer("authentification_refusee", origine=origine)

    def oublier(self, origine: str) -> None:
        self._tentatives.pop(origine, None)


# Mots courants et sans ambiguïté à l'oral : la phrase se lit sur une console de
# chantier et se retape sans se tromper.
_MOTS = ("chantier", "platre", "niveau", "poutre", "carreau", "enduit", "rabot",
         "escabeau", "truelle", "mortier", "plinthe", "cheville", "lambris",
         "parquet", "cloison", "linteau", "ardoise", "gouttiere")


def _phrase_lisible() -> str:
    return "-".join(secrets.choice(_MOTS) for _ in range(4))
