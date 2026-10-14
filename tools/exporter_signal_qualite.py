#!/usr/bin/env python3
"""Exporte les corrections d'artisan en candidats d'entraînement (US-25).

    VIRTUAL_ENV=~/.venvs/the-project uv run python tools/exporter_signal_qualite.py
    … --destination ~/.local/share/the-project/signal_qualite.jsonl
    … --projets donnees/            # racine des projets, par défaut BTP_DONNEES
    … --a-blanc                     # compte sans écrire

Le fichier produit est en ajout seul et dédoublonné : relancer la commande deux
fois de suite n'ajoute rien la seconde fois, et rien n'en est jamais retiré.

La destination est vérifiée avant écriture. Un chemin sur un montage synchronisé
(ce dépôt est sur OneDrive) ou distant est **refusé** : ces corrections portent
des dictées de chantier et des noms de clients, elles restent sur la machine.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.boucle_qualite import (DESTINATION_DEFAUT, DestinationNonLocale,  # noqa: E402
                                candidats_du_disque, exporter,
                                verifier_destination)


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parseur.add_argument("--destination", default=None,
                         help=f"fichier JSONL du jeu (défaut : {DESTINATION_DEFAUT})")
    parseur.add_argument("--projets", default=None,
                         help="racine des projets persistés (défaut : BTP_DONNEES)")
    parseur.add_argument("--a-blanc", action="store_true",
                         help="compte les candidats sans rien écrire")
    args = parseur.parse_args(argv)

    trouves = candidats_du_disque(Path(args.projets) if args.projets else None)
    complets = [c for c in trouves if c.complet]
    incomplets = len(trouves) - len(complets)

    if args.a_blanc:
        try:
            cible = verifier_destination(args.destination or DESTINATION_DEFAUT)
        except DestinationNonLocale as erreur:
            print(f"destination refusée : {erreur}", file=sys.stderr)
            return 2
        print(f"{len(complets)} candidat(s) complet(s), {incomplets} incomplet(s) "
              f"— rien écrit (à blanc). Destination validée : {cible}")
        return 0

    try:
        rapport = exporter(trouves, args.destination)
    except DestinationNonLocale as erreur:
        print(f"destination refusée : {erreur}", file=sys.stderr)
        return 2
    except OSError as erreur:
        print(f"écriture impossible : {erreur}", file=sys.stderr)
        return 1

    print(f"jeu : {rapport['destination']}")
    print(f"  ajoutés        : {rapport['ajoutes']}")
    print(f"  déjà présents  : {rapport['deja_presents']}")
    print(f"  incomplets     : {rapport['incomplets']} "
          f"(corrections d'avant la version 4 du format — triplet absent)")
    print(f"  taille du jeu  : {rapport['total_jeu']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
