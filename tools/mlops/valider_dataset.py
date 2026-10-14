"""Étape « données » de la chaîne MLOps : valider le dataset avant tout entraînement.

Trois convictions, reprises de la chaîne de données catalogue parce qu'elles
valent ici aussi :

1. **Rien n'est écarté en silence.** Chaque exemple refusé est compté avec son
   motif, et le total des refus plus le total des exemples retenus égale le
   nombre de lignes lues.
2. **Aucune valeur n'est inventée.** Un exemple incomplet est refusé, jamais
   complété par défaut. Un `reasoning` vide reste vide et fait échouer l'étape.
3. **L'écart à la cible est une donnée**, pas une erreur à masquer. La
   répartition visée par `docs/produit/CADRAGE_MODELE.md` (≈ 72 % de raisonné, ~15 % de
   mention simple, ~5 % de forte) est comparée à la répartition réelle, avec sa
   tolérance, et l'écart est écrit.

Ce que cette étape protège vraiment : le jeu d'essai. Un exemple d'essai qui
réapparaît à l'entraînement transforme la seule mesure honnête du projet en
mesure de mémorisation. La détection de fuite est donc bloquante, sans
tolérance.

Format attendu — un objet JSON par ligne :

    {"id": "devis-0001",
     "capacite": "devis",
     "user": "je refais mon salon, peinture et sol",
     "reasoning": "20 m² de mur ... 4,2 L de sous-couche ...",
     "final": {"intent": "devis", "payload": {...}, "mention": null}}

Usage :

    python -m tools.mlops.valider_dataset
    python -m tools.mlops.valider_dataset --entrainement X.jsonl --essai Y.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.schema import (PayloadClarification, PayloadConsommables,
                        PayloadDevis, PayloadReponse, SortieModele)

ENTRAINEMENT = Path("dataset/entrainement.jsonl")
ESSAI = Path("dataset/essai.jsonl")
# Le gabarit : quatre exemples de référence, et six exemples fautifs portant
# chacun un défaut et son motif de refus attendu. Voir `verifier_gabarit`.
GABARIT = Path("dataset/gabarit.jsonl")
GABARIT_FAUTIFS = Path("dataset/gabarit_fautifs.jsonl")

# `docs/produit/CADRAGE_MODELE.md` §Répartition cible. Les volumes y sont donnés pour
# ~2000 exemples ; ce qui compte ici est la **part**, pas le nombre absolu, car
# le dataset se construit progressivement.
CIBLE_PART = {
    "devis": 0.25, "quantitatif": 0.20, "lots": 0.15,
    "consommables": 0.125, "clarification": 0.10, "reponse": 0.175,
}
# Les capacités dont les exemples portent un raisonnement. Les deux autres sont
# courtes par nature : leur imposer un `reasoning` produirait du remplissage.
CAPACITES_RAISONNEES = {"devis", "quantitatif", "lots", "consommables"}
PART_RAISONNEE_CIBLE = 0.72          # Unsloth recommande 75 % minimum
PART_MENTION = {"simple": 0.15, "forte": 0.05}

# Tolérances. Un dataset écrit à la main n'atteint pas une cible au centième ;
# exiger l'exactitude ferait échouer l'étape pour rien. Au-delà, en revanche,
# la dérive est réelle et doit se voir.
TOLERANCE_PART = 0.07
TOLERANCE_RAISONNE = 0.05
TOLERANCE_MENTION = 0.05

PAYLOADS = {
    "devis": PayloadDevis, "quantitatif": PayloadDevis, "lots": PayloadDevis,
    "clarification": PayloadClarification,
    "consommables": PayloadConsommables,
    "reponse": PayloadReponse,
}


@dataclass
class Rapport:
    """Ce que l'étape a lu, retenu, refusé — et pourquoi."""
    lus: int = 0
    retenus: int = 0
    refus: Counter = field(default_factory=Counter)
    details: list[str] = field(default_factory=list)
    capacites: Counter = field(default_factory=Counter)
    raisonnes: int = 0
    mentions: Counter = field(default_factory=Counter)
    ecarts: list[str] = field(default_factory=list)
    fuites: list[str] = field(default_factory=list)

    @property
    def coherent(self) -> bool:
        """Le contrôle qui garantit que rien n'a disparu en route."""
        return self.retenus + sum(self.refus.values()) == self.lus

    @property
    def valide(self) -> bool:
        return not self.refus and not self.fuites and self.coherent


def _refuser(rapport: Rapport, motif: str, detail: str) -> None:
    rapport.refus[motif] += 1
    if len(rapport.details) < 20:      # au-delà, la liste cesse d'être lisible
        rapport.details.append(f"{motif} — {detail}")


def valider_exemple(exemple: Any, rapport: Rapport, origine: str) -> bool:
    """Rend True si l'exemple est retenu. Chaque sortie compte son motif."""
    if not isinstance(exemple, dict):
        _refuser(rapport, "ligne non objet", origine)
        return False

    identifiant = exemple.get("id")
    if not isinstance(identifiant, str) or not identifiant.strip():
        _refuser(rapport, "identifiant absent", origine)
        return False

    capacite = exemple.get("capacite")
    if capacite not in CIBLE_PART:
        _refuser(rapport, "capacité inconnue", f"{identifiant} : {capacite!r}")
        return False

    texte = exemple.get("user")
    if not isinstance(texte, str) or not texte.strip():
        _refuser(rapport, "message utilisateur vide", identifiant)
        return False

    final = exemple.get("final")
    if not isinstance(final, dict):
        _refuser(rapport, "sortie absente", identifiant)
        return False

    try:
        sortie = SortieModele.model_validate(final)
    except ValidationError as erreur:
        _refuser(rapport, "enveloppe non conforme",
                 f"{identifiant} : {erreur.errors()[0]['msg']}")
        return False

    if sortie.intent != capacite:
        _refuser(rapport, "intention contredisant la capacité",
                 f"{identifiant} : capacité {capacite}, intent {sortie.intent}")
        return False

    try:
        PAYLOADS[capacite].model_validate(sortie.payload)
    except ValidationError as erreur:
        _refuser(rapport, "payload non conforme à l'intention",
                 f"{identifiant} : {erreur.errors()[0]['msg']}")
        return False

    raisonnement = exemple.get("reasoning")
    porte_raisonnement = isinstance(raisonnement, str) and raisonnement.strip()
    if capacite in CAPACITES_RAISONNEES and not porte_raisonnement:
        # C'est le `reasoning` qui porte l'expertise métier. Sans lui, on
        # n'entraîne qu'un formateur de JSON.
        _refuser(rapport, "raisonnement absent sur une capacité raisonnée",
                 identifiant)
        return False

    rapport.retenus += 1
    rapport.capacites[capacite] += 1
    rapport.raisonnes += 1 if porte_raisonnement else 0
    rapport.mentions[sortie.mention or "aucune"] += 1
    return True


def lire(chemin: Path, rapport: Rapport) -> list[dict]:
    """Lit un JSONL. Une ligne illisible est un refus, pas une exception."""
    retenus: list[dict] = []
    for numero, ligne in enumerate(
            chemin.read_text(encoding="utf-8").splitlines(), start=1):
        if not ligne.strip():
            continue
        rapport.lus += 1
        origine = f"{chemin.name}:{numero}"
        try:
            exemple = json.loads(ligne)
        except json.JSONDecodeError as erreur:
            _refuser(rapport, "JSON illisible", f"{origine} : {erreur.msg}")
            continue
        if valider_exemple(exemple, rapport, origine):
            retenus.append(exemple)
    return retenus


def _normaliser(texte: str) -> str:
    return " ".join(texte.lower().split())


def detecter_fuite(entrainement: list[dict], essai: list[dict]) -> list[str]:
    """Un exemple d'essai présent à l'entraînement rend la mesure malhonnête.

    La comparaison porte sur le message utilisateur normalisé, pas sur
    l'identifiant : renommer un exemple ne le rend pas nouveau.
    """
    vus = {_normaliser(e["user"]): e["id"] for e in entrainement}
    fuites = []
    for exemple in essai:
        jumeau = vus.get(_normaliser(exemple["user"]))
        if jumeau:
            fuites.append(f"{exemple['id']} (essai) ≡ {jumeau} (entraînement)")
    return fuites


def mesurer_ecarts(rapport: Rapport) -> list[str]:
    """Compare la répartition réelle à la cible. Écrit l'écart, ne le corrige pas."""
    ecarts = []
    total = rapport.retenus
    if not total:
        return ["dataset vide : aucune répartition à mesurer"]

    for capacite, cible in sorted(CIBLE_PART.items()):
        part = rapport.capacites[capacite] / total
        if abs(part - cible) > TOLERANCE_PART:
            ecarts.append(f"{capacite} : {part:.0%} pour une cible de {cible:.0%}")

    part_raisonnee = rapport.raisonnes / total
    if abs(part_raisonnee - PART_RAISONNEE_CIBLE) > TOLERANCE_RAISONNE:
        ecarts.append(f"exemples raisonnés : {part_raisonnee:.0%} pour une cible "
                      f"de {PART_RAISONNEE_CIBLE:.0%}")

    for mention, cible in PART_MENTION.items():
        part = rapport.mentions[mention] / total
        if abs(part - cible) > TOLERANCE_MENTION:
            ecarts.append(f"mention {mention} : {part:.0%} pour une cible de {cible:.0%}")
    return ecarts


def valider(chemin_entrainement: Path, chemin_essai: Path) -> Rapport:
    rapport = Rapport()
    entrainement = lire(chemin_entrainement, rapport) if chemin_entrainement.exists() else []
    essai = lire(chemin_essai, rapport) if chemin_essai.exists() else []
    rapport.fuites = detecter_fuite(entrainement, essai)
    rapport.ecarts = mesurer_ecarts(rapport)
    return rapport


def imprimer(rapport: Rapport) -> None:
    print(f"Exemples lus       : {rapport.lus}")
    print(f"Exemples retenus   : {rapport.retenus}")
    if rapport.refus:
        print("Refus, par motif :")
        for motif, nombre in rapport.refus.most_common():
            print(f"  - {motif} : {nombre}")
        for detail in rapport.details:
            print(f"      {detail}")
    if not rapport.coherent:
        print("INCOHÉRENCE : retenus + refusés ≠ lus — des exemples ont disparu.")
    if rapport.fuites:
        print("FUITE entre entraînement et essai :")
        for fuite in rapport.fuites:
            print(f"  - {fuite}")
    if rapport.ecarts:
        print("Écarts à la répartition cible (avertissement, pas un échec) :")
        for ecart in rapport.ecarts:
            print(f"  - {ecart}")


def verifier_gabarit(bons: Path = GABARIT, fautifs: Path = GABARIT_FAUTIFS) -> list[str]:
    """Vérifie que le validateur détecte encore ce qu'il est censé détecter.

    Un détecteur qui cesse silencieusement de détecter est pire que pas de
    détecteur : il donne une garantie qu'il ne tient plus. Le gabarit fautif
    porte un défaut par ligne et le motif de refus attendu ; si un refus change
    de motif ou disparaît, c'est ici que ça rougit, pas six mois plus tard.

    Rend la liste des anomalies — vide si tout va bien.
    """
    anomalies = []

    rapport = Rapport()
    for numero, ligne in enumerate(
            bons.read_text(encoding="utf-8").splitlines(), start=1):
        if ligne.strip():
            rapport.lus += 1
            if not valider_exemple(json.loads(ligne), rapport, f"{bons.name}:{numero}"):
                anomalies.append(f"exemple de référence refusé : {bons.name}:{numero}")
    anomalies += [f"exemple de référence refusé — {d}" for d in rapport.details]

    for numero, ligne in enumerate(
            fautifs.read_text(encoding="utf-8").splitlines(), start=1):
        if not ligne.strip():
            continue
        exemple = json.loads(ligne)
        attendu = exemple.pop("_motif_attendu")
        controle = Rapport()
        controle.lus = 1
        retenu = valider_exemple(exemple, controle, f"{fautifs.name}:{numero}")
        if retenu:
            anomalies.append(f"défaut non détecté ({attendu}) : {exemple['id']}")
        elif attendu not in controle.refus:
            obtenu = ", ".join(controle.refus) or "aucun"
            anomalies.append(
                f"{exemple['id']} : motif attendu « {attendu} », obtenu « {obtenu} »")
    return anomalies


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument("--entrainement", type=Path, default=ENTRAINEMENT)
    analyseur.add_argument("--essai", type=Path, default=ESSAI)
    analyseur.add_argument("--sans-gabarit", action="store_true",
                           help="ne pas vérifier les détecteurs avant de valider")
    arguments = analyseur.parse_args(argv)

    if not arguments.sans_gabarit:
        anomalies = verifier_gabarit()
        if anomalies:
            print("Le validateur ne détecte plus ce qu'il devrait :")
            for anomalie in anomalies:
                print(f"  - {anomalie}")
            return 1
        print("Gabarit : détecteurs vérifiés, exemples de référence acceptés.")

    if not arguments.entrainement.exists() and not arguments.essai.exists():
        print(f"{arguments.entrainement} et {arguments.essai} absents : "
              "aucun exemple à valider — le dataset reste à écrire à la main.")
        return 0 if not arguments.sans_gabarit else 3

    rapport = valider(arguments.entrainement, arguments.essai)
    imprimer(rapport)
    return 0 if rapport.valide else 1


if __name__ == "__main__":
    raise SystemExit(main())
