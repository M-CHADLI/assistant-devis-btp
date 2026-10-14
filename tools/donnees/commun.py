"""Ce que les trois extracteurs partagent : la trace d'origine et l'écriture.

Deux règles tiennent tout le reste de la chaîne :

1. **Aucune donnée brute n'est écrite sans sa provenance.** Chaque fichier de
   `catalogue/brut/` porte en tête la source, sa licence, l'horodatage et le
   nombre de lignes. Un jeu de données sans provenance n'est pas exploitable :
   on ne sait ni s'il a le droit d'être là, ni ce qu'il vaut.
2. **L'écriture est atomique.** Un extracteur interrompu au milieu laisserait
   sinon un JSON tronqué que l'agrégation lirait comme un fichier valide et
   vide. Même parade que `app/persistance.py` : fichier temporaire puis
   `replace`, qui est atomique sur le même système de fichiers.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RACINE_BRUT = Path("catalogue/brut")


def ecrire_brut(nom: str, *, source: str, licence: str,
                lignes: list[dict[str, Any]], notes: str = "") -> Path:
    """Écrit `catalogue/brut/<nom>.json` avec son en-tête de provenance."""
    RACINE_BRUT.mkdir(parents=True, exist_ok=True)
    cible = RACINE_BRUT / f"{nom}.json"
    contenu = {
        "source": source,
        "licence": licence,
        "extrait_le": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nombre_de_lignes": len(lignes),
        "notes": notes,
        "lignes": lignes,
    }
    temporaire = cible.with_suffix(".json.tmp")
    temporaire.write_text(json.dumps(contenu, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    temporaire.replace(cible)
    return cible


def lire_brut(nom: str) -> dict[str, Any]:
    """Relit un extrait, en disant clairement quel script le produit."""
    cible = RACINE_BRUT / f"{nom}.json"
    if not cible.exists():
        raise FileNotFoundError(
            f"{cible} absent : lancer d'abord tools/donnees/extraire_{nom.split('_')[0]}.py")
    return json.loads(cible.read_text(encoding="utf-8"))
