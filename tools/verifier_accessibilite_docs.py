#!/usr/bin/env python3
"""Contrôle mécanique des règles d'accessibilité documentaire.

Trois des neuf règles de `docs/ACCESSIBILITE_DOCUMENTS.md` se vérifient sans
jugement humain : un seul titre de niveau 1 par document (règle 1), aucun saut
dans la hiérarchie des titres (règle 2), aucun libellé de lien creux (règle 4).
Les six autres se relisent — elles sont courtes exprès.

Sort en code 1 dès qu'une règle est enfreinte, pour servir d'étape de chaîne
d'intégration continue.

    python3 tools/verifier_accessibilite_docs.py
"""
from __future__ import annotations

import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent

# Les fichiers du dossier, hors archive/ (valeur historique, non livré) et hors
# CONTEXTE_COMPLET_PROJET.md (fichier généré, destiné à être collé ailleurs).
def corpus() -> list[pathlib.Path]:
    fichiers = sorted((RACINE / "docs").glob("*.md"))
    fichiers += sorted((RACINE / "veille").glob("*.md"))
    # Les comptes rendus de séance sont un livrable de C6 au même titre que le
    # dispositif qui les encadre : les laisser hors du contrôle reviendrait à
    # exempter la partie qui grossit chaque semaine.
    fichiers += sorted((RACINE / "veille" / "seances").glob("*.md"))
    fichiers += [RACINE / nom for nom in ("README.md", "CLAUDE.md", "PLANNING.md")]
    return [f for f in fichiers if f.exists()]


def titres(chemin: pathlib.Path) -> list[tuple[int, int]]:
    """(numéro de ligne, niveau) des titres, blocs de code exclus.

    Un commentaire `# Règle 1` dans un bloc bash n'est pas un titre : sans cette
    exclusion, le contrôle signale des violations dans les documents qui
    montrent des commandes — dont ce document lui-même.
    """
    dans_bloc = False
    trouves: list[tuple[int, int]] = []
    for numero, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
        if ligne.startswith("```"):
            dans_bloc = not dans_bloc
            continue
        if dans_bloc:
            continue
        marque = re.match(r"^(#{1,6}) ", ligne)
        if marque:
            trouves.append((numero, len(marque.group(1))))
    return trouves


LIENS_CREUX = re.compile(r"\[(ici|ce lien|voir|cliquez[^\]]*|lire la suite)\]\(", re.I)


def main() -> int:
    manquements: list[str] = []

    for chemin in corpus():
        relatif = chemin.relative_to(RACINE)
        entetes = titres(chemin)

        # Règle 1 — un seul titre de niveau 1
        premiers = [n for n, niveau in entetes if niveau == 1]
        if len(premiers) != 1:
            manquements.append(
                f"{relatif} — règle 1 : {len(premiers)} titres de niveau 1 "
                f"(lignes {premiers or 'aucune'})"
            )

        # Règle 2 — aucun saut de niveau
        precedent = 0
        for numero, niveau in entetes:
            if precedent and niveau > precedent + 1:
                manquements.append(
                    f"{relatif}:{numero} — règle 2 : saut de niveau "
                    f"{precedent} vers {niveau}"
                )
            precedent = niveau

        # Règle 4 — libellés de lien explicites
        for numero, ligne in enumerate(
            chemin.read_text(encoding="utf-8").splitlines(), 1
        ):
            if LIENS_CREUX.search(ligne):
                manquements.append(
                    f"{relatif}:{numero} — règle 4 : libellé de lien non explicite"
                )

    if manquements:
        print("Accessibilité documentaire — manquements :\n")
        for m in manquements:
            print(f"  {m}")
        print(f"\n{len(manquements)} manquement(s). Voir docs/ACCESSIBILITE_DOCUMENTS.md.")
        return 1

    print(f"Accessibilité documentaire : {len(corpus())} documents conformes "
          "aux règles 1, 2 et 4.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
