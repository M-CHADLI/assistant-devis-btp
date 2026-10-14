"""Étape 1 — extraction depuis un **fichier de données** (export fournisseur).

Source : `catalogue/sources/export_fournisseur_simule.csv`, point-virgule,
UTF-8, une ligne par référence vendable. Le fichier est **simulé** (contrainte
légale, `docs/DECISIONS.md` D-12) mais sa structure est celle d'un vrai export,
et ce script ne fait aucune hypothèse qui tomberait sur un vrai dump.

**Ce script n'interprète rien.** Il lit, il compte, il trace. Le nettoyage
appartient à `agreger.py` : mélanger extraction et nettoyage rendrait
impossible de savoir, devant une valeur bizarre, si la source est sale ou si le
code l'a abîmée.

Dépendances : bibliothèque standard uniquement.

```bash
VIRTUAL_ENV=~/.venvs/the-project uv run --no-sync python -m tools.donnees.extraire_fichier
```
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from tools.donnees.commun import ecrire_brut

SOURCE = Path("catalogue/sources/export_fournisseur_simule.csv")


def extraire(chemin: Path = SOURCE) -> list[dict[str, str]]:
    if not chemin.exists():
        raise FileNotFoundError(
            f"{chemin} absent : lancer tools/donnees/simuler_dump.py, ou "
            "déposer le véritable export à cet emplacement.")
    with chemin.open(encoding="utf-8", newline="") as flux:
        return [dict(ligne) for ligne in csv.DictReader(flux, delimiter=";")]


def main() -> int:
    try:
        lignes = extraire()
    except (OSError, csv.Error) as erreur:
        print(f"extraction fichier échouée : {erreur}", file=sys.stderr)
        return 1
    cible = ecrire_brut(
        "fichier_export_fournisseur",
        source=str(SOURCE),
        licence="Données simulées — structure d'un export fournisseur réel",
        lignes=lignes,
        notes="Valeurs simulées par tools/donnees/simuler_dump.py. "
              "Défauts volontaires : doublons, prix vides ou négatifs, unités "
              "hétérogènes, dates à deux formats.")
    print(f"{cible} : {len(lignes)} lignes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
