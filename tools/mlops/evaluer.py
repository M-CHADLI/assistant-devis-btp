"""Étape « validation » : mesurer le modèle sur le jeu d'essai, jamais vu.

Trois métriques seulement, celles que ce jeu permet de mesurer honnêtement
(numérotation de `DISPOSITIF_AGENT.md` §4.3, seuils lus dans
`app.observabilite.SEUILS` — jamais recopiés ici) :

- **nº 1, taux de JSON valide** — la mesure directe de l'apport du fine-tuning ;
- **nº 5, justesse de la mention** — comparaison à la mention attendue ;
- **nº 7, prix ou référence inventés** — seuil zéro, non négociable : le modèle
  décrit, il ne chiffre pas.

Les métriques 2, 3, 4 et 6 demandent une annotation ligne à ligne du jeu
d'essai qui n'existe pas encore. Elles sont **déclarées non mesurées** plutôt
qu'approchées : un chiffre flatteur vaut moins qu'un blanc assumé.

Le rapport est écrit dans `mlops/evaluations/`, horodaté, avec le nom du modèle
interrogé : une mesure sans son modèle ne se compare à rien.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path

from app import llm
from app.observabilite import SEUILS

DOSSIER = Path("mlops/evaluations")

# Un prix ou une référence produit dans la sortie du modèle : la frontière que
# le projet ne franchit pas. On cherche large — mieux vaut un faux positif à
# examiner qu'un prix inventé qui passe.
MOTIFS_INTERDITS = (
    re.compile(r"\d+[.,]\d{2}\s*(?:€|eur\b|euros\b)", re.I),
    re.compile(r"\b(?:prix|tarif|montant)\s*:\s*\d", re.I),
    re.compile(r"\bréf(?:érence)?\s*:?\s*[A-Z0-9]{4,}\b"),
)

# Deux seuils seulement font échouer la validation : le taux de JSON valide,
# métrique nº 1 du projet, et les prix inventés, dont le seuil est zéro et
# « non négociable » (`docs/CADRAGE_MODELE.md`). Les autres sont des
# indicateurs : un modèle qui rate la justesse de mention reste utilisable, un
# modèle qui invente des prix ne l'est pas. Cette liste vit ici, et non dans
# `app.observabilite`, parce qu'elle qualifie la **validation d'un modèle
# candidat**, pas la surveillance en exploitation.
SEUILS_BLOQUANTS = frozenset({1, 7})


def contient_prix_ou_reference(sortie: dict) -> bool:
    texte = json.dumps(sortie, ensure_ascii=False)
    return any(motif.search(texte) for motif in MOTIFS_INTERDITS)


def evaluer(exemples: list[dict], appel=llm.appeler_modele) -> dict:
    """Interroge le modèle une fois par exemple et compte, sans rien corriger."""
    valides = comparables = mentions_justes = inventions = 0
    latences: list[float] = []
    echecs: list[dict] = []

    for exemple in exemples:
        debut = time.monotonic()
        try:
            sortie = appel([], exemple["user"])
        except llm.SortieModeleInvalide as erreur:
            echecs.append({"id": exemple["id"], "motif": "JSON invalide",
                           "detail": str(erreur)[:200]})
            latences.append(time.monotonic() - debut)
            continue
        except llm.ModeleInjoignable as erreur:
            raise SystemExit(f"Modèle injoignable : {erreur}") from erreur
        latences.append(time.monotonic() - debut)

        valides += 1
        attendue = exemple["final"].get("mention")
        if "mention" in exemple["final"]:
            comparables += 1
            mentions_justes += 1 if sortie.get("mention") == attendue else 0
        inventions += 1 if contient_prix_ou_reference(sortie) else 0

    total = len(exemples)
    latences.sort()
    return {
        "horodatage": datetime.now(UTC).isoformat(timespec="seconds"),
        "modele": llm.MODEL_NAME,
        "exemples": total,
        "metriques": {
            1: round(100 * valides / total, 1) if total else None,
            5: round(100 * mentions_justes / comparables, 1) if comparables else None,
            7: inventions,
            8: round(latences[int(0.95 * (len(latences) - 1))], 2) if latences else None,
        },
        "non_mesurees": [2, 3, 4, 6],
        "echecs": echecs[:20],
    }


def verdict(rapport: dict) -> tuple[bool, list[str]]:
    """Confronte les mesures aux seuils. Seuls les seuils bloquants font échouer."""
    manquements = []
    tenu = True
    for seuil in SEUILS:
        valeur = rapport["metriques"].get(seuil.numero)
        if valeur is None:
            continue
        depasse = valeur < seuil.seuil if seuil.sens == "min" else valeur > seuil.seuil
        if depasse:
            manquements.append(
                f"nº {seuil.numero} {seuil.libelle} : {valeur} {seuil.unite} "
                f"pour un seuil {seuil.sens} de {seuil.seuil}"
                + (" (bloquant)" if seuil.numero in SEUILS_BLOQUANTS else ""))
            tenu = tenu and seuil.numero not in SEUILS_BLOQUANTS
    return tenu, manquements


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument("--essai", type=Path, default=Path("dataset/essai.jsonl"))
    analyseur.add_argument("--dossier", type=Path, default=DOSSIER)
    arguments = analyseur.parse_args(argv)

    if not arguments.essai.exists():
        print(f"{arguments.essai} absent : aucune mesure possible.")
        return 3

    exemples = [json.loads(l) for l in
                arguments.essai.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not exemples:
        print(f"{arguments.essai} vide : aucune mesure possible.")
        return 3

    rapport = evaluer(exemples)
    tenu, manquements = verdict(rapport)
    rapport["seuils_tenus"] = tenu
    rapport["manquements"] = manquements

    arguments.dossier.mkdir(parents=True, exist_ok=True)
    destination = arguments.dossier / f"{rapport['horodatage'].replace(':', '')}.json"
    destination.write_text(json.dumps(rapport, ensure_ascii=False, indent=2),
                           encoding="utf-8")

    print(f"{rapport['exemples']} exemples · modèle {rapport['modele']}")
    for numero, valeur in rapport["metriques"].items():
        print(f"  métrique nº {numero} : {valeur}")
    print(f"  non mesurées : {rapport['non_mesurees']}")
    for manquement in manquements:
        print(f"  MANQUEMENT {manquement}")
    print(f"Rapport écrit dans {destination}")
    return 0 if tenu else 1


if __name__ == "__main__":
    raise SystemExit(main())
