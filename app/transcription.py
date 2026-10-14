"""HITL-0 — relecture de la dictée avant tout traitement.

Frontière volontairement séparée de `app.llm` : la reformulation est faite par un
modèle **prompté**, jamais par le modèle fine-tuné du pipeline
(docs/produit/STORIES.md US-05, docs/produit/DISPOSITIF_AGENT.md §1.4). Ce module n'importe donc
rien de `app.llm` — c'est vérifiable, et un test le vérifie
(`tests/test_transcription.py`).

Le rôle du modèle ici est **cosmétique** : ponctuer, découper les phrases,
enlever les hésitations. Il ne doit ni résumer, ni compléter, ni surtout toucher
à un chiffre. Comme une consigne de prompt ne se fait pas respecter toute seule,
un contrôle déterministe compare les nombres et les unités avant/après : si le
modèle en a modifié un, sa proposition est **jetée** et le texte brut est rendu
tel quel, avec une alerte. La dictée « 22 m² » devenue « 2 m² » ne doit pas
seulement être visible : elle ne doit pas atteindre l'écran.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import requests

OLLAMA_URL = "http://localhost:11434/api/chat"

# Le modèle de relecture est prompté, pas fine-tuné, et le restera : quand le
# modèle fine-tuné arrivera, il remplacera MODEL_NAME dans app/llm.py, pas
# celui-ci.
MODELE_PROMPTE = "gpt-oss:20b"

SYSTEM_PROMPT_RELECTURE = """Tu remets en forme une dictée d'artisan sur un chantier.

Tu ponctues, tu mets les majuscules, tu enlèves les hésitations (« euh », « voilà »,
répétitions). C'est tout.

INTERDITS ABSOLUS :
- ne change aucun chiffre, aucune unité, aucune dimension ;
- n'ajoute aucune information qui n'est pas dite ;
- ne résume pas, ne raccourcis pas le propos ;
- ne réponds pas à l'artisan, ne commente pas.

Tu renvoies uniquement le texte remis en forme, sans guillemets ni préambule."""

# Un nombre, éventuellement décimal (virgule ou point), suivi ou non d'une unité
# collée (« 22m² », « 2,5m »). On compare des multiensembles : l'ordre peut
# changer si le modèle réordonne une phrase, pas les valeurs.
# Le « 2 » de « m2 » n'est pas un nombre : on écarte les chiffres collés à une
# lettre, sans quoi « 22 m² » reformulé en « 22 m2 » passerait pour une
# altération de chiffre.
_NOMBRE = re.compile(r"(?<![^\W\d_])\d+(?:[.,]\d+)?")
_UNITES = re.compile(r"\b(m²|m2|m³|m3|ml|m|cm|mm|km|kg|g|l|cl|%|€)\b", re.IGNORECASE)

ALERTE_CHIFFRES = (
    "La remise en forme automatique a modifié un chiffre ou une unité : elle a été "
    "écartée. Voici ta dictée telle quelle."
)


@dataclass
class Relecture:
    """Ce que l'artisan doit relire avant que quoi que ce soit ne démarre."""
    brut: str
    propose: str
    alerte: str = ""
    reformule: bool = True


def _normaliser_nombre(brut: str) -> str:
    """« 22,0 » et « 22 » sont le même nombre ; « 22 » et « 2 » ne le sont pas —
    d'où le retrait des zéros de fin *seulement* sur un décimal."""
    n = brut.replace(",", ".")
    return n.rstrip("0").rstrip(".") if "." in n else n


def _empreinte(texte: str) -> tuple[list[str], list[str]]:
    """Les nombres et les unités du texte, normalisés — la partie qu'un
    reformulateur n'a pas le droit de toucher."""
    nombres = sorted(_normaliser_nombre(n) for n in _NOMBRE.findall(texte))
    unites = sorted(u.lower().replace("²", "2").replace("³", "3")
                    for u in _UNITES.findall(texte))
    return nombres, unites


def chiffres_preserves(brut: str, propose: str) -> bool:
    return _empreinte(brut) == _empreinte(propose)


def _appeler_reformulateur(brut: str, timeout: int) -> str:
    resp = requests.post(
        OLLAMA_URL,
        json={"model": MODELE_PROMPTE, "stream": False,
              "messages": [{"role": "system", "content": SYSTEM_PROMPT_RELECTURE},
                           {"role": "user", "content": brut}],
              "options": {"temperature": 0.0}},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def relire(brut: str, timeout: int = 30) -> Relecture:
    """Prépare le texte à relire. Ne lève jamais : une panne de reformulation ne
    doit pas empêcher un artisan de dicter son chantier."""
    texte = (brut or "").strip()
    if not texte:
        return Relecture(brut="", propose="", reformule=False)

    try:
        propose = _appeler_reformulateur(texte, timeout)
    except (requests.RequestException, KeyError, ValueError):
        # Dégradé : on rend la dictée telle quelle, l'artisan la corrige à la main.
        return Relecture(brut=texte, propose=texte, reformule=False,
                         alerte="La remise en forme automatique est indisponible — "
                                "relis et corrige directement ta dictée.")

    if not propose:
        return Relecture(brut=texte, propose=texte, reformule=False)

    if not chiffres_preserves(texte, propose):
        return Relecture(brut=texte, propose=texte, reformule=False,
                         alerte=ALERTE_CHIFFRES)

    return Relecture(brut=texte, propose=propose)
