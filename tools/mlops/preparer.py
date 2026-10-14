"""Étape « préparation » : du dataset validé au format attendu par Unsloth.

La conversion est volontairement bête — elle ne corrige rien, ne complète rien,
ne réordonne rien. Toute transformation intelligente à cet endroit serait une
transformation que le dataset validé ne porte pas, donc une divergence entre ce
qui a été relu à la main et ce qui entre dans l'entraînement.

Le raisonnement va dans un message `analysis` distinct de la réponse finale :
c'est ce qui permet à gpt-oss de conserver sa capacité de raisonnement au lieu
d'apprendre à recracher du JSON sans réfléchir.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.llm import SYSTEM_PROMPT

DESTINATION = Path("mlops/artefacts/entrainement.chat.jsonl")


def convertir(exemple: dict) -> dict:
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": exemple["user"]}]
    if exemple.get("reasoning"):
        messages.append({"role": "assistant", "channel": "analysis",
                         "content": exemple["reasoning"]})
    messages.append({"role": "assistant", "channel": "final",
                     "content": json.dumps(exemple["final"], ensure_ascii=False)})
    return {"id": exemple["id"], "capacite": exemple["capacite"], "messages": messages}


def preparer(source: Path, destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    lignes = []
    for ligne in source.read_text(encoding="utf-8").splitlines():
        if ligne.strip():
            lignes.append(json.dumps(convertir(json.loads(ligne)), ensure_ascii=False))
    destination.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return len(lignes)


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument("--source", type=Path, default=Path("dataset/entrainement.jsonl"))
    analyseur.add_argument("--destination", type=Path, default=DESTINATION)
    arguments = analyseur.parse_args(argv)

    if not arguments.source.exists():
        print(f"{arguments.source} absent : rien à préparer.")
        return 3
    nombre = preparer(arguments.source, arguments.destination)
    print(f"{nombre} exemples écrits dans {arguments.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
