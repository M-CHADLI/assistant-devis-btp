"""Client du modèle — gpt-oss:20b brut, servi localement par Ollama.

C'est la baseline « brute, bien promptée » du protocole de preuve
(docs/CADRAGE_MODELE.md §7) : pas le modèle fine-tuné (chantier de plusieurs
mois, hors portée d'une démo), mais le même modèle de base, avec un prompt
sérieux qui décrit le schéma et donne des exemples — donc une comparaison
honnête reste possible plus tard.

Le modèle décrit, il ne calcule jamais (CLAUDE.md) : aucun outil de calcul ne
lui est exposé, il ne reçoit que du texte et rend du JSON.
"""
from __future__ import annotations

import json
import re

import requests

from app.referentiel import REFERENTIEL, MENTIONS

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "gpt-oss:20b"

LOTS_DISPONIBLES = "\n".join(
    f"- {code} ({lot.corps_metier}, unité {lot.unite}) : {lot.nom}"
    for code, lot in sorted(REFERENTIEL.items())
)

SYSTEM_PROMPT = f"""Tu es l'agent de préparation de chantier d'une application B2B pour prestataires BTP.
Un artisan décrit son chantier ; ton rôle est de le structurer, jamais de le chiffrer.

RÈGLE ABSOLUE : tu ne produis jamais de prix, jamais de référence produit. Le code
s'en charge après toi. Tu ne connais que des `lot_code` parmi cette liste fermée —
n'en invente aucun :
{LOTS_DISPONIBLES}

Domaines à mention réglementaire (tu dois répondre puis signaler, jamais refuser) :
{', '.join(MENTIONS.keys())} → mention "forte" ou "simple" selon le cas.

Tu réponds TOUJOURS avec un unique objet JSON, rien d'autre avant ni après, de la forme :
{{"intent": "clarification|lots|quantitatif|devis|consommables|reponse", "payload": {{...}}, "mention": null|"simple"|"forte"}}

Formes de payload attendues selon l'intent :
- "clarification" : {{"questions": ["..."]}}  — si des informations manquent pour chiffrer
- "devis" : {{"pieces": ["salon"], "lignes": [{{"lot_code": "PEINT_FINITION", "dimension": {{"type": "surface", "valeur": 22.0}}, "commentaire": "..."}}]}}
- "quantitatif" : même forme que "devis" — quand tu ne fais que préciser des quantités
  déjà discutées, sans redécouper le chantier
- "consommables" : {{"lot_code": "SOL_POSE_STRATIFIE", "items": ["barres de seuil", "cales de dilatation"]}}
- "reponse" : {{"texte": "..."}}  — pour une question directe hors devis

Exemple : l'artisan dit "je refais le salon, 22 m² au sol, murs à repeindre" →
tu réponds avec intent "devis", des lignes pour la préparation des supports,
la sous-couche et la finition peinture, plus le sol si mentionné, chacune avec
sa dimension réelle (surface en m²). N'ajoute jamais de champ prix ou référence.
"""


class SortieModeleInvalide(Exception):
    """Le modèle a répondu, mais sa sortie n'est pas un JSON exploitable."""


class ModeleInjoignable(Exception):
    """Ollama n'a pas répondu du tout — panne, timeout, service arrêté.

    Distinct de SortieModeleInvalide : une reprise n'a aucune chance d'aboutir,
    l'appelant doit escalader tout de suite (docs/DISPOSITIF_AGENT.md §1.3).
    """


def _extraire_json(texte: str) -> dict:
    """Le modèle brut ajoute parfois du texte autour du JSON — on l'isole."""
    match = re.search(r"\{.*\}", texte, re.DOTALL)
    if not match:
        raise SortieModeleInvalide(f"aucun JSON trouvé dans la sortie : {texte[:200]!r}")
    return json.loads(match.group(0))


def appeler_modele(historique: list[dict], nouveau_message: str, timeout: int = 60) -> dict:
    """Un tour de pipeline : historique + message → JSON `{intent, payload, mention}`.

    **Un seul appel modèle, sans reprise interne.** La reprise appartient au
    pipeline, qui est le seul à voir l'ensemble des motifs d'échec (JSON illisible
    *et* schéma non conforme) et le seul à pouvoir borner le nombre total d'appels
    (docs/DISPOSITIF_AGENT.md §1.3, objectif de latence §4.3 : p95 < 30 s).
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *historique,
                {"role": "user", "content": nouveau_message}]

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "messages": messages, "stream": False,
                  "options": {"temperature": 0.2}},
            timeout=timeout,
        )
        resp.raise_for_status()
        contenu = resp.json()["message"]["content"]
    except requests.RequestException as exc:
        raise ModeleInjoignable(f"Ollama injoignable sur {OLLAMA_URL} : {exc}") from exc
    except (KeyError, ValueError) as exc:
        raise ModeleInjoignable(f"réponse Ollama inattendue : {exc}") from exc

    try:
        return _extraire_json(contenu)
    except (SortieModeleInvalide, json.JSONDecodeError) as exc:
        raise SortieModeleInvalide(f"sortie non exploitable : {exc}") from exc
