"""Étape « entraînement » : LoRA sur gpt-oss via Unsloth.

**Cette étape n'a jamais été exécutée.** Elle attend le dataset et la DGX
Spark ; le calendrier la place en octobre (`PLANNING.md`). Elle existe
maintenant parce qu'une chaîne MLOps écrite après l'entraînement ne peut plus
en porter la trace — elle ne fait que la raconter.

Le parti pris est donc : vérifier les prérequis, les nommer un par un quand ils
manquent, et sortir avec le code 3 (« prérequis absent ») plutôt que de
prétendre. Aucun entraînement simulé, aucun artefact factice — un adaptateur
qui n'existe pas ne doit pas laisser croire le contraire.

Les hyperparamètres vivent dans `mlops/lora.toml`, hors du code : les changer
ne doit pas demander de modifier un script, et leur historique doit se lire
dans git.
"""
from __future__ import annotations

import argparse
import importlib.util
import tomllib
from pathlib import Path

CONFIGURATION = Path("mlops/lora.toml")
DONNEES = Path("mlops/artefacts/entrainement.chat.jsonl")


def prerequis_manquants(configuration: Path, donnees: Path) -> list[str]:
    """Chaque prérequis est nommé séparément : « ça ne marche pas » n'aide personne."""
    manquants = []
    if not configuration.exists():
        manquants.append(f"configuration absente : {configuration}")
    if not donnees.exists():
        manquants.append(f"données préparées absentes : {donnees} "
                         "(lancer d'abord tools.mlops.preparer)")
    if importlib.util.find_spec("unsloth") is None:
        manquants.append("paquet `unsloth` non installé dans l'environnement")
    else:  # pragma: no cover - dépend d'une machine équipée
        import torch
        if not torch.cuda.is_available():
            manquants.append("aucun GPU CUDA visible")
    return manquants


def lire_configuration(chemin: Path) -> dict:
    return tomllib.loads(chemin.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument("--configuration", type=Path, default=CONFIGURATION)
    analyseur.add_argument("--donnees", type=Path, default=DONNEES)
    arguments = analyseur.parse_args(argv)

    manquants = prerequis_manquants(arguments.configuration, arguments.donnees)
    if manquants:
        print("Entraînement non lancé — prérequis absents :")
        for manquant in manquants:
            print(f"  - {manquant}")
        if arguments.configuration.exists():
            reglages = lire_configuration(arguments.configuration)["lora"]
            print("\nCe qui serait lancé, une fois les prérequis réunis :")
            print(f"  modèle    : {reglages['modele_base']}")
            print(f"  rang LoRA : {reglages['rang']} (alpha {reglages['alpha']})")
            print(f"  époques   : {reglages['epoques']}, "
                  f"longueur max {reglages['longueur_max']}")
        return 3

    # pragma: no cover - jamais atteint sans GPU ni dataset
    raise SystemExit(
        "Prérequis réunis, mais l'entraînement reste à écrire avec la machine "
        "sous la main : le code d'appel Unsloth n'a jamais été exécuté et ne "
        "sera pas versionné avant de l'avoir été. Voir docs/CHAINE_MLOPS.md.")


if __name__ == "__main__":
    raise SystemExit(main())
