"""Exécuteur de la chaîne MLOps — lit `mlops/pipeline.toml` et déroule les étapes.

Pourquoi un exécuteur maison plutôt que Kubeflow, Airflow ou ZenML : la chaîne
compte cinq étapes, tourne sur une machine, et doit rester lisible par un jury
en trois minutes. Un orchestrateur ajouterait un serveur à tenir, une base de
métadonnées, et une couche d'abstraction entre la commande et ce qu'elle fait.
Le jour où la chaîne s'exécutera sur plusieurs machines, ce choix se
rediscutera — il est écrit dans `docs/CHAINE_MLOPS.md` pour cela.

**Trois états, pas deux.** Une étape est `réussie`, `échouée`, ou `ignorée`
faute de prérequis (code de sortie 3). La troisième existe parce que la chaîne
décrit un entraînement qui n'a pas encore eu lieu : confondre « pas encore
lancé » avec « réussi » ferait mentir le rapport, et confondre avec « échoué »
ferait rougir une chaîne qui va bien.

Usage :

    python -m tools.mlops.executer                     # toute la chaîne
    python -m tools.mlops.executer --jusqu-a donnees   # s'arrêter après une étape
    python -m tools.mlops.executer --simulation        # afficher le plan, ne rien lancer
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

DECLARATION = Path("mlops/pipeline.toml")
EXECUTIONS = Path("mlops/executions")

REUSSI, ECHOUE, IGNORE = "réussi", "échoué", "ignoré"
CODE_PREREQUIS_ABSENT = 3


@dataclass
class Etape:
    nom: str
    description: str
    module: str
    arguments: list[str]
    prerequis: list[str]
    bloquant: bool


@dataclass
class Resultat:
    etape: str
    etat: str
    code: int | None
    duree_s: float
    motif: str = ""


def lire_declaration(chemin: Path) -> tuple[dict, list[Etape]]:
    declaration = tomllib.loads(chemin.read_text(encoding="utf-8"))
    etapes = [Etape(nom=e["nom"], description=e["description"], module=e["module"],
                    arguments=e.get("arguments", []), prerequis=e.get("prerequis", []),
                    bloquant=e.get("bloquant", True))
              for e in declaration["etape"]]
    noms = [e.nom for e in etapes]
    if len(set(noms)) != len(noms):
        raise ValueError(f"étapes en double dans {chemin} : {noms}")
    return declaration["chaine"], etapes


def prerequis_absents(etape: Etape, racine: Path) -> list[str]:
    return [chemin for chemin in etape.prerequis if not (racine / chemin).exists()]


def executer(etapes: list[Etape], racine: Path, simulation: bool = False,
             jusqu_a: str | None = None) -> list[Resultat]:
    resultats: list[Resultat] = []
    for etape in etapes:
        absents = prerequis_absents(etape, racine)
        if absents:
            resultats.append(Resultat(etape.nom, IGNORE, None, 0.0,
                                      "prérequis absents : " + ", ".join(absents)))
        elif simulation:
            resultats.append(Resultat(etape.nom, IGNORE, None, 0.0,
                                      "simulation : rien n'a été lancé"))
        else:
            debut = datetime.now(UTC)
            acheve = subprocess.run(
                [sys.executable, "-m", etape.module, *etape.arguments],
                cwd=racine, capture_output=True, text=True)
            duree = (datetime.now(UTC) - debut).total_seconds()
            if acheve.returncode == 0:
                etat, motif = REUSSI, ""
            elif acheve.returncode == CODE_PREREQUIS_ABSENT:
                etat = IGNORE
                motif = (acheve.stdout or acheve.stderr).strip().splitlines()[-1:] or [""]
                motif = motif[0]
            else:
                etat = ECHOUE
                motif = (acheve.stderr or acheve.stdout).strip().splitlines()[-1:] or [""]
                motif = motif[0]
            resultats.append(Resultat(etape.nom, etat, acheve.returncode,
                                      round(duree, 2), motif))
            print(acheve.stdout, end="")
            if acheve.stderr:
                print(acheve.stderr, end="", file=sys.stderr)

        dernier = resultats[-1]
        if dernier.etat == ECHOUE and etape.bloquant:
            break
        if jusqu_a and etape.nom == jusqu_a:
            break
    return resultats


def rapport(chaine: dict, resultats: list[Resultat]) -> dict:
    return {
        "chaine": chaine["nom"],
        "version": chaine["version"],
        "horodatage": datetime.now(UTC).isoformat(timespec="seconds"),
        "etapes": [asdict(r) for r in resultats],
        "reussi": all(r.etat != ECHOUE for r in resultats),
    }


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument("--declaration", type=Path, default=DECLARATION)
    analyseur.add_argument("--jusqu-a", dest="jusqu_a")
    analyseur.add_argument("--simulation", action="store_true")
    analyseur.add_argument("--executions", type=Path, default=EXECUTIONS)
    arguments = analyseur.parse_args(argv)

    racine = arguments.declaration.resolve().parent.parent
    chaine, etapes = lire_declaration(arguments.declaration)
    if arguments.jusqu_a and arguments.jusqu_a not in {e.nom for e in etapes}:
        print(f"étape inconnue : {arguments.jusqu_a}", file=sys.stderr)
        return 2

    print(f"Chaîne {chaine['nom']} v{chaine['version']} — {len(etapes)} étapes"
          + (" (simulation)" if arguments.simulation else ""))
    resultats = executer(etapes, racine, arguments.simulation, arguments.jusqu_a)

    largeur = max(len(r.etape) for r in resultats)
    print()
    for resultat in resultats:
        motif = f"  — {resultat.motif}" if resultat.motif else ""
        print(f"  {resultat.etape:<{largeur}}  {resultat.etat:<7}"
              f"{resultat.duree_s:>7.2f}s{motif}")

    ecrit = rapport(chaine, resultats)
    if not arguments.simulation:
        arguments.executions.mkdir(parents=True, exist_ok=True)
        destination = (arguments.executions
                       / f"{ecrit['horodatage'].replace(':', '')}.json")
        destination.write_text(json.dumps(ecrit, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        print(f"\nRapport : {destination}")
    return 0 if ecrit["reussi"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
